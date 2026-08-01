# Plan 3 M4 S1～S3 Naive Vector Retriever 设计

## Status

- Scope: `P3-M4-S1～P3-M4-S3`
- Date: 2026-08-01
- Baseline: `main == origin/main == 5b72d10874134a6804652aba7502d5607fe628ce`
- Selected approach: 独立 `Retriever` 类 + 稳定 `RetrievalResult` schema
- Design approval: 用户已明确要求开始仓库既定 Step；Plan 原文已冻结输入、Top-K 与 threshold 契约
- Implementation status: complete; matching verification and Codex self-review passed

## 1. 目标与边界

本批在已完成的 `EmbeddingProvider` 和 `VectorStore` 之上实现基础语义检索：输入一个
非空 query、Knowledge Base UUID、可选 `top_k` 和 `score_threshold`，生成一个 query
embedding，调用 VectorStore 的 Knowledge Base 隔离搜索，并返回有序、可序列化且保留
来源信息的 `RetrievalResult`。

本批不创建 API、RAG Prompt、答案生成、会话写入、`rag_queries` 记录、Agent Tool、
前端页面，也不实现 metadata filter、Hybrid Search、Parent-Child、Rerank、Evaluation、
Trace、Memory、OCR 或 multimodal runtime。

## 2. 验收矩阵

| Step | 原文验收 | 当前证据 | 缺口 | 最小交付 |
|---|---|---|---|---|
| S1 | `retriever.py`；给定 query 返回 Top-K `RetrievalResult` | Provider 已有 `embed_query()`；VectorStore 已有 `search()` | 没有独立检索编排 | 新增 `Retriever.retrieve()`，串联 query embedding 与 vector search |
| S2 | 返回 `chunk_id`、`document_id`、`score`、`content`、`metadata` | Qdrant payload 已保留 KB/document/chunk、filename/index/content/heading/page/metadata | 没有稳定来源 schema 与映射 | 在 `schemas/rag.py` 新增不可变 `RetrievalResult`，保留全部稳定来源字段 |
| S3 | mock VectorStore 检索测试通过 | Provider/VectorStore 各自已有测试 | 没有 Retriever 行为、输入、错误与隔离测试 | 新增 focused tests，覆盖默认/自定义参数、空结果、严格输入、数量/维度和 KB 隔离 |

## 3. 方案比较

### 采用：依赖注入的 `Retriever` 类

构造器接收一个 `EmbeddingProvider` 和一个 `VectorStore`，`retrieve()` 只接收每次查询
变化的参数。这样 Retriever 不知道 Provider/Qdrant 的实现细节，也不拥有 Session、Settings
或 client lifecycle。未来 RAG Service 可以在请求依赖层创建一次并复用，测试可以注入完整
边界替身。

### 未采用：无状态检索函数

函数足以完成当前行为，但每次调用都要重复传 Provider/Store，未来 RAG Query、RAG Chat
和 Tool 三个调用方容易形成重复组合代码。类只保存两个依赖，没有引入额外状态机。

### 未采用：SQL/Settings-aware Retriever

直接按 Knowledge Base 行选择 Provider/model/collection 会让基础检索器承担配置与数据库
职责，并要求本批新增 Session/error/API 组合。S1～S3 只要求可替换边界上的 Top-K 检索；
Knowledge Base 级运行配置可以在未来 service/dependency 层解决。

## 4. 公共接口

`backend/app/rag/retriever.py` 提供：

```python
class Retriever:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None: ...

    async def retrieve(
        self,
        *,
        query: str,
        knowledge_base_id: UUID,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> tuple[RetrievalResult, ...]: ...
```

同时提供 `RetrieverError`、`RetrieverInputError` 和 `RetrieverResponseError`。Provider
调用失败继续抛出既有 `EmbeddingProviderError` 子类；VectorStore 调用失败继续抛出既有
`VectorStoreError` 子类，避免丢失可测试的边界类别。

## 5. RetrievalResult 来源结构

`backend/app/schemas/rag.py` 新增不可变、`extra="forbid"` 的 Pydantic schema：

```python
class RetrievalResult(BaseModel):
    knowledge_base_id: UUID
    document_id: UUID
    chunk_id: UUID
    filename: str
    chunk_index: int
    content: str
    score: float
    heading: str | None
    page_number: int | None
    metadata: dict[str, JsonValue]
```

原文要求的五个字段全部保留；额外字段来自已经冻结的 Qdrant payload，直接支持后续来源
展示而不引入新的检索能力。UUID 在 Python 内保持强类型，`model_dump(mode="json")` 时输出
规范字符串。metadata 在映射时深复制，避免调用方修改结果后污染 VectorStore response。

## 6. 数据流与校验

```text
query + knowledge_base_id + top_k + score_threshold
  -> Retriever 输入校验（无外部调用）
  -> EmbeddingProvider.embed_query(query)
  -> 必须恰好返回 1 个有限向量
  -> 向量维度必须等于 VectorStore.dimension
  -> VectorSearchQuery(KB filter, vector, limit, threshold)
  -> VectorStore.search()
  -> 二次校验每个 payload 的 knowledge_base_id
  -> 按 VectorStore 返回顺序映射 RetrievalResult tuple
```

输入约束：

- query 必须是非空白字符串；只用于判空，不静默修改发送内容；
- `knowledge_base_id` 必须是 `UUID` 实例；
- `top_k` 必须是非 bool 的 int，范围 1～100，默认 5；
- threshold 必须是 `None` 或非 bool 的有限 int/float。

输入校验在 embedding 之前完成，避免无效参数触发潜在计费调用。零命中返回空 tuple，不是
异常。结果顺序完全保留 VectorStore 的相似度顺序，不在 Retriever 内重排、去重或 rerank。

## 7. 错误与安全

- 本地输入失败使用固定 `RetrieverInputError`，不包含 query 内容。
- query embedding 若不是恰好一个向量、或维度与 VectorStore 不同，使用固定
  `RetrieverResponseError`，不包含 query、vector、model、endpoint 或底层 cause。
- 任一结果越过请求 Knowledge Base，视为不可信组合响应并整体失败，不返回 partial results。
- Provider/VectorStore 的安全错误原样传播；本批没有 HTTP route，因此不新增 API status 映射。
- Retriever 不记录正文、向量或 credential，不读真实 `.env`、用户 SQLite 或真实 Provider。

## 8. TDD 与验证

先新增 `backend/tests/test_retriever.py` 并确认因模块/schema 缺失 RED，再实现最小 GREEN。
测试至少覆盖：

1. 默认 Top-5 查询、一次 query embedding、KB filter 与完整来源映射；
2. 自定义 Top-K/threshold 原样传递，零命中为空 tuple；
3. query、UUID、Top-K、threshold 严格校验且外部调用数为零；
4. query embedding 数量和维度不可信时不搜索；
5. 越过 Knowledge Base 的结果 fail closed；
6. Provider/VectorStore 错误类别不被错误包装；
7. metadata 防御性复制与 JSON 序列化。

matching verification 包括 Retriever/schema/Embedding/VectorStore focused tests。最终仍运行完整
backend、`pip check`、临时 SQLite Alembic 往返、frontend typecheck/test/build、Compose 与
Qdrant health、文档链接、secret/private-key、artifact、Plan boundary 和 Git allowlist/status。
真实 Qdrant 如用于 smoke，只创建精确随机前缀的临时 collection，使用确定性 Mock
Embedding，并在 `finally` 删除后复核残留为 0。

## 9. 文档与完成边界

同步 README 中英文、CHANGELOG、Architecture、Knowledge Base 设计和 Plan 3 执行表，明确
当前只完成可独立调用的 Retriever，不宣称 RAG Prompt/API/answer/Tool 可用。新增正式设计与
实施计划，不提前创建 `docs/23-naive-rag.md`；该文档随 S4～S6 的完整 Naive RAG API 再建立。

用户继续手动 stage/commit/push/tag。本批只准备经过验证的工作区和建议 commit message。
