# Plan 3 M3 S7～S9 Qdrant Vector Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Repository policy forbids subagents for this batch. Use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现并验证 P3-M3-S7～S9 的 VectorStore 抽象、Qdrant adapter 和稳定 Chunk payload 规范。

**Architecture:** `app.rag.vectorstores` 拥有面向 Naive RAG 的异步窄接口；`payload.py` 把 Document/Chunk 转为完整来源 payload；`qdrant_store.py` 是唯一依赖 Qdrant SDK 的 adapter，并通过客户端注入保持测试可控。SQLite 继续保存业务/审计事实，Qdrant 只保存向量和检索所需 payload。

**Tech Stack:** Python 3.11、Pydantic、qdrant-client 1.15.x、pytest、Qdrant 1.15.4、Docker Compose、React/TypeScript/Vitest/Vite。

## Global constraints

- 只实现 `P3-M3-S7～S9`，不开始 S10+、M4+ 或 Plan 4+。
- 不读取真实 `.env`、secret、API key 或 `backend/ai_agent_lab.db`；不调用真实 Embedding/LLM Provider。
- 单元测试只替换 Qdrant 网络边界；真实 smoke 只使用本机 Compose 和随机临时 collection。
- 不删除或重建既有 collection；smoke 结束只清理本次随机临时 collection。
- 不创建/切换分支，不使用 worktree，不 stage、commit、push 或 tag。
- 不使用子代理或外部 review；Codex self-review 是唯一 gate。

---

### Task 1: VectorStore contract and payload RED

**Files:**

- Create: `backend/tests/test_vector_store.py`
- Create: `backend/tests/test_qdrant_payload.py`

- [x] 写 mock VectorStore 测试：异步 collection/upsert/search/delete/close 契约和规范返回值。
- [x] 写 point/query/result 验证测试：UUID、有限向量、维度前置条件、limit 和 score。
- [x] 写 payload builder 测试：所有必需字段、M4 content/source 字段、UUID JSON 序列化、ownership、JSON-safe metadata 和输入复制。
- [x] 运行并确认因 `app.rag.vectorstores` 缺失而 RED：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_vector_store.py tests/test_qdrant_payload.py -q
```

### Task 2: VectorStore contract and payload GREEN

**Files:**

- Create: `backend/app/rag/vectorstores/base.py`
- Create: `backend/app/rag/vectorstores/payload.py`
- Create: `backend/app/rag/vectorstores/__init__.py`

- [x] 实现不可变 VectorPoint、VectorSearchQuery、VectorSearchResult 和 collection 状态。
- [x] 实现 VectorStore 抽象与配置/输入/operation/response/dimension 错误层级。
- [x] 实现 Chunk payload model 和 `build_qdrant_payload()` ownership/JSON-safe 校验。
- [x] 运行 Task 1 focused tests 至 GREEN。

### Task 3: Qdrant adapter and Settings RED

**Files:**

- Create: `backend/tests/test_qdrant_vector_store.py`
- Modify: `backend/tests/test_config.py`

- [x] 写 collection 缺失创建、已有检查、dimension/distance/named-vector fail-closed 测试。
- [x] 写 upsert PointStruct/wait/维度、query_points KB filter/payload/result、Document delete 双 ownership filter 测试。
- [x] 写 SDK 异常和畸形响应安全规范化测试。
- [x] 写 Settings 默认、覆盖、URL/collection/timeout 边界和 factory dimension 缺失测试。
- [x] 运行并确认因 adapter/config 缺失而 RED。

### Task 4: Qdrant adapter and Settings GREEN

**Files:**

- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/rag/vectorstores/qdrant_store.py`
- Modify: `backend/app/rag/vectorstores/__init__.py`
- Modify: `backend/.env.example`

- [x] 增加与 server 1.15.4 同 minor 的 `qdrant-client` 依赖并刷新 editable dev 环境。
- [x] 增加惰性 `QDRANT_COLLECTION_NAME` 和 `QDRANT_TIMEOUT_SECONDS` 配置及边界。
- [x] 实现 factory、客户端 ownership/close、COSINE collection create/check。
- [x] 实现 upsert、Knowledge Base filtered query、Document filtered delete 和安全错误转换。
- [x] 运行 Task 3 focused tests至 GREEN，再运行 config/embedding/RAG/knowledge adjacent tests。

### Task 5: Live Qdrant matching verification

- [x] 只读确认 Compose config、容器镜像/端口/重启和 `/healthz`。
- [x] 使用随机 `codex_p3_m3_s7_s9_*` collection 和合成 3 维向量执行 create/check。
- [x] upsert 两个不同 Knowledge Base payload，验证 filtered search 只返回目标 KB。
- [x] 按目标 Document 删除并确认目标 point 消失、其他 KB point 保留。
- [x] 精确核对临时 collection 名后删除它，确认未留下本批 collection/artifact。

### Task 6: Formal documentation

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs/21-embedding-provider.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this spec and plan

- [x] 说明 collection/config、payload、filter、错误、安全、生命周期和当前限制。
- [x] 把 Batch 9 更新为已完成并写入可复核验收记录。
- [x] 明确 S10～S12 ingestion/vector_id/status 与 M4 Retriever 仍 deferred。

### Task 7: Full verification and Codex self-review

- [x] Backend focused and full pytest。
- [x] `pip check`。
- [x] 新建临时 SQLite，执行 Alembic upgrade/check/downgrade/upgrade；删除临时目录，不接触用户 DB。
- [x] Frontend typecheck、tests、build。
- [x] 检查 Markdown links、secrets、private key headers、network/later-plan runtime、tracked artifacts。
- [x] 检查 `git diff --check`、diff allowlist、staged paths、branch/HEAD/origin/tags/status。
- [x] Codex self-review 分类 must fix / fix later / limitation / not applicable；修复后重新验证。
- [x] 将本文 checkbox 和设计状态更新为最终证据，向用户建议 commit message，但不提交。
