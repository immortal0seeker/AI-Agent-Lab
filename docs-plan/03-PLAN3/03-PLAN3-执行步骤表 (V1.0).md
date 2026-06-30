# Plan 3 执行步骤表｜Document Ingestion + Naive RAG

> 适用文档：`00-ALL PLAN/03-PLAN-3 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P3-Mx-Sy` 顺序推进，除非 Codex 明确调整 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | 数据模型、Ingestion Pipeline、Embedding / Vector Store、Retriever / RAG API 完成后 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | 文档格式、上传限制、Qdrant 配置、RAG API、来源展示变化必须同步 docs 或 README |
| 禁止提前做 | Hybrid Search、Parent-Child、Rerank、Query Rewrite、Evaluation、Memory、Agentic RAG、OCR、多模态 |

推荐状态值：

```text
pending
doing
implemented
tested
reviewed
fixed
done
blocked
```

---

## 1. Plan 3 总览

| 阶段 | 里程碑 | 对应原 PLAN3 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 交接与知识库数据模型 | Step 1～4 | v0.2.0 检查、Qdrant 启动、KnowledgeBase / Document / Chunk / RAG Query 模型、KB API | 15～25 h | Codex | Codex + Claude Code |
| Phase 2 | M2 文档上传与解析 Pipeline | Step 5～8 | 文件上传、Markdown / TXT / PDF 文本解析、清洗、Chunking | 15～25 h | Codex + Cursor | Codex review |
| Phase 3 | M3 Embedding 与 Vector Store | Step 9～12 | Embedding Provider、OpenAI-compatible Embedding、Qdrant Vector Store、文档入库 Pipeline | 20～30 h | Codex | Codex + Claude Code |
| Phase 4 | M4 Retriever 与 Naive RAG API | Step 13～17 | Retriever、RAG Prompt、RAG Query API、RAG Chat API、search_knowledge_base 工具 | 15～25 h | Codex | Codex + Claude Code |
| Phase 5 | M5 前端知识库与 RAG Chat | Step 18～19 | 知识库页面、文档上传 UI、RAG Chat、来源展示 | 15～25 h | Cursor + Codex | Codex review |
| Phase 6 | M6 测试、文档与封版 | Step 20～22 | RAG 测试、README、docs、截图、CHANGELOG、v0.3.0 tag | 10～20 h | Codex + Cursor | Codex + Claude Code |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 |
|---|---|---|---|
| Batch 1 | P3-M1-S1～S3 | 确认 Plan2 地基，接入 Qdrant 配置 | 跑现有测试和 Qdrant health |
| Batch 2 | P3-M1-S4～S6 | 建立知识库核心数据模型 | 数据库迁移和模型测试 |
| Batch 3 | P3-M1-S7～S9 | 实现 Knowledge Base API | API 测试，Codex + Claude review M1 |
| Batch 4 | P3-M2-S1～S3 | 实现文件上传和存储 | 上传 API 测试 |
| Batch 5 | P3-M2-S4～S6 | 实现 Markdown / TXT / PDF 文本解析 | Parser 测试 |
| Batch 6 | P3-M2-S7～S9 | 实现文本清洗和 Chunking | Chunking 测试，Codex review M2 |
| Batch 7 | P3-M3-S1～S3 | 实现 Embedding Provider 抽象 | mock embedding 测试 |
| Batch 8 | P3-M3-S4～S6 | 实现 OpenAI-compatible Embedding 和配置 | provider 测试 |
| Batch 9 | P3-M3-S7～S9 | 实现 Qdrant Vector Store | vector store 测试 |
| Batch 10 | P3-M3-S10～S12 | 实现文档入库 Pipeline | 端到端入库测试，Codex + Claude review M3 |
| Batch 11 | P3-M4-S1～S3 | 实现 Retriever 和 RAG Prompt | 检索 + prompt 测试 |
| Batch 12 | P3-M4-S4～S6 | 实现 RAG Query / Chat API | API 测试 |
| Batch 13 | P3-M4-S7～S8 | 注册 search_knowledge_base 工具 | Agent 工具调用测试，Codex + Claude review M4 |
| Batch 14 | P3-M5-S1～S3 | 实现知识库页面和上传 UI | 浏览器手测 |
| Batch 15 | P3-M5-S4～S6 | 实现 RAG Chat 和来源展示 | 浏览器手测，Codex review M5 |
| Batch 16 | P3-M6-S1～S6 | 测试、文档、截图、封版 | Codex + Claude final review |

---

## 3. Phase 1｜M1 交接与知识库数据模型

阶段目标：

```text
确认 v0.2.0 Tool Calling 底座稳定，启动 Qdrant，并建立 Knowledge Base、Document、DocumentChunk、RAG Query 的数据模型和基础 API。
```

阶段验收：

```text
1. Plan 2 的 Tool Registry、read_file、list_dir、Simple Agent Loop 仍可用
2. Qdrant 可以通过 Docker Compose 或本地配置启动
3. knowledge_bases / documents / document_chunks / rag_queries 数据模型可用
4. Knowledge Base API 可以创建、查询、更新、删除知识库
5. 数据模型保留 Plan 4 需要的 metadata / status / hash / vector_id 扩展点
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M1-S1 | 检查 Plan 2 封版状态和 v0.2.0 tag | Codex | Plan 2 验收记录 | Chat、Tool Registry、read_file、list_dir、Agent API 均可用或有明确证据 | Codex |
| P3-M1-S2 | 配置 Qdrant 服务和环境变量 | Codex | `docker-compose.yml`、`.env.example`、Qdrant settings | Qdrant health 可访问 | Codex |
| P3-M1-S3 | 创建 RAG / Knowledge 目录结构 | Codex | `backend/app/rag/`、`backend/app/knowledge/` 或约定目录 | 目录结构符合 PLAN3 推荐边界 | Codex |
| P3-M1-S4 | 创建 KnowledgeBase ORM / schema | Codex | `KnowledgeBase` 模型和 schema | 模型测试通过 | Codex |
| P3-M1-S5 | 创建 Document ORM / schema | Codex | `Document` 模型和 schema | 支持 filename、file_type、file_path、hash、parse_status、metadata | Codex |
| P3-M1-S6 | 创建 DocumentChunk 和 RagQuery ORM / schema | Codex | `DocumentChunk`、`RagQuery` 模型和 schema | 包含 document_id、chunk_index、content、metadata、vector_id | Claude Code 可审 |
| P3-M1-S7 | 实现 Knowledge Base Service | Codex | `knowledge_base_service.py` | 创建、列表、详情、更新、删除测试通过 | Codex |
| P3-M1-S8 | 实现 Knowledge Base API | Codex | `api/v1/knowledge_bases.py` | API 测试通过，OpenAPI 可见 | Codex |
| P3-M1-S9 | 完成 M1 review 和数据模型文档 | Codex | `docs/20-knowledge-base-design.md` 初版 | 文档说明表结构、状态字段、扩展点 | Codex + Claude review |

M1 完成后建议 commit：

```text
feat(rag): add knowledge base models and api
```

---

## 4. Phase 2｜M2 文档上传与解析 Pipeline

阶段目标：

```text
实现文档上传、文件存储、Markdown / TXT / PDF 文本解析、文本清洗和基础 Chunking。
```

阶段验收：

```text
1. 可以上传 Markdown / TXT / 文本型 PDF
2. 文档文件保存到受控目录
3. Document 记录 parse_status、file_hash、file_type、metadata
4. Parser 输出 ParsedDocument
5. Text Cleaner 和 Chunker 可单独测试
6. 解析失败不会导致系统崩溃，Document 状态可见
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M2-S1 | 实现文件上传存储策略 | Codex | `document_storage.py` | 文件保存到受控目录，文件名冲突安全处理 | Codex |
| P3-M2-S2 | 实现 Document Upload API | Codex | `api/v1/documents.py` 上传接口 | 上传 Markdown / TXT 返回 Document 记录 | Codex |
| P3-M2-S3 | 添加文件类型、大小、hash 校验 | Codex | 上传校验逻辑 | 超大文件、未知类型、重复文件测试通过 | Codex |
| P3-M2-S4 | 实现 Markdown Parser | Codex | `parsers/markdown_parser.py` | Markdown 标题、正文、代码块提取测试通过 | Codex |
| P3-M2-S5 | 实现 TXT Parser | Codex | `parsers/txt_parser.py` | TXT 文本读取和编码处理测试通过 | Codex |
| P3-M2-S6 | 实现文本型 PDF Parser | Codex | `parsers/pdf_parser.py` | 文本型 PDF 可提取文本；扫描 PDF 返回可读限制说明 | Codex |
| P3-M2-S7 | 实现 Text Cleaner | Codex | `text_cleaner.py` | 空白、重复换行、不可见字符清洗测试通过 | Codex |
| P3-M2-S8 | 实现 Chunker | Codex | `chunker.py` | chunk_size、overlap、chunk_index、token_count 测试通过 | Claude Code 可审 |
| P3-M2-S9 | 串联解析、清洗、切分并更新 Document 状态 | Codex | parser pipeline 初版 | 上传后可生成 DocumentChunk 记录 | Codex review |

M2 完成后建议 commit：

```text
feat(rag): add document upload parsing and chunking
```

---

## 5. Phase 3｜M3 Embedding 与 Vector Store

阶段目标：

```text
建立 Embedding Provider 抽象、OpenAI-compatible Embedding Provider、Qdrant Vector Store，并完成文档入库 Pipeline。
```

阶段验收：

```text
1. Embedding Provider 可替换
2. OpenAI-compatible Embedding Provider 可配置模型和维度
3. Qdrant collection 可创建和检查
4. document_chunks 可以写入 Qdrant
5. Qdrant payload 包含 knowledge_base_id、document_id、chunk_id、metadata
6. 文档入库 Pipeline 从上传文件走到向量写入
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M3-S1 | 设计 EmbeddingProvider 抽象 | Codex | `providers/embedding/base.py` | mock provider 测试通过 | Claude Code 可审 |
| P3-M3-S2 | 定义 EmbeddingResult 和 batch embed 接口 | Codex | embedding schema / dataclass | 批量输入返回向量和 token usage | Codex |
| P3-M3-S3 | 实现 Embedding Provider Registry | Codex | `providers/embedding/registry.py` | 可按配置选择 provider | Codex |
| P3-M3-S4 | 实现 OpenAI-compatible Embedding Provider | Codex | `openai_compatible_embedding.py` | mock HTTP 或测试替身验证请求和响应解析 | Codex |
| P3-M3-S5 | 增加 embedding 配置和错误处理 | Codex | config、provider 初始化逻辑 | 缺少 key 或模型维度不匹配时返回可读错误 | Codex |
| P3-M3-S6 | 补 Embedding Provider 文档 | Codex | `docs/21-embedding-provider.md` | 文档说明配置、模型、维度、成本注意事项 | Codex |
| P3-M3-S7 | 设计 VectorStore 抽象 | Codex | `vectorstores/base.py` | mock vector store 测试通过 | Claude Code 可审 |
| P3-M3-S8 | 实现 Qdrant Vector Store | Codex | `vectorstores/qdrant_store.py` | collection 创建、upsert、search 测试通过 | Codex |
| P3-M3-S9 | 定义 Qdrant payload 规范 | Codex | payload builder | payload 包含 Plan 4 所需字段 | Codex |
| P3-M3-S10 | 实现文档入库 Pipeline | Codex | `ingestion_pipeline.py` | 上传文档后完成 parse、chunk、embed、upsert | Codex |
| P3-M3-S11 | 持久化 chunk vector_id 和 ingest 状态 | Codex | chunk 更新逻辑 | 数据库 chunk 记录关联 Qdrant point id | Codex |
| P3-M3-S12 | 完成 M3 review 和入库文档 | Codex | `docs/22-document-ingestion-pipeline.md` | 端到端入库测试通过 | Codex + Claude review |

M3 完成后建议 commit：

```text
feat(rag): add embedding provider vector store and ingestion pipeline
```

---

## 6. Phase 4｜M4 Retriever 与 Naive RAG API

阶段目标：

```text
实现 Top-K Retriever、RAG Prompt、RAG Query API、RAG Chat API，并把知识库检索注册成 Tool。
```

阶段验收：

```text
1. Retriever 可以按 query 检索相关 chunk
2. RAG Prompt 独立封装，便于 PLAN4 优化
3. RAG Query API 返回 answer、sources、retrieval metadata
4. RAG Chat API 可以复用会话系统
5. rag_queries 或等价查询记录可用
6. search_knowledge_base 工具可以被 Plan 2 的 Agent Loop 调用
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M4-S1 | 实现 Retriever | Codex | `retriever.py` | 给定 query 返回 Top-K RetrievalResult | Claude Code 可审 |
| P3-M4-S2 | 实现检索 metadata 和来源结构 | Codex | `RetrievalResult` schema | 返回 chunk_id、document_id、score、content、metadata | Codex |
| P3-M4-S3 | 补 Retriever 测试 | Codex | retriever tests | mock vector store 检索测试通过 | Codex |
| P3-M4-S4 | 实现 RAG Prompt 模板 | Codex | `prompts/rag_prompt.md` 或 prompt builder | Prompt 包含问题、上下文、来源约束 | Codex |
| P3-M4-S5 | 实现 RAG Query Service 和 API | Codex | `rag_service.py`、`api/v1/rag.py` | API 返回 answer、sources、metadata | Codex |
| P3-M4-S6 | 实现 RAG Chat API | Codex | rag chat endpoint | 能把 RAG 回答写入会话历史 | Codex |
| P3-M4-S7 | 实现 rag_queries 记录 | Codex | 查询记录写入逻辑 | 记录 query、knowledge_base_id、top_k、source ids、latency | Codex |
| P3-M4-S8 | 注册 search_knowledge_base 工具 | Codex | `tools/builtin/search_knowledge_base.py` | Agent 可调用 RAG Tool 返回检索结果 | Codex + Claude review |

M4 完成后建议 commit：

```text
feat(rag): add naive rag query chat and tool integration
```

---

## 7. Phase 5｜M5 前端知识库与 RAG Chat

阶段目标：

```text
实现知识库管理页面、文档上传页面、RAG Chat 页面和来源片段展示，让 Plan 3 成为可展示的 MVP。
```

阶段验收：

```text
1. 前端可以创建和查看知识库
2. 前端可以上传 Markdown / TXT / PDF
3. 前端可以查看文档解析 / 入库状态
4. 前端可以基于知识库提问
5. 前端可以展示回答和来源片段
6. 典型验收场景可以完整跑通
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M5-S1 | 创建前端 Knowledge Base API 封装和类型 | Cursor | `frontend/src/api/knowledge.ts`、types | TypeScript 检查通过 | Codex |
| P3-M5-S2 | 实现知识库列表和创建页面 | Cursor | `KnowledgeBasePage.tsx` | 可创建、查看知识库 | Codex |
| P3-M5-S3 | 实现文档上传和状态展示 | Cursor | Document upload component | 可上传文件并显示 parse / ingest 状态 | Codex |
| P3-M5-S4 | 创建前端 RAG API 封装和 store | Cursor | `api/rag.ts`、rag store | TypeScript 检查通过 | Codex |
| P3-M5-S5 | 实现 RAG Chat 页面 | Cursor | `RagChatPage.tsx` | 可选择知识库并提问 | Codex |
| P3-M5-S6 | 实现来源片段展示组件 | Cursor | `SourceCitationList.tsx`、source cards | 展示文档名、chunk 片段、score、metadata | Codex review |

M5 完成后建议 commit：

```text
feat(frontend): add knowledge base and rag chat pages
```

---

## 8. Phase 6｜M6 测试、文档与封版

阶段目标：

```text
补齐 Plan 3 的测试、文档、截图、CHANGELOG 和 v0.3.0 tag，让它成为第一个真正可展示的 AI 应用 MVP。
```

阶段验收：

```text
1. Knowledge Base / Document / Chunk / RAG API 有核心测试
2. Parser / Cleaner / Chunker / Embedding / Vector Store / Retriever 有测试
3. 前端知识库和 RAG Chat 通过手动或 smoke 验证
4. README 和 docs 说明上传、入库、RAG 问答、限制
5. CHANGELOG 记录 v0.3.0
6. 创建 v0.3.0 tag
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M6-S1 | 补数据模型、Knowledge Base API、Document API 测试 | Codex | 后端测试 | `pytest` 对应测试通过 | Codex |
| P3-M6-S2 | 补 Parser、Cleaner、Chunker 测试 | Codex | 文档处理测试 | Markdown / TXT / PDF 文本型样例通过 | Codex |
| P3-M6-S3 | 补 Embedding、Vector Store、Ingestion、Retriever 测试 | Codex | RAG pipeline 测试 | mock embedding + test Qdrant 或 mock vector store 通过 | Codex |
| P3-M6-S4 | 补 RAG Query / Chat / Tool 测试 | Codex | RAG API 和 Tool 测试 | 检索、回答、来源、rag_queries 记录通过 | Codex |
| P3-M6-S5 | 补前端检查和 Demo 验证 | Cursor + Codex | 前端 build、截图、手动验证记录 | 上传文档、提问、展示来源可跑通 | Codex |
| P3-M6-S6 | 更新 README、docs、CHANGELOG、创建 v0.3.0 tag | Codex + Claude Code | 文档、截图、tag、桥接检查表 | 全量测试通过，tag 存在 | Codex + Claude final review |

M6 完成后建议 commit：

```text
chore: release v0.3.0 naive rag
```

---

## 9. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P3-Mx-Sy ～ P3-Mx-Sz
必须遵守：只做这些 Step，不提前做 Hybrid Search、Rerank、Evaluation、Memory 或多模态
完成要求：
1. 实现对应交付物
2. 跑对应验证命令
3. 修复发现的问题
4. 更新必要文档
5. 给出变更摘要和测试结果
```

执行完成后，Codex review 使用这个检查表：

```text
1. 是否只改了本批次相关文件
2. 是否引入超出 Plan 3 的 Advanced RAG 能力
3. 是否破坏 Plan 1 Chat 或 Plan 2 Tool Calling
4. RAG 模块是否保持 Provider / Vector Store / Retriever 可替换
5. metadata、source、vector_id 是否保留 Plan 4 扩展点
6. 是否有测试或手动验证证据
7. 是否同步 README / docs / env example
8. 是否适合进入下一批次
```

---

## 10. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | 数据模型是否能支撑 Plan 4 的 Trace / Advanced RAG | diff、ORM、schema、API、测试结果 |
| M3 结束 | Embedding / Vector Store / Ingestion 抽象是否稳定 | diff、provider、vector store、pipeline、payload 规范、测试结果 |
| M4 结束 | Retriever / RAG API / Tool 集成是否可扩展 | diff、retriever、prompt、RAG API、search_knowledge_base、测试结果 |
| M6 封版前 | v0.3.0 是否能作为 Plan 4 的工程化 RAG 底座 | 全量 diff、README、测试结果、CHANGELOG、桥接检查 |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
```

---

## 11. Plan 3 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| Qdrant 可启动 | pending | Qdrant health 输出 |
| Knowledge Base 数据模型完成 | pending | ORM / migration / test |
| Document 数据模型完成 | pending | ORM / migration / test |
| DocumentChunk 数据模型完成 | pending | ORM / migration / test |
| 可以创建知识库 | pending | API 测试或页面截图 |
| 可以上传 Markdown | pending | 上传验证记录 |
| 可以上传 TXT | pending | 上传验证记录 |
| 可以上传文本型 PDF | pending | 上传验证记录 |
| 可以解析文档 | pending | parser 测试 |
| 可以清洗文本 | pending | cleaner 测试 |
| 可以切分 Chunk | pending | chunker 测试 |
| 可以调用 Embedding Provider | pending | provider 测试 |
| 可以写入 Qdrant | pending | vector store 测试 |
| 可以基于 query 检索 Chunk | pending | retriever 测试 |
| 可以基于检索结果生成回答 | pending | RAG API 测试 |
| 前端可以上传文档 | pending | 页面截图 |
| 前端可以查看文档状态 | pending | 页面截图 |
| 前端可以进行 RAG Chat | pending | 页面截图 |
| 前端可以展示来源片段 | pending | 页面截图 |
| search_knowledge_base 工具可用 | pending | Agent Tool 测试 |
| README 已更新 | pending | README 链接 |
| docs 已更新 | pending | docs 链接 |
| 已创建 v0.3.0 tag | pending | `git tag --list` 输出 |

---

## 12. Plan 3 到 Plan 4 的桥接检查

只有下面 5 项都满足，才建议进入 Plan 4：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| `search_knowledge_base` 工具可用 | pending | 后续 Agent 和 Trace 能统一观察 RAG 调用 |
| `rag_queries` 或等价查询记录可用 | pending | Plan 4 可以扩展为检索 Trace |
| `document_chunks` 至少包含 document_id、chunk_index、content、metadata、vector_id | pending | Parent-Child / metadata filter / rerank 都依赖这些字段 |
| RAG Query API 返回 answer、sources、retrieval metadata | pending | Evaluation 和 Trace 需要统一结果结构 |
| Qdrant payload 中保留 knowledge_base_id、document_id、chunk_id | pending | Plan 4 的过滤、来源展示、检索记录都依赖 payload |

---

## 13. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| Knowledge Base API | `backend/app/api/v1/knowledge_bases.py` |
| Document API | `backend/app/api/v1/documents.py` |
| RAG API | `backend/app/api/v1/rag.py` |
| 数据模型 | `backend/app/models/knowledge_base.py`、`document.py`、`document_chunk.py`、`rag_query.py` |
| 文档处理 | `backend/app/rag/parsers/`、`text_cleaner.py`、`chunker.py` |
| Embedding Provider | `backend/app/providers/embedding/` |
| Vector Store | `backend/app/rag/vectorstores/` |
| Ingestion Pipeline | `backend/app/rag/ingestion_pipeline.py` |
| Retriever | `backend/app/rag/retriever.py` |
| RAG Prompt | `backend/app/prompts/rag_prompt.md` 或 `backend/app/rag/prompt_builder.py` |
| RAG Tool | `backend/app/tools/builtin/search_knowledge_base.py` |
| 后端测试 | `backend/tests/rag/`、`backend/tests/knowledge/` |
| 前端知识库页面 | `frontend/src/pages/KnowledgeBasePage.tsx` |
| 前端 RAG 页面 | `frontend/src/pages/RagChatPage.tsx` |
| 前端来源组件 | `frontend/src/components/rag/` |
| 项目文档 | `docs/20-knowledge-base-design.md`、`docs/21-embedding-provider.md`、`docs/22-document-ingestion-pipeline.md`、`docs/23-naive-rag.md` |
| 截图 | `docs/assets/plan3/` |

---

## 14. 执行建议

Plan 3 的重点不是追求“最强 RAG”，而是把 Naive RAG 的工程链路做完整、可观察、可扩展。

推荐实际推进方式：

```text
先做 Knowledge Base 和文档数据模型
再做上传、解析、清洗、Chunking
再做 Embedding 和 Qdrant 入库
再做 Retriever、RAG Prompt 和 RAG API
再接前端页面和 search_knowledge_base 工具
最后补测试、文档、截图和 v0.3.0 封版
```

不要在 Plan 3 阶段提前优化检索策略。

Plan 3 做稳之后，Plan 4 才能自然地在同一套 Retriever、Vector Store、Prompt、RAG Query 记录上增加 Trace、Hybrid Search、Rerank 和 Evaluation。
