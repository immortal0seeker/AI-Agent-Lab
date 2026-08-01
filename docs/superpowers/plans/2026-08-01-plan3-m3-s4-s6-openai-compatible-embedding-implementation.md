# Plan 3 M3 S4～S6 OpenAI-compatible Embedding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Repository policy forbids subagents for this batch. Use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现并验证 P3-M3-S4～S6 的 OpenAI-compatible Embedding Provider、配置/错误初始化和正式文档。

**Architecture:** 保留现有厂商无关抽象；具体 HTTP 协议只存在于 adapter，Settings 仅解析配置，factory 延迟校验必需项。返回结果继续使用不可变 `EmbeddingResult`，响应维度必须与配置一致。

**Tech Stack:** Python 3.11、Pydantic Settings、httpx、pytest、Docker Compose、React/TypeScript/Vitest/Vite。

## Global constraints

- 只实现 `P3-M3-S4～S6`，不开始 S7+、M4+ 或 Plan 4+。
- 不读取真实 `.env`、secret、API key 或 `backend/ai_agent_lab.db`；不调用真实 Provider。
- 测试只使用合成凭据、示例 URL 和 `httpx.MockTransport`。
- 不创建/切换分支，不使用 worktree，不 stage、commit、push 或 tag。
- 不使用子代理或外部 review；Codex self-review 是唯一 gate。

---

### Task 1: Adapter and error boundary RED

**Files:**

- Create: `backend/tests/test_openai_compatible_embedding_provider.py`
- Modify: `backend/tests/test_embedding_provider.py`

- [x] 写 mock HTTP 测试：批量和 query 请求、Bearer header、model、dimensions、float encoding。
- [x] 写响应解析测试：按 index 排序、实际 model、usage、vectors。
- [x] 写失败测试：无效输入、HTTP 分类、timeout/request error、无效 JSON/结构、条目/index/维度错误、消息不泄漏。
- [x] 运行并确认因适配器/错误类型缺失而 RED：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_embedding_provider.py tests/test_embedding_provider.py -q
```

### Task 2: Adapter and error boundary GREEN

**Files:**

- Modify: `backend/app/providers/embedding/base.py`
- Create: `backend/app/providers/embedding/openai_compatible_embedding.py`
- Modify: `backend/app/providers/embedding/__init__.py`

- [x] 增加 Embedding 专用配置、输入、请求、响应和维度错误类型。
- [x] 实现 client 注入/所有权、payload、批量/query 请求、状态码和网络错误映射。
- [x] 严格解析 data/index/model/usage，构造 `EmbeddingResult` 并校验配置维度。
- [x] 运行 Task 1 focused tests 至 GREEN。

### Task 3: Settings and factory RED

**Files:**

- Create: `backend/tests/test_embedding_provider_factory.py`
- Modify: `backend/tests/test_config.py`

- [x] 写 Settings 默认/覆盖/边界/SecretStr 遮蔽测试。
- [x] 写 factory 缺 key、base URL、model、dimension 的可读错误测试。
- [x] 写 factory 使用配置初始化 Provider 的 mock HTTP 测试。
- [x] 运行并确认因配置字段和 factory 缺失而 RED。

### Task 4: Settings and factory GREEN

**Files:**

- Modify: `backend/app/core/config.py`
- Create: `backend/app/providers/embedding/factory.py`
- Modify: `backend/app/providers/embedding/__init__.py`
- Modify: `backend/.env.example`

- [x] 增加 `EMBEDDING_PROVIDER` 与 `OPENAI_COMPATIBLE_EMBEDDING_*` 配置。
- [x] 为 dimension 和 timeout 增加正数、有限值与上界。
- [x] 实现延迟初始化 factory，缺配置时不泄漏 key。
- [x] 运行 Task 3 focused tests 至 GREEN，再运行所有 Embedding/LLM/config 邻接测试。

### Task 5: Formal documentation

**Files:**

- Create: `docs/21-embedding-provider.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this plan

- [x] 说明配置、模型/维度一致性、批量语义、错误类别、成本/隐私注意事项和限制。
- [x] 把执行表 Batch 8 更新为已完成并写入可复核验收记录。
- [x] 明确 S7+ 的 Qdrant 和 ingestion 仍 deferred。

### Task 6: Verification and Codex self-review

- [x] Backend focused and full pytest。
- [x] `pip check`。
- [x] 新建临时 SQLite，执行 Alembic upgrade/check/downgrade/upgrade；删除临时目录，不接触用户 DB。
- [x] Frontend typecheck、tests、build。
- [x] `docker compose config --quiet`、Qdrant service/health 只读检查。
- [x] 检查 Markdown links、secrets、private key headers、network/later-plan runtime、tracked artifacts。
- [x] 检查 `git diff --check`、diff allowlist、staged paths、branch/HEAD/origin/tags/status。
- [x] Codex self-review 分类 must fix / fix later / limitation / not applicable；修复后重新验证。
- [x] 将本文 checkbox 和设计状态更新为最终证据，向用户建议 commit message，但不提交。
