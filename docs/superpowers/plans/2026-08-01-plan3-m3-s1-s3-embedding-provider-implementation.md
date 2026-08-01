# Plan 3 M3 S1～S3 Embedding Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Repository policy forbids subagents for this batch. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可替换、可验证的 Embedding Provider 抽象、批量结果契约和按配置名称选择实例的 Registry。

**Architecture:** `providers/embedding/base.py` 只定义 Provider 与不可变结果；`registry.py` 只管理运行时 Provider 实例。具体 HTTP adapter、Settings/secret、Qdrant 和 ingestion 均留给 S4+。

**Tech Stack:** Python 3.11、ABC、Pydantic 2、pytest。

## Global Constraints

- 只实现 `P3-M3-S1～S3`；不得创建 OpenAI-compatible Embedding adapter、Embedding Settings/factory、Vector Store、Qdrant client、向量写入或 Retriever。
- 不读取真实 `.env`、secret、API key、用户 SQLite 或工作区外敏感路径；不调用真实 Provider 或网络 Tool。
- 测试只使用内存 Mock Provider；运行数据库验证时只使用新建系统临时 SQLite。
- SQLite 继续作为默认且长期支持的业务/审计数据库；Qdrant 只承担 Plan 3 向量存储。
- 不创建或切换分支，不使用 worktree，不 stage、commit、push 或 tag。
- 不使用子代理或外部 review；Codex self-review 是唯一 gate。

## File Map

### Create

- `backend/app/providers/embedding/base.py` — Provider、usage 和 batch result 契约。
- `backend/app/providers/embedding/registry.py` — 运行时 Provider 注册与配置名选择。
- `backend/app/providers/embedding/__init__.py` — 稳定公开导出。
- `backend/tests/test_embedding_provider.py` — mock Provider 和结果边界。
- `backend/tests/test_embedding_provider_registry.py` — Registry 行为与错误路径。
- `docs/superpowers/specs/2026-08-01-plan3-m3-s1-s3-embedding-provider-design.md` — 验收矩阵和设计。
- `docs/superpowers/plans/2026-08-01-plan3-m3-s1-s3-embedding-provider-implementation.md` — 本计划与执行证据。

### Modify After GREEN

- `README.md`
- `README_CN.md`
- `CHANGELOG.md`
- `docs/01-architecture.md`
- `docs/20-knowledge-base-design.md`
- `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`

---

### Task 1: Define The Mockable Provider And Batch Result

**Files:**

- Create: `backend/tests/test_embedding_provider.py`
- Create: `backend/app/providers/embedding/base.py`
- Create: `backend/app/providers/embedding/__init__.py`

**Interfaces:**

- Produces: `EmbeddingUsage(input_tokens: int, total_tokens: int)`.
- Produces: `EmbeddingResult(model: str, vectors: tuple[tuple[float, ...], ...], usage: EmbeddingUsage)` and `.dimension`.
- Produces: `EmbeddingProvider(name: str)` with async `embed_texts()` and `embed_query()`.
- Produces: `EmbeddingProviderError` as the shared Provider-boundary base exception.

- [x] **Step 1: Write failing result-contract and mock-provider tests**

Create tests that define this wished-for API:

```python
class MockEmbeddingProvider(EmbeddingProvider):
    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            model="mock-embedding",
            vectors=tuple((float(index), 1.0) for index, _ in enumerate(texts)),
            usage=EmbeddingUsage(
                input_tokens=len(texts),
                total_tokens=len(texts),
            ),
        )

    async def embed_query(self, query: str) -> EmbeddingResult:
        return EmbeddingResult(
            model="mock-embedding",
            vectors=((0.5, 1.0),),
            usage=EmbeddingUsage(input_tokens=1, total_tokens=1),
        )
```

Assertions must cover:

- batch input order maps to ordered vectors and returns usage;
- query returns one vector and usage;
- provider name is trimmed, immutable and bounded to 100 characters;
- result model is trimmed; inputs are defensively converted to tuples;
- empty result batch, empty vector, mixed dimensions, NaN/Infinity, negative usage and `total_tokens < input_tokens` fail validation;
- result model is frozen and `.dimension` is stable.

- [x] **Step 2: Run RED and confirm the feature is absent**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_embedding_provider.py -q
```

Expected: collection failure because `app.providers.embedding` does not exist.

- [x] **Step 3: Implement the minimal base contract**

Create `base.py` with:

```python
class EmbeddingUsage(BaseModel): ...
class EmbeddingResult(BaseModel): ...
class EmbeddingProviderError(RuntimeError): ...
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> EmbeddingResult: ...
    @abstractmethod
    async def embed_query(self, query: str) -> EmbeddingResult: ...
```

Use `ConfigDict(extra="forbid", frozen=True)`, Pydantic validation for shape/
finite-number/usage invariants, and a read-only normalized Provider name. Export
all public contracts from `embedding/__init__.py`.

- [x] **Step 4: Run GREEN**

Run the focused test command again. Expected: all tests pass with no new warning.

- [x] **Step 5: Read-only checkpoint**

Run `git diff --check` and inspect `git status --short`; do not stage or commit.

---

### Task 2: Register And Select Providers By Configuration Name

**Files:**

- Create: `backend/tests/test_embedding_provider_registry.py`
- Create: `backend/app/providers/embedding/registry.py`
- Modify: `backend/app/providers/embedding/__init__.py`

**Interfaces:**

- Consumes: `EmbeddingProvider.name` and concrete Provider instances.
- Produces: `EmbeddingProviderRegistry.register_provider(provider) -> None`.
- Produces: `EmbeddingProviderRegistry.get_provider(name) -> EmbeddingProvider`.
- Produces: `EmbeddingProviderRegistry.list_providers() -> list[EmbeddingProvider]`.
- Produces: `EmbeddingProviderRegistryError`, `DuplicateEmbeddingProviderError`, `EmbeddingProviderNotFoundError`.

- [x] **Step 1: Write failing Registry tests**

Tests must demonstrate:

```python
registry = EmbeddingProviderRegistry()
registry.register_provider(first)
registry.register_provider(second)
assert registry.get_provider(configured_name) is first
assert registry.list_providers() == [first, second]
```

Also assert duplicate registration leaves the original mapping unchanged, missing and
non-string names fail with stable errors, non-Provider instances are rejected, exact
lookup does not trim or fold case, and clearing the returned list cannot mutate Registry
state.

- [x] **Step 2: Run RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_embedding_provider_registry.py -q
```

Expected: collection failure because Registry exports do not exist.

- [x] **Step 3: Implement the minimal Registry**

Use an insertion-ordered `dict[str, EmbeddingProvider]`. Validate the instance before
reading its name; reject duplicates before mutation; return `list(dict.values())` for a
defensive ordered snapshot. Do not import Settings or any concrete adapter.

- [x] **Step 4: Run GREEN and adjacent Provider regression**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_embedding_provider.py tests/test_embedding_provider_registry.py tests/test_llm_provider_base.py tests/test_llm_provider_factory.py -q
```

Expected: all tests pass; only the repository's known TestClient warning is acceptable
when API tests are included later.

- [x] **Step 5: Read-only checkpoint**

Run `git diff --check` and inspect `git status --short`; do not stage or commit.

---

### Task 3: Synchronize Current-Scope Documentation

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this implementation plan

- [x] **Step 1: Update current-stage facts**

Record that completed scope is now through `P3-M3-S3`. Describe only the abstract
Provider, validated batch result and runtime Registry. Replace statements claiming all
Embedding runtime is deferred with precise statements that the concrete adapter,
Settings/error initialization, Qdrant Vector Store and ingestion integration remain
deferred.

- [x] **Step 2: Mark only Batch 7 / S1～S3 complete**

Update the execution table row and add a dated acceptance record with RED/GREEN and
final verification evidence. Do not change Batch 8+ status.

- [x] **Step 3: Run documentation checks**

Validate UTF-8 readability and every local Markdown link/image target. Search changed
content for stale `P3-M2-S9` current-scope claims and for accidental claims that S4+
exists.

---

### Task 4: Full Verification And Codex Self-Review

- [x] **Step 1: Focused backend verification**

Run new tests plus adjacent Provider, Settings, Knowledge Base, Document processing,
model, migration, service and API tests.

- [x] **Step 2: Full backend and dependency verification**

Run complete backend pytest and `pip check` through the workspace virtual environment.

- [x] **Step 3: Temporary SQLite migration verification**

Create a new system temporary directory, point Alembic at a new SQLite file through a
synthetic environment override, then run upgrade/current/check/downgrade/re-upgrade.
Verify the temporary directory is removed. Never access `backend/ai_agent_lab.db`.

- [x] **Step 4: Frontend regression**

Run typecheck, Vitest and production build even though frontend files are unchanged.

- [x] **Step 5: Docker/Qdrant verification**

Run Compose config validation, `docker compose ps`, and the loopback `/healthz` check.
Do not create collections or send vectors in this batch.

- [x] **Step 6: Static and Git gates**

Check Markdown links, high-confidence secrets/private-key markers, tracked artifacts,
later-Plan executable runtime, `git diff --check`, staged paths, branch/HEAD/origin/tag
targets, and exact changed-path scope.

- [x] **Step 7: Codex self-review and fix loop**

Classify every finding as must fix, later Step, accepted limitation or not applicable.
Fix must-fix items with a reproducing RED test, rerun matching verification, and finish
only when no blocking issue remains.

- [x] **Step 8: Final handoff**

Report S1～S3 status, fresh verification evidence, residual limitations, readiness for
`P3-M3-S4～S6`, and suggested commit message. Do not commit.

## Plan Self-Review

- Every S1～S3 acceptance item maps to a TDD task and exact file.
- Interface names and result fields are consistent across tasks.
- No placeholder, concrete Provider, Settings factory, Vector Store, ingestion or later
  Plan runtime is included.
- Execution remains inline because repository policy forbids subagents for this batch.

## Execution Evidence

- Baseline: `main == origin/main == 70ef2f90307a11beb8755439085ce29b1f2bc7aa`,
  clean working tree and staged paths 0 before implementation; existing tags were not
  moved.
- Base/result TDD: missing-package RED; initial GREEN `17 passed`.
- Registry TDD: missing-export RED; Provider/LLM adjacent GREEN `58 passed`.
- Codex review TDD: Pydantic coercion reproduced as `4 failed, 17 passed`; strict
  numeric/integer boundary GREEN `62 passed`.
- Final backend: focused `303 passed, 1 warning`; full `765 passed, 1 warning`;
  `pip check` reported `No broken requirements found.`. The warning is the existing
  Starlette TestClient/httpx deprecation warning.
- Temporary SQLite: upgrade/current/check/downgrade/re-upgrade passed at
  `20260801_0006`; the system temporary directory was removed. The user database was
  not read or modified.
- Frontend: typecheck passed; `18 files / 90 tests`; build passed with `1813` modules.
- Docker: Compose config passed; `qdrant/qdrant:v1.15.4` was up on
  `127.0.0.1:6333`; `/healthz` returned `healthz check passed`.
- Documentation/security: `97` Markdown files, `69` local links/images, zero missing;
  high-confidence token 0, unexpected private-key header 0, `web_fetch` runtime 0,
  later-Plan runtime 0, tracked artifacts 0.
- Codex self-review: the only must-fix was strict rejection of coerced bool/string
  vector values and bool/float token counts; it was fixed and reverified. S4+ work
  remains deferred. No external review was used.
- Git workflow: no branch/worktree creation, stage, commit, push, or tag operation was
  performed; the batch remains ready for the user's manual commit.
