# Plan 3 M3 S10～S12 文档向量入库设计

## Status

- Scope: `P3-M3-S10～P3-M3-S12`
- Date: 2026-08-01
- Selected approach: 独立异步向量化 pipeline、现有 service 持久化状态、请求事务执行向量补偿
- Design approval: 用户已要求开始执行仓库内既定 Plan 3 Step，无需重复确认正常范围内操作
- Implementation status: complete; matching verification and Codex self-review passed

## 1. 目标

在现有同步上传、解析、清洗、Chunking、EmbeddingProvider 和 VectorStore 之上，完成
Plan 3 M3 的最后一段链路：上传成功后批量生成 Chunk embeddings、写入 Qdrant、把
point ID 回写到 `DocumentChunk.vector_id`，并将 `Document.embedding_status` 更新为
`ready`。预期的解析、切分、Provider 或 Vector Store 失败应留下可读且不泄密的失败
状态；非预期数据库/存储错误继续交给请求事务回滚。

本批完成 M3 review 和正式入库文档，但不实现 Retriever、RAG Prompt、RAG API、
Agent Tool、前端页面或任何 Advanced RAG / Plan 4+ 能力。

## 2. 验收映射

| Step | 验收要求 | 设计响应 |
|---|---|---|
| S10 | `ingestion_pipeline.py`；上传后完成 parse、chunk、embed、upsert | 新增只依赖 `EmbeddingProvider` 与 `VectorStore` 的异步向量化 pipeline，现有 `DocumentIngestionService` 在 Chunk flush 后调用它 |
| S11 | Chunk 记录关联 Qdrant point ID；持久化 ingest 状态 | point ID 固定为 Chunk UUID 的规范字符串；成功时全部回写并标记 `ready`，失败时不留下 partial IDs 并标记 `failed` |
| S12 | `docs/22-document-ingestion-pipeline.md`；端到端入库测试和 M3 review | 使用临时 SQLite/文件、Mock Embedding 与 Mock/临时真实 Qdrant 完整验收；新增正式文档和 M3 review |

## 3. 方案比较

### 采用：独立 pipeline + service 状态编排 + 请求事务补偿

`app.rag.ingestion_pipeline` 只负责外部向量化契约：检查 collection、批量 embed、验证
结果数量与维度、构建 `VectorPoint`、upsert，并验证返回 point IDs。它不持有 SQLAlchemy
Session，也不写 ORM 状态。`DocumentIngestionService` 继续拥有 parse/clean/chunk 和
Document/Chunk 状态迁移，因 Embedding 和 Vector Store 均为异步接口，服务入口调整为
异步并由现有上传 service `await`。

Qdrant upsert 与 SQLite commit 不能形成原子事务。请求 Session 在成功 upsert 后登记一个
异步 rollback callback；若后续 flush/commit 失败，先回滚 SQLite 和文件，再按
Knowledge Base + Document 双 ownership filter best-effort 删除本次 vectors。事务完成后
再关闭请求创建的 Qdrant client。该设计覆盖普通异常与 commit failure，但进程硬崩溃仍
可能留下 orphan points，记录为本地 MVP 限制。

### 未采用：全部逻辑直接放入 DocumentIngestionService

该方案文件较少，但 Provider 结果校验、Qdrant 补偿和 ORM 状态混在一个类中，无法独立
验证 execution table 要求的 `ingestion_pipeline.py`，也会让未来 Retriever 或重入任务
难以复用向量化边界。

### 未采用：后台队列、outbox 或两阶段任务表

该方案可以进一步缩短上传请求并改善 crash recovery，但 Plan 3 原文明确允许初版同步
执行；引入 Worker、重试状态机或 outbox 会扩张到后续工程化范围。

## 4. 组件与接口

### `app.rag.ingestion_pipeline`

提供：

```python
async def ingest_document_vectors(
    *,
    document: Document,
    chunks: list[DocumentChunk],
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
) -> tuple[UUID, ...]:
    ...
```

输入必须为一个非空、顺序固定且 ownership 一致的 Chunk 列表。pipeline 先
`ensure_collection()`，再用全部 Chunk content 调用一次 `embed_texts()`。返回 vector
数量必须与 Chunk 数一致，维度必须与 Vector Store 一致；每个 point ID 使用对应
`chunk.id`，payload 由既有 `build_qdrant_payload()` 构建。`upsert()` 返回 ID 必须与输入
顺序和集合完全一致，否则视为不可信响应并删除该 Document 的 vectors。

Embedding 异常继续使用既有 `EmbeddingProviderError` 层级；Vector Store 异常继续使用
既有 `VectorStoreError` 层级。pipeline 不复制文本、向量、endpoint、响应 body 或底层
异常诊断。

### `DocumentIngestionService`

状态迁移冻结为：

```text
uploaded/pending/pending
  -> parsing/pending/pending
  -> parsed/chunking/pending
  -> parsed/chunked/embedding
  -> parsed/chunked/ready
```

预期失败：

- parse 失败：`failed/failed/failed`；
- chunk 失败：`parsed/failed/failed`；
- embedding 或 vector 失败：`parsed/chunked/failed`，Chunk 保留、`vector_id` 全为空；
- 成功：`parsed/chunked/ready`，每个 `vector_id == str(chunk.id)`。

Provider/Vector Store 失败保存固定安全消息，而不是直接保存异常字符串。存储解析路径错误、
SQLAlchemy 错误和其他非预期异常继续向上冒泡，交给请求事务 owner rollback。

### 请求依赖与事务 callback

新增可注入的 `get_embedding_provider()` 与 `get_vector_store()`，生产默认使用当前 Settings、
OpenAI-compatible factory 和 Qdrant factory；测试覆盖只注入完整的 Mock Provider/Store，
不调用真实 Provider。Qdrant Store 的 `close()` 注册为事务 finalizer，确保发生 commit 或
rollback 后才关闭客户端。

Session callback 只保存异步 callable，不保存 secret、content 或 vector。rollback callback
失败不能覆盖原始数据库异常，只写安全日志；成功 commit 会丢弃 rollback callback。

## 5. 数据与一致性

不新增 ORM 字段或 Alembic migration。`DocumentChunk.vector_id`、Document 三组状态字段和
现有约束已满足 S11。SQLite 继续是 Document/Chunk/status 的主事实源；Qdrant 只保存向量
及检索 payload。

只有在整个 upsert 返回成功且 ID 契约通过后才回写 `vector_id`。任何预期外部失败均先将
全部 Chunk `vector_id` 保持/恢复为 `None`，再 flush `embedding_status=failed`。成功 upsert
后先登记 rollback cleanup，再 flush ready 状态，避免数据库失败时没有补偿信息。

## 6. API 与错误行为

现有上传 route 保持不变且仍返回 HTTP 201 `DocumentRead`：

- 全链路成功返回 `embedding_status=ready`；
- 内容、Embedding 或 Vector Store 的预期运行时失败返回已持久化的 201 failed Document；
- Provider/Vector Store 在依赖初始化阶段的配置错误发生在读取上传 stream 前，映射为安全
  HTTP 503；
- 非预期存储/数据库故障仍使用既有 503，并回滚 Document、Chunks、文件和已登记 vectors。

本批不增加查询、重试、重新入库或删除 Document API。

## 7. 测试策略

按 TDD 分三组 RED/GREEN：

1. pipeline 单元测试先因模块缺失 RED，覆盖成功、数量/维度/ownership/返回 ID、upsert
   异常补偿；
2. service 状态与事务 callback 测试先因异步签名和依赖缺失 RED，覆盖 ready、三类失败、
   vector_id 全有或全无、commit failure 清理；
3. API 端到端先因仍返回 pending RED，使用临时 SQLite/文件和完整 Mock Provider/Store，
   验证上传响应、数据库与向量 payload 一致。

最终使用随机 `codex_p3_m3_s10_s12_*` collection、临时 SQLite、临时文件和确定性 Mock
Embedding 运行真实 Qdrant smoke；`finally` 精确删除本批临时 collection。另运行 backend
全量、依赖检查、临时 Alembic 往返、frontend typecheck/test/build、Compose/health、文档
链接、secret、artifact、Plan boundary、Git diff/status 和 Codex self-review。

## 8. 范围边界与限制

### Included

- 同步上传内的 parse/clean/chunk/embed/upsert 全链路；
- Chunk point ID 回写、Document embedding 状态与安全错误；
- 请求级 Qdrant rollback compensation 和客户端 lifecycle；
- Mock 端到端与临时真实 Qdrant 入库 smoke；
- `docs/22-document-ingestion-pipeline.md`、M3 review、README/架构/CHANGELOG/执行表同步。

### Excluded

- 自动 batching、retry/backoff、缓存、并发 re-ingestion、后台 Worker/outbox、hard-crash
  reconciliation；
- 真实付费 Embedding Provider 连通、质量、价格或模型可用性验收；
- Document 查询/删除/重新入库 API 与前端；
- Retriever、metadata filtering、Hybrid Search、Parent-Child、Rerank、Evaluation、Trace、
  Memory、OCR、multimodal 或其他 Plan 4+ runtime。
