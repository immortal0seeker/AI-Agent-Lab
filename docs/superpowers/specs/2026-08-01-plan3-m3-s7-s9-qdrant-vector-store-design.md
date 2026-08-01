# Plan 3 M3 S7～S9 Qdrant Vector Store 设计

## Status

- Scope: `P3-M3-S7～P3-M3-S9`
- Date: 2026-08-01
- Selected approach: 官方异步 Qdrant 客户端、仓库自有窄接口、客户端注入
- Design approval: 用户已要求开始执行仓库内既定 Plan 3 Step
- Implementation status: complete; full verification, live Qdrant smoke, and Codex self-review passed

## 1. 目标

在现有 Embedding Provider、Document 和 DocumentChunk 契约之上，增加一个可替换、
异步、面向 Naive RAG 的 VectorStore 边界，并实现 Qdrant 适配器。适配器负责检查或
创建 COSINE collection、写入 Chunk 向量、按 Knowledge Base 过滤检索，以及按
Document 过滤删除向量。

本批同时冻结 Chunk payload 规范，使后续 M4 Retriever 无需再次读取或猜测来源字段
即可构造包含 content 和 source metadata 的 `RetrievalResult`。本批不串联上传与
Embedding，不更新 SQLite 的 `vector_id` 或 Document ingestion 状态。

## 2. 验收映射

| Step | 验收要求 | 设计响应 |
|---|---|---|
| S7 | `vectorstores/base.py`，mock vector store 测试通过 | 在 `app/rag/vectorstores/` 定义异步 `VectorStore`、collection/point/query/result 契约和稳定错误层级，并用内存测试替身验证可替换性 |
| S8 | collection 创建、upsert、search 测试通过 | 使用官方 `AsyncQdrantClient` 1.15.x；检查现有 collection 的维度和 COSINE 距离，upsert 使用 `wait=True`，search 强制 Knowledge Base filter，并实现 Plan Step 11 指定的 Document 向量删除 |
| S9 | payload 包含 Plan 4 所需字段 | `payload.py` 生成 `knowledge_base_id`、`document_id`、`chunk_id`、`metadata`，并保存 `filename`、`chunk_index`、`content`、`heading`、`page_number` |

## 3. 方案选择

### 采用：官方异步客户端 + 窄接口 + 注入

生产适配器依赖 `qdrant-client>=1.15.1,<1.16.0`，与 Compose 固定的 Qdrant
`v1.15.4` 保持同一 minor。业务层只依赖仓库自己的 `VectorStore`、`VectorPoint`、
`VectorSearchQuery` 和 `VectorSearchResult`，不会接触 Qdrant response shape。

客户端可注入，使单元测试只替换网络边界，同时仍检查真实 Qdrant model 的 collection
参数、PointStruct、Filter 和 QueryResponse 映射。默认使用异步客户端，避免在未来的
异步 ingestion/Retriever 路径中阻塞事件循环。

未采用原始 HTTP，因为这会在仓库中复制 Qdrant OpenAPI 模型、兼容性和错误处理。未
采用同步客户端，因为它与现有异步 Provider/RAG 方向不一致。未采用 Qdrant local mode
作为生产实现，因为项目已经明确用 Compose Qdrant 作为 Plan 3 向量服务；local mode
只适合测试或原型，不能替代本批真实容器 smoke。

## 4. VectorStore 契约

`VectorStore` 提供以下异步操作：

- `ensure_collection()`：collection 不存在时创建，存在时检查 dimension 和 COSINE；
- `upsert(points)`：一次写入非空、同维度的 Chunk point，并返回规范 point IDs；
- `search(query)`：按 `knowledge_base_id` 过滤并返回有序结果；
- `delete_document_vectors(knowledge_base_id, document_id)`：只删除指定 ownership
  范围内的 points；
- `close()`：关闭由 store 自己创建的客户端；注入客户端仍由注入方管理。

`VectorPoint` 使用 Chunk UUID 作为 point ID，向量必须非空、数值、有限且不能包含
bool。`VectorSearchQuery` 要求非空有限向量，`limit` 为 1～100，可选 score threshold
也必须有限。`VectorSearchResult` 保存 UUID point ID、有限 score 和经过完整校验的
Chunk payload。Qdrant adapter 在 upsert 和 query 前再次检查向量维度与 collection
配置一致，维度不匹配时不会发出写入或检索请求。

## 5. Collection 与配置

新增惰性配置：

```text
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=ai_agent_lab_chunks
QDRANT_TIMEOUT_SECONDS=10
```

应用启动仍不连接 Qdrant。只有初始化具体 store 后调用方法才访问服务。factory 使用
Embedding 的已配置 dimension；若 dimension 缺失、URL/collection name/timeout 无效，
返回可读的 `VectorStoreConfigurationError`。Knowledge Base 的可选
`vector_collection_name` 可在未来 ingestion 初始化 store 时显式覆盖默认 collection。

collection 使用单个默认 dense vector 和 COSINE distance。若已有 collection 使用
named vectors、不同 dimension 或不同 distance，适配器 fail-closed，不自动重建、迁移
或删除 collection。collection 创建后也会读取配置复核，避免把服务端拒绝或并发状态
误判为成功。

## 6. Payload 规范

每个 point payload 固定为：

```json
{
  "knowledge_base_id": "00000000-0000-0000-0000-000000000001",
  "document_id": "00000000-0000-0000-0000-000000000002",
  "chunk_id": "00000000-0000-0000-0000-000000000003",
  "filename": "README.md",
  "chunk_index": 0,
  "content": "chunk text",
  "heading": "项目介绍",
  "page_number": null,
  "metadata": {"source_format": "md", "start_char": 0, "end_char": 10}
}
```

UUID 始终序列化为小写规范字符串。builder 验证 Document、Chunk 和 Knowledge Base
ownership 一致；filename、content、index、heading、page 和 metadata 沿用当前 ORM/
schema 边界。metadata 必须是完整 JSON-safe object，拒绝 NaN、Infinity、任意 Python
对象或非字符串 key。

`content` 虽未出现在旧版 payload 示例中，但 M4 的 `RetrievalResult` 和 RAG Prompt
明确要求返回 chunk content。把它作为本批 Plan 4 bridge 字段可避免 M4 每个命中再做
SQLite N+1 查询，同时不引入 Retriever 或 RAG runtime。

## 7. 搜索、删除与安全边界

search 永远附加 `knowledge_base_id` 精确匹配 filter，并请求 payload、不请求 vectors。
delete 同时匹配 `knowledge_base_id` 与 `document_id`，避免错误 UUID 跨 Knowledge Base
删除。两种操作均不实现 Hybrid Search、metadata filtering UI、rerank 或 evaluation。

Qdrant SDK/网络异常会转换为固定、可测试的 `VectorStoreOperationError`，不复制 URL、
响应 body、payload、content、向量或内部诊断，且不保留可被 traceback 展示的异常 cause。
Qdrant 成功响应若包含非 UUID point、非有限 score、缺失/额外/无效 payload、
point/chunk ID 不一致、越过请求 Knowledge Base 的 payload，或非 `completed` write
status，则转换为 `VectorStoreResponseError`。本地输入和 collection 配置错误使用独立
类型。

tracked 配置不包含 Qdrant key。本地 Compose 无鉴权，只绑定 `127.0.0.1:6333` 并禁用
遥测；本批不增加远端 Qdrant secret 管理，也不调用付费 Provider。

## 8. 范围边界

### Included

- VectorStore 抽象、输入/结果和错误契约；
- Qdrant 1.15.x 异步 adapter 与配置 factory；
- collection create/check、upsert、Knowledge Base search、Document delete；
- Chunk payload model/builder；
- mock 网络单元测试和临时真实 collection smoke；
- README、架构、知识库设计、CHANGELOG、env example 和活动执行表同步。

### Excluded

- 上传、解析、Chunking、Embedding 与 upsert 的 ingestion 串联；
- `DocumentChunk.vector_id`、Document `embedding_status` 或 error 持久化；
- Document 查询/删除 API 与文件/Qdrant/SQLite 事务编排；
- Retriever、RAG Prompt、RAG API、Agent Tool 或前端；
- payload index、named vectors、sparse vectors、Hybrid Search、Rerank、Evaluation、
  Memory、OCR、multimodal 或 Plan 4+ runtime。

## 9. 验证策略

按 TDD 先让抽象/payload 测试因模块缺失而 RED，再完成最小 GREEN；随后让 Qdrant
adapter/config 测试因实现缺失而 RED，再实现并重跑 focused/adjacent tests。单元测试
覆盖 collection 创建/复核/不匹配、upsert、search filter/result、delete filter、输入、
payload、SDK 异常和响应错误。

最终在 Docker 的固定 Qdrant 上创建随机前缀临时 collection，完成 create/check、upsert、
filtered search 和 delete 验收，然后只删除该临时 collection。另运行 backend 全量、
依赖检查、临时 SQLite Alembic 往返、frontend typecheck/test/build、Compose/health、文档
链接、secret、artifact、Plan boundary、`git diff --check`、staged paths、HEAD/origin/tags
和状态检查。
