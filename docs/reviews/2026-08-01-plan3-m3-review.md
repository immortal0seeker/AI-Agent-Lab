# Plan 3 M3 Embedding, Vector Store, And Ingestion Review

## Scope And Baseline

本 review 覆盖 Plan 3 M3 S1～S12，重点复核最终批次 S10～S12 如何把已提交的
Embedding Provider 与 Qdrant VectorStore 串成文档向量入库。S10～S12 开始时是干净的
`main`，`HEAD == origin/main == e78320199fc7c36dd8ea8c08140aaa47c6ae31b4`，
staged paths 为 0；`v0.2.0` / `v0.2.1` peeled targets 保持
`0e3f3a66e1322c565f2056696f7e482cedbb5f6c` /
`872310b4dc1b78e2a2487303699d68ec8b22f88b`。

本批未创建或切换分支、未使用 worktree、未 stage/commit/push/tag，未开始 M4、
Retriever、RAG Prompt/API、Agent Tool、前端 RAG 或 Plan 4+ runtime，也未读取或修改
`backend/ai_agent_lab.db`。

## Acceptance Matrix

| Step | 验收要求 | 实现与证据 | 状态 |
|---|---|---|---|
| S1～S3 | 可替换 Embedding 抽象、批量结果、Registry | 异步 Provider、严格不可变向量/usage、精确名称选择及 Mock tests | implemented |
| S4～S6 | OpenAI-compatible adapter、配置/错误、文档 | 批量/查询协议映射、延迟配置、维度双检、安全错误及 Provider 文档 | implemented |
| S7～S9 | VectorStore、Qdrant、payload | collection/upsert/search/delete、ownership filter、source payload 及真实临时 collection smoke | implemented |
| S10 | 上传后 parse/chunk/embed/upsert | 独立 `ingestion_pipeline.py` 由异步 `DocumentIngestionService` 调用，API 端到端覆盖 | implemented |
| S11 | Chunk point ID 与 ingest 状态 | point UUID 固定等于 Chunk UUID；成功全量写 `vector_id`/`ready`，失败全无 ID/`failed` | implemented |
| S12 | 入库文档、端到端测试、M3 review | 正式 pipeline 文档、Mock API 全链路、真实本地 Qdrant 与本 review | implemented |

## Architecture Review

- `EmbeddingProvider` 不依赖数据库或 Qdrant；`VectorStore` 不依赖 Provider 或
  SQLAlchemy；独立 ingestion pipeline 只组合这两个边界并返回可信 point IDs。
- Route 只做依赖/schema/service 调用。`DocumentService` 协调受控文件与 Document，
  `DocumentIngestionService` 负责状态和 Chunk 持久化，请求 Session 是唯一 commit owner。
- SQLite 继续拥有 Document/Chunk/status/audit 事实；Qdrant 只拥有向量与可追溯 payload。
  point ID 与 Chunk UUID 统一，避免双重身份映射。
- Qdrant 与 SQLite 无分布式事务；upsert 成功后登记请求级 rollback callback，commit
  失败时按 Knowledge Base + Document 双 ownership filter best-effort 删除 points。
  Session finalizer 在成功或失败后关闭 Qdrant client。
- 上传流程仍受文件、PDF 页数、提取字符、Markdown 结构、Chunk 数、Chunk 大小/重叠
  限制约束；完整 Chunk 列表只发起一个受界 Provider batch，不做静默截断。

## TDD Evidence

M3 各批均从行为级 RED 开始：

- S1～S3：base/result 因 package 缺失 RED，GREEN `17 passed`；Registry 因导出
  缺失 RED；严格数值自审 RED `4 failed, 17 passed`，最终邻接 `62 passed`。
- S4～S6：adapter 导出缺失 RED，GREEN `48 passed`；Settings/factory 缺失 RED，
  GREEN `52 passed`；响应 cause 安全自审 RED `6 failed, 21 passed`，最终 adapter
  `27 passed`。
- S7～S9：contract/payload package 缺失 RED，GREEN `30 passed`；adapter/config
  缺失 RED；ID/KB traceability RED `2 failed, 42 passed`、写入状态 RED
  `4 failed, 21 passed`，最终 focused `113 passed`。
- S10～S12：pipeline 模块缺失 RED，GREEN `8 passed`；callback/factory/error mapping
  接口缺失 RED，GREEN `22 passed, 1 warning`；service/API 预期因旧构造器和 pending
  状态 RED `38 failed, 11 passed`，实现后 GREEN `49 passed, 1 warning`。

最终 S10～S12 邻接 focused 为 `312 passed, 1 warning`。warning 是既知 Starlette
`TestClient` / httpx 弃用提示。

## End-To-End Evidence

API 测试使用系统临时 SQLite、临时 workspace、确定性 Mock Embedding 和完整 Mock
VectorStore，验证：

- HTTP 201 ready 响应、SQLite Document/Chunk、point IDs 和 payload 完全一致；
- parse、chunk、Provider、VectorStore 失败状态准确且没有 partial vector IDs；
- Provider/VectorStore 初始化失败在读文件前返回安全 503，不留下文件或数据库行；
- Qdrant upsert 后模拟 SQLite commit failure，会回滚 Document/Chunks/文件并执行
  ownership-scoped vector cleanup。

真实本地 Qdrant 1.15.4 运行于 `127.0.0.1:6333`，restart 为 0，`/healthz`
返回 HTTP 200 `healthz check passed`。随机 `codex_p3_m3_s10_s12_*` collection 使用
确定性 Mock Embedding、临时 SQLite/文件完成一份 Document 的 parse/chunk/embed/upsert：
Document 为 ready、数据库/point IDs 一致、search 返回 1 hit；按 Document 删除后为
0 hit，最终删除 collection 并确认同前缀临时 collection 数为 0。

## Full Verification Evidence

- 完整 backend：`900 passed, 1 warning`。
- dependency integrity：`No broken requirements found.`。
- 新建系统临时 SQLite 完成 Alembic upgrade/current `--check-heads`/check/downgrade
  `20260726_0005`/re-upgrade；head 为 `20260801_0006`，临时目录已删除。
- frontend：typecheck、`18 files / 90 tests`、production build `1813 modules` 通过。
- Compose config、Qdrant runtime/health 与真实临时 collection 闭环通过。
- 文档：`106` 个 Markdown、`84` 个本地链接/图片、`0 missing`。
- 安全/边界：高置信 secret `0`、private-key header `0`、executable later-Plan
  runtime `0`、network-Tool runtime `0`、tracked artifact `0`。
- final Git gate：`git diff --check` 通过，staged paths `0`，`26` 个预期路径
  （17 modified、9 untracked）；branch/HEAD/origin 与两个既有 peeled tag targets
  均未改变。

## Security And Plan-Boundary Review

所有 Provider/API 凭据均为合成值，Embedding 只使用 Mock，未调用真实付费 Provider 或
网络 Tool。固定持久化错误不包含文件名、路径、正文、hash、向量、endpoint、credential、
remote body 或底层 cause。Qdrant 仅绑定 loopback，搜索/删除始终带 Knowledge Base
ownership，Document 清理额外带 Document ownership。

实现路径未新增 Retriever、RAG answer/query runtime、Advanced RAG、Hybrid Search、
Rerank、Evaluation、Trace、Memory、OCR、multimodal、MCP 或 Human Approval。正式文档只
把这些能力记录为 later-step/limitation，不宣称已实现。

## Codex Self-Review

### Must fix

已修复并复验：

- pipeline 首次导出造成 `config -> rag.__init__ -> ingestion_pipeline -> provider.factory
  -> config` 循环导入；保持 `app.rag.__init__` 为轻量文本处理边界，调用方直接导入
  pipeline 模块。
- rollback closure 若捕获完整 ORM Document，事务失败后访问属性可能触发失效对象加载；
  改为在 upsert 后捕获标量 Knowledge Base/Document UUID。
- 同步 README、架构、Knowledge Base/Embedding 文档与执行表中的陈旧 `pending` 状态，
  明确成功 `ready`、失败状态、vector ID 与补偿边界。

无剩余 must-fix。

### Fix later

- M4 实现 Retriever、RetrievalResult、RAG Prompt、RAG Query/Chat、rag_queries 写入和
  `search_knowledge_base` Tool。
- 后续 Plan 3 实现 Document 查询/删除/重试、前端上传/状态/RAG Chat 与来源展示。

### Accepted limitation

- 没有对真实 Embedding 服务的连通性、模型质量、价格、限流或可用性验收。
- 每份 Document 使用一个 Provider batch；无自动拆批、retry/backoff、fallback、cache
  或持久化 embedding usage/cost。
- rollback 补偿是 best-effort；进程/主机硬崩溃或清理期间 Qdrant 不可用仍可能留下
  orphan points，当前没有自动 reconciliation job。
- 上传仍同步占用请求；没有 worker/outbox/re-ingestion 状态机。
- 保留既知 Starlette `TestClient` / httpx 弃用 warning。

### Not applicable

- 新 ORM 字段或 migration、PostgreSQL 迁移、前端页面/截图、真实/付费 Provider、真实
  网络 Tool、外部 Claude/Fable review、release tag。

## Readiness Conclusion

Plan 3 M3 S1～S12 已实现，S10～S12 matching verification 和 M3 全量 Codex review 均无
剩余 must-fix。用户手动提交本批后，可以进入 `P3-M4-S1～S3`；该结论不表示 M4、
Naive RAG API、前端或 Plan 3 release 已完成。
