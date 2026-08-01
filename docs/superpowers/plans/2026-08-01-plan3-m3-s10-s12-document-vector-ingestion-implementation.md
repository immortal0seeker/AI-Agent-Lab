# Plan 3 M3 S10～S12 Document Vector Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Repository policy forbids subagents for this batch. Use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成上传文档从 parse/chunk 到 embed/Qdrant upsert 的同步链路，持久化 Chunk point ID 与 Document ingestion 状态，并完成 M3 验收文档。

**Architecture:** `app.rag.ingestion_pipeline` 只编排 EmbeddingProvider 与 VectorStore 并返回可信 point IDs；`DocumentIngestionService` 负责 ORM 状态和 `vector_id`；请求 Session 在 commit/rollback 后执行异步补偿和 Qdrant client finalizer。SQLite 保持业务主事实源，Qdrant 只负责向量与 payload。

**Tech Stack:** Python 3.11、FastAPI、SQLAlchemy、Pydantic、httpx、qdrant-client 1.15.x、pytest、Qdrant 1.15.4、Docker Compose、React/TypeScript/Vitest/Vite。

## Global Constraints

- 只实现 `P3-M3-S10～S12`，不开始 M4、Retriever、RAG API、前端 RAG 或 Plan 4+。
- 不读取真实 `.env`、secret、API key 或 `backend/ai_agent_lab.db`；不调用真实 Embedding/LLM Provider。
- 测试只使用完整 Mock Provider、Mock VectorStore、系统临时 SQLite/文件和随机临时 Qdrant collection。
- 不删除或重建既有 Qdrant collection；smoke 只清理名称精确匹配本批随机前缀的 collection。
- 不创建/切换分支，不使用 worktree，不 stage、commit、push 或 tag。
- 不使用子代理或外部 review；Codex self-review 是唯一 gate。

---

### Task 1: Ingestion pipeline RED

**Files:**

- Create: `backend/tests/test_ingestion_pipeline.py`

**Interfaces:**

- Consumes: `EmbeddingProvider.embed_texts(list[str]) -> EmbeddingResult`、`VectorStore.ensure_collection()`、`VectorStore.upsert(list[VectorPoint])`
- Produces: `ingest_document_vectors(...)->tuple[UUID, ...]`

- [x] 写成功测试：两个真实 ORM Chunk 经完整 Mock Provider/Store 生成有序 point IDs，payload ownership/content/source 字段完整。
- [x] 写 fail-closed 测试：空 Chunk、ownership 不一致、embedding 数量/维度不匹配、upsert 返回 ID 不一致。
- [x] 写补偿测试：upsert 异常或返回不可信 ID 后，按 Knowledge Base + Document 删除 vectors。
- [x] 运行并确认因 `app.rag.ingestion_pipeline` 缺失而 RED：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_ingestion_pipeline.py -q
```

### Task 2: Ingestion pipeline GREEN

**Files:**

- Create: `backend/app/rag/ingestion_pipeline.py`

**Interfaces:**

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

- [x] 校验非空 Chunk 列表、Document ownership 和稳定顺序。
- [x] 先检查 collection，再批量 embed；验证 vector count 与 `vector_store.dimension`。
- [x] 使用 Chunk UUID 和既有 payload builder 构建 points，upsert 并精确验证返回 IDs。
- [x] 对 upsert 不确定结果执行 best-effort Document vectors 删除，不泄漏文本/向量/底层异常。
- [x] 保持 `app.rag.__init__` 为 config 可安全导入的轻量文本处理边界；调用方直接导入 pipeline 模块。
- [x] 运行 Task 1 focused tests 至 GREEN，再运行 embedding/vectorstore 邻接测试。

### Task 3: Session transaction callbacks and dependencies RED

**Files:**

- Create: `backend/tests/test_session_callbacks.py`
- Modify: `backend/tests/test_embedding_provider_factory.py`
- Modify: `backend/tests/test_document_api.py`

**Interfaces:**

- Produces: rollback callback 注册/丢弃/异步执行、事务 finalizer 注册/执行
- Produces: `get_embedding_provider()`、`get_vector_store()` 可被 FastAPI tests 覆盖

- [x] 写 callback 顺序、commit 丢弃、rollback 执行、callback 失败不覆盖原异常的测试。
- [x] 写配置 provider 精确选择和未知 provider 安全失败测试。
- [x] 写 API dependency 初始化错误映射为安全 503 且不读取上传 stream 的测试。
- [x] 运行并确认 callback/dependency 接口缺失而 RED。

### Task 4: Session transaction callbacks and dependencies GREEN

**Files:**

- Create: `backend/app/db/session_callbacks.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/providers/embedding/factory.py`
- Modify: `backend/app/api/errors.py`

- [x] 实现 Session `info` 内的 async rollback callbacks 与 transaction finalizers；失败仅安全记录。
- [x] `get_db_session()` 在 commit 后丢弃 rollback callbacks，在 rollback 后 await cleanup，并始终执行 finalizers。
- [x] 实现 configured provider 选择；生产 Qdrant store close 注册到同一请求 Session finalizer。
- [x] 增加 Embedding/Vector 配置初始化异常的稳定 HTTP 503 映射。
- [x] 运行 Task 3 focused tests 至 GREEN，并回归现有 API/session/provider 测试。

### Task 5: Service status/vector ID RED

**Files:**

- Modify: `backend/tests/test_document_ingestion_service.py`
- Modify: `backend/tests/test_document_service.py`
- Modify: `backend/tests/test_document_api.py`

- [x] 将调用期望调整为 async，注入完整确定性 Provider/VectorStore test doubles。
- [x] 写成功断言：`parsed/chunked/ready`、所有 `vector_id == chunk.id`、payload 与数据库一致。
- [x] 写 parse/chunk/provider/vector 失败断言：状态准确、安全 error、无 partial vector IDs。
- [x] 写 API commit failure 断言：Document/Chunk/文件回滚，已写 vectors 经 rollback callback 删除。
- [x] 运行并确认当前实现仍返回 `pending` 或缺少新依赖而 RED。

### Task 6: Service status/vector ID GREEN

**Files:**

- Modify: `backend/app/services/document_ingestion_service.py`
- Modify: `backend/app/services/document_service.py`

- [x] 把 `process_document()` 改为 async，在 Chunk flush 后调用独立 pipeline。
- [x] parse/chunk 失败同步将 `embedding_status=failed`；外部失败保存固定安全消息。
- [x] 成功 upsert 后先登记 rollback cleanup，再全量写入规范 `vector_id`、标记 ready 并 flush。
- [x] `DocumentService.upload_document()` await ingestion，保持请求 Session 为唯一 commit/rollback owner。
- [x] 运行 Task 5 focused tests至 GREEN，再运行 knowledge/RAG/API 邻接回归。

### Task 7: End-to-end and live Qdrant matching verification

- [x] 使用 API + 临时 SQLite/文件 + Mock Embedding + Mock VectorStore 验证上传响应、数据库、points/payload 全链路。
- [x] 只读确认 Compose config、Qdrant 镜像/端口/restart 和 `/healthz`。
- [x] 使用随机 `codex_p3_m3_s10_s12_*` collection、临时 SQLite/文件和确定性 Mock Embedding，运行真实 create/check/embed/upsert/search。
- [x] 验证数据库 Chunk point IDs 与 Qdrant IDs 一致、Document 为 ready、payload ownership 完整。
- [x] 在 `finally` 精确删除本批临时 collection 与临时文件/数据库，并确认未留下 artifact。

### Task 8: M3 formal documentation and review

**Files:**

- Create: `docs/22-document-ingestion-pipeline.md`
- Create: `docs/reviews/2026-08-01-plan3-m3-review.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs/21-embedding-provider.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this spec and plan

- [x] 记录同步数据流、状态机、事务 ownership/补偿、配置、错误、安全与运行限制。
- [x] 将 Batch 10 与 M3 验收项更新为已完成，但保持 M4/Plan 4 项 pending。
- [x] 完成 M3 S1～S12 Codex review，分类 must fix / fix later / limitation / not applicable。

### Task 9: Full verification and Codex self-review

- [x] Backend focused and full pytest；`pip check`。
- [x] 新建系统临时 SQLite 做 Alembic upgrade/current/check/downgrade/upgrade；删除临时目录。
- [x] Frontend typecheck、tests、production build。
- [x] Compose config/Qdrant health、Markdown links、secret/private-key、network/later-plan runtime、tracked artifact 检查。
- [x] `git diff --check`、diff allowlist、staged paths、branch/HEAD/origin/tags/status 检查。
- [x] Codex self-review 修复所有 must-fix 后重新验证；更新本文 checkbox 和设计状态。
- [x] 向用户报告 M3 是否完成、能否进入 M4，并建议 commit message；不执行提交。
