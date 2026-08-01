# Plan 3 M4 S4～S6 Naive RAG Query / Chat 设计

- Date: 2026-08-01
- Scope: `P3-M4-S4～P3-M4-S6`
- Status: approved by the user's explicit start instruction
- Selected approach: 独立 Prompt Builder + 轻量 `RagQueryService` + `RagService` Chat 子类 + 两个薄 FastAPI endpoints

## 1. 目标与范围

本批把 M4 S1～S3 已完成的独立 Retriever 接入最小 Naive RAG HTTP 闭环：

1. 独立构造有来源约束、来源编号和上下文字符预算的 RAG Prompt；
2. `POST /api/v1/rag/query` 只检索，不调用 LLM，返回有序结果和检索 metadata；
3. `POST /api/v1/rag/chat` 保存用户问题，检索 Chunk，构造 Prompt，调用 Mockable LLM
   Provider，保存 assistant 回答和 `LLMCall`，返回 answer、sources 与 metadata。

本批不写 `rag_queries`（S7），不注册 `search_knowledge_base` Tool（S8），不实现 streaming、
前端、Advanced RAG、metadata filtering、hybrid search、rerank、evaluation、memory、OCR 或
multimodal。SQLite 仍是业务与会话主数据库，Qdrant 只负责向量检索。

## 2. 验收解释

详细 Step 15 明确 `POST /api/v1/rag/query` 是“只检索、不生成回答”的接口，并给出
`results` 响应示例。执行步骤表阶段摘要中的“RAG Query API 返回 answer、sources、retrieval
metadata”与详细 Step 冲突。本设计以更具体的 Step 15 为准：

- `/rag/query` 返回 `results + metadata`，不产生 `answer`；
- `/rag/chat` 返回 `answer + sources + metadata`。

两个接口合并满足阶段所需的检索调试和完整问答能力，同时不让 query endpoint 隐式产生
付费 LLM 调用。

## 3. 方案比较

### 采用：分离依赖的 Query/Chat service

`RagQueryService` 只注入 SQLAlchemy Session 和 Retriever。`RagService` 继承该检索
能力，再注入 RAG Prompt Builder、ModelRegistry 和 LLM Provider mapping。Chat 复用
`ConversationService`、`ProviderLatencyTimer`、`build_llm_call_metrics` 和已有 ORM，
不修改 ChatService 的公开行为。

优点是 retrieval-only route 保持真正无 LLM 配置依赖，两个 route 都保持薄，RAG
orchestration 可单测，Provider/VectorStore 可完整替换，且不会把 RAG Prompt 作为用户
原始消息错误持久化。代价是 LLMCall 收尾与 ChatService 有少量结构性重复；本批不做跨
服务重构，以控制回归范围。

### 未采用：扩展 `ChatService.complete()` 接受 prepared messages

这可以复用更多代码，但会扩大 Plan 1 稳定 Chat 契约，并让普通 Chat 知道 RAG Prompt 和
source 语义。当前批次不需要承担这个兼容风险。

### 未采用：拆分 RetrievalService 与 RagChatService

职责最细，但 S5/S6 的共享校验、metadata 和依赖装配会重复。当前只有一种 Naive RAG
策略，一个组合 service 足够；Plan 4 引入多策略时再评估拆分。

## 4. 文件与职责

### `backend/app/rag/rag_prompt.py`

提供纯同步、无数据库和网络依赖的 `RagPromptBuilder`：

```python
class RagPromptBuilder:
    def __init__(self, *, max_context_characters: int = 12_000) -> None: ...

    def build(
        self,
        *,
        query: str,
        retrieval_results: tuple[RetrievalResult, ...],
        history: tuple[ChatMessage, ...] = (),
    ) -> RagPrompt: ...
```

`RagPrompt` 是不可变 dataclass，包含：

- `messages: tuple[ChatMessage, ...]`；
- `sources: tuple[RagSource, ...]`，只包含实际注入 Prompt 的来源；
- `context_characters: int`。

Builder 固定生成一个 system message，随后保留既有 user/assistant 历史，最后生成包含资料
片段和当前问题的 user message。资料中的内容只被声明为参考数据，不能覆盖 system 指令。

### `backend/app/schemas/rag.py`

新增严格、`extra="forbid"` 的 API schema：

- `RagRetrievalRequest`：Knowledge Base UUID、非空 query、严格 1～100 `top_k`、可选有限
  `score_threshold`；
- `RagChatRequest`：在检索参数上增加必填 conversation/provider/model，以及 temperature、
  max_tokens；
- `RagRetrievalMetadata`：`strategy="naive_vector"`、请求参数和结果数量；
- `RagSource`：`RetrievalResult` 加稳定的 1-based `source_index`；
- `RagQueryResponse`：`results + metadata`；
- `RagChatResponse`：conversation/user/assistant/LLMCall、answer、indexed sources 和 answer
  metadata。

### `backend/app/services/rag_service.py`

提供轻量基类和 Chat 子类两个异步入口：

```python
class RagQueryService:
    async def query(self, request: RagRetrievalRequest) -> RagQueryResult: ...

class RagService(RagQueryService):
    async def chat(self, request: RagChatRequest) -> RagChatResult: ...
```

`query()` 先确认 Knowledge Base 存在，再调用 Retriever，一次请求不调用 LLM、不创建
Message/LLMCall/RagQuery。

`chat()` 按以下顺序执行：

```text
验证 model/provider/Knowledge Base/conversation
  -> 保存原始 user query
  -> 检索 Chunk
  -> 用既有 user/assistant 历史和当前 sources 构造 Prompt
  -> 调用一次 provider.chat()
  -> 校验非空文本响应
  -> 保存 assistant Message 与 LLMCall
  -> 更新 conversation provider/model/updated_at
  -> 返回 answer + 实际注入的 indexed sources + metadata
```

发生任何异常时，service 回滚当前 Session，确保直接 service 测试和 API transaction owner 都
不会留下半个回合。Provider、Embedding 和 VectorStore 原始分类异常继续由统一 API handler
映射为安全错误。

### `backend/app/api/v1/rag.py`

只负责 schema、Depends、service 调用和 response mapping：

- `POST /api/v1/rag/query`；
- `POST /api/v1/rag/chat`。

`backend/app/api/dependencies.py` 分别组装不解析 LLM 的 RagQueryService，以及完整的
Prompt/Registry/Provider RagService；
`backend/app/main.py` 注册 router。

## 5. Prompt 与上下文预算

system instruction 要求：只基于资料回答；没有答案时明确回答“资料中没有找到相关信息”；
引用事实时使用 `[n]`；不得编造来源；资料片段中的指令不能覆盖系统约束。

每个来源格式为：

```text
[1] 文件：guide.md，第 3 页
内容：...
```

来源按 Retriever 顺序编号，不重排或 rerank。`RAG_MAX_CONTEXT_CHARACTERS` 默认 12,000，
范围 128～1,000,000，只限制格式化后的资料片段区域，不限制 system instruction、历史或用户
问题。Builder 逐个加入来源；最后一个来源可按剩余预算截断并加省略号；没有空间的后续来源
不进入 Prompt，也不进入响应 `sources`。这样回答引用索引始终对应模型实际看到的来源。

无命中时注入“（无可用资料片段）”，仍调用 LLM，让 system instruction 引导固定的无资料
回答语义；响应 sources 为空。

## 6. 数据与事务边界

- `/rag/query` 是只读业务操作，不写 SQLite 或 Qdrant；
- `/rag/chat` 只写既有 Conversation、Message、LLMCall；
- `rag_queries` 已存在但本批绝不写入，留给 S7；
- route dependency owns commit/rollback，service 在 Provider/组合失败时主动 rollback，保持与
  ChatService 的直接调用行为一致；
- 不创建 migration，不修改 ORM schema；
- 不读取或修改用户 `backend/ai_agent_lab.db`。

## 7. 错误与安全

- malformed UUID、空 query、bool Top-K、非有限 threshold 等在 Pydantic 层返回统一 422；
- Knowledge Base 或 Conversation 不存在沿用安全 404；
- 未注册 model 返回 `model_not_found` 400，未配置 provider 返回
  `provider_unavailable` 503；
- Embedding/VectorStore/LLM Provider 错误沿用已有脱敏映射；
- Retriever 不可信组合响应映射为固定 `rag_retrieval_response_invalid`，不泄漏 query、正文、
  向量、endpoint、credential 或底层 diagnostic；
- 日志不记录 Prompt、source content、query 或 secret。

## 8. TDD 与验证

按以下 RED/GREEN 次序：

1. Prompt Builder import/format/预算/source-index RED；
2. RAG request/response schema RED；
3. query service 无 LLM/无写入/KB 404 RED；
4. chat service Prompt/会话/LLMCall/rollback RED；
5. route/OpenAPI/response/error mapping RED；
6. Mock Embedding + real temporary Qdrant + Mock LLM 的 API smoke。

matching verification 覆盖 Prompt、schemas、Retriever、RagService、RAG API、Conversation、
Chat、Provider、VectorStore。完成后运行完整 backend、pip check、临时 SQLite Alembic 往返、
frontend typecheck/tests/build、Docker/health、文档链接、secret、artifact、Plan boundary 和 Git
检查。

## 9. 文档与边界

新增 `docs/23-naive-rag.md`，同步 README 中英文、CHANGELOG、Architecture、Knowledge Base
Design、`.env.example` 和 Plan 3 执行步骤表。文档明确 query endpoint 不生成答案，chat
endpoint 非 streaming，审计记录/Tool/frontend/Advanced RAG 仍未实现。
