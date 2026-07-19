# Plan 2 M4 Agent API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository policy forbids subagents and automatic commits for this batch, so execution stays inline and the user creates the final commit manually.

**Goal:** Complete `P2-M4-S1～S3` with validated Agent API schemas, a synchronous AgentRun creation endpoint, and read-only AgentRun/ToolCall query endpoints over the existing M3 Simple Agent Loop.

**Architecture:** Add API-facing Pydantic schemas and a small `AgentService` façade. The existing `SimpleAgentService` remains the only Agent Loop implementation; FastAPI dependencies compose it only for POST, while GET queries depend only on the database so Provider configuration is never required for history reads.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, Alembic, pytest, FastAPI TestClient.

## Global Constraints

- Only implement `P2-M4-S1～S3`; frontend work remains `P2-M4-S4～S6`.
- Use only plural `/api/v1/agents/runs` routes; do not add singular aliases.
- The external task field is `input`; do not accept a `content` alias.
- A created structured failed AgentRun commits and returns HTTP 201 with `status="failed"` and safe `error`.
- Query endpoints must work without constructing or configuring a Provider.
- Register only the existing read-only `read_file` and `list_dir` Tools and preserve their workspace security boundary.
- Do not change ORM states, database models, Alembic revisions, Provider contracts, or the M3 loop.
- Do not call real Providers, network Tools, paid APIs, real `.env`, credentials, or user databases.
- Do not implement frontend, streaming Tool Calls, retry/cancel/resume, RAG, Embedding, Memory, MCP, Shell, write, or delete Tools.
- SQLite remains the default and long-term supported primary database.
- Do not stage, commit, push, tag, create/switch branches, or use Claude Code/Fable 5/subagents.

---

## File Structure

**Create:**

- `backend/app/schemas/agent.py`: public Agent request, AgentRun read, ToolCall read, and execution response schemas.
- `backend/app/services/agent_service.py`: API-facing run delegation and AgentRun/ToolCall query behavior.
- `backend/app/api/v1/agents.py`: thin FastAPI routes and ORM-to-schema conversion.
- `backend/tests/test_agent_service.py`: service query/order/not-found tests.
- `backend/tests/test_agent_api.py`: schema, OpenAPI, transaction, endpoint, error, and security-boundary tests.
- `docs/12-agent-api.md`: formal implemented API contract and limitations.

**Modify:**

- `backend/app/agents/errors.py`, `backend/app/agents/__init__.py`: AgentRun not-found domain error export.
- `backend/app/api/dependencies.py`: Tool Registry, Simple Agent executor, and AgentService dependencies.
- `backend/app/api/errors.py`: safe Agent domain error mapping.
- `backend/app/main.py`: register the Agent router.
- `backend/app/schemas/__init__.py`: public schema exports. Import `AgentService`
  directly from its module to avoid coupling package initialization to Agent code.
- `README.md`, `README_CN.md`, `CHANGELOG.md`, `docs/00-project-overview.md`, `docs/01-architecture.md`, `docs/11-simple-agent-loop.md`: actual implemented surface and current limitations.
- `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`: Batch 10/S1～S3 evidence and next batch.
- `docs/superpowers/plans/2026-07-19-plan2-m4-agent-api-implementation.md`: mark only verified checklist items complete.

---

### Task 1: Agent API Schemas

**Files:**

- Create: `backend/app/schemas/agent.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/tests/test_agent_api.py`

**Interfaces:**

- Consumes: `app.schemas.tool.ToolCallStatus`, `app.tools.ToolResult`.
- Produces: `AgentRunCreate`, `AgentRunRead`, `AgentRunExecutionRead`, `AgentRunStatus`, `ToolCallRead`.

- [x] **Step 1: Write RED schema tests**

Add tests proving:

```python
request = AgentRunCreate(
    provider=" mock ",
    model=" tools-model ",
    input="Read the workspace",
)
assert request.provider == "mock"
assert request.model == "tools-model"
assert request.temperature == 0.7
assert request.max_tokens is None
assert request.max_steps == 3
```

Parametrize `max_steps` with `True`, `1.5`, `0`, and `11`; reject unknown fields and blank `input`; accept exactly `1` and `10`. Validate a terminal ToolCall response with a complete `ToolResult`, and prove public schema fields are named `arguments`, `result`, and `error`.

- [x] **Step 2: Run RED**

From `backend/` run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -k "schema" -q
```

Expected: collection fails because `app.schemas.agent` does not exist.

- [x] **Step 3: Implement `schemas/agent.py`**

Define exact types:

```python
AgentRunStatus = Literal[
    "created", "running", "waiting_tool", "completed", "failed", "cancelled"
]

class AgentRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID | None = None
    provider: NonEmptyIdentifier = Field(max_length=100)
    model: NonEmptyIdentifier = Field(max_length=255)
    input: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    max_steps: int = Field(default=3, ge=1, le=10, strict=True)

    @field_validator("input")
    @classmethod
    def reject_blank_input(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input must not be blank")
        return value
```

Define `AgentRunRead` with the exact fields in design section 4.1; allow nullable `user_message_id`, terminal fields, and timestamps consistent with ORM. Define `ToolCallRead` with semantic public field names and `result: ToolResult | None`. Define:

```python
class AgentRunExecutionRead(AgentRunRead):
    tool_calls: list[ToolCallRead] = Field(default_factory=list)
```

Export these types from `app.schemas`.

- [x] **Step 4: Run GREEN**

Run the Task 1 command again. Expected: all schema-selected tests pass.

---

### Task 2: AgentService Queries and Run Delegation

**Files:**

- Create: `backend/app/services/agent_service.py`
- Modify: `backend/app/agents/errors.py`
- Modify: `backend/app/agents/__init__.py`
- Create: `backend/tests/test_agent_service.py`

**Interfaces:**

- Consumes: `AgentRunCreate`, `SimpleAgentRequest`, `SimpleAgentResult`, `SimpleAgentService`, `AgentRun`, `ToolCall`.
- Produces: `AgentRunNotFoundError`; `AgentService.run(data, *, runner)`; `AgentService.get_agent_run(run_id)`; `AgentService.list_tool_calls(run_id)`.

- [x] **Step 1: Write RED service tests**

Use an in-memory or temporary SQLite engine with `Base.metadata.create_all`. Add tests that:

- `get_agent_run()` returns the exact row;
- unknown UUID raises `AgentRunNotFoundError`;
- `list_tool_calls()` returns `created_at ASC, id ASC` order;
- an existing run without ToolCalls returns `[]`;
- an unknown run raises rather than returning `[]`;
- `run()` converts `input` to `SimpleAgentRequest.content` and returns the runner result without committing.

Use a small recording runner exposing:

```python
async def run(self, request: SimpleAgentRequest) -> SimpleAgentResult:
    self.request = request
    return expected_result
```

- [x] **Step 2: Run RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_service.py -q
```

Expected: collection fails because `AgentService` and `AgentRunNotFoundError` do not exist.

- [x] **Step 3: Implement the domain error and service**

Add to `app.agents.errors`:

```python
class AgentRunNotFoundError(AgentError):
    def __init__(self, run_id: UUID) -> None:
        super().__init__(f"AgentRun not found: {run_id}")
        self.run_id = run_id
```

Implement:

```python
class AgentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def run(
        self,
        data: AgentRunCreate,
        *,
        runner: SimpleAgentService,
    ) -> SimpleAgentResult:
        return await runner.run(
            SimpleAgentRequest(
                conversation_id=data.conversation_id,
                provider=data.provider,
                model=data.model,
                content=data.input,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
                max_steps=data.max_steps,
            )
        )

    def get_agent_run(self, run_id: UUID) -> AgentRun:
        row = self._session.get(AgentRun, run_id)
        if row is None:
            raise AgentRunNotFoundError(run_id)
        return row

    def list_tool_calls(self, run_id: UUID) -> list[ToolCall]:
        self.get_agent_run(run_id)
        statement = (
            select(ToolCall)
            .where(ToolCall.agent_run_id == run_id)
            .order_by(ToolCall.created_at, ToolCall.id)
        )
        return list(self._session.scalars(statement))
```

Export the error through `app.agents.__init__`. Import `AgentService` directly
from `app.services.agent_service`; do not import it from `app.services.__init__`,
because `AgentError` depends on `app.services.errors` during package startup.

- [x] **Step 4: Run GREEN**

Run the Task 2 test command. Expected: all service tests pass.

---

### Task 3: FastAPI Dependencies and Safe Error Mapping

**Files:**

- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/errors.py`
- Modify: `backend/tests/test_agent_api.py`

**Interfaces:**

- Consumes: current request-scoped Session, Model Registry, Provider mapping, `register_builtin_tools`.
- Produces: `get_tool_registry()`, `get_simple_agent_service()`, `get_agent_service()` and stable Agent HTTP errors.

- [x] **Step 1: Write RED dependency/error tests**

Add focused unit/API tests proving:

- two calls to `get_tool_registry()` return different Registry instances containing exactly `read_file`, `list_dir`;
- `AgentModelNotFoundError` maps to 400 `model_not_found`;
- `AgentModelToolsUnsupportedError` maps to 400 `model_tools_unsupported`;
- `AgentProviderUnavailableError` maps to 503 `provider_unavailable`;
- `AgentRunNotFoundError` maps to 404 `agent_run_not_found`;
- error bodies use fixed safe messages and do not include injected provider/model diagnostics.

- [x] **Step 2: Run RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -k "dependency or error_mapping" -q
```

Expected: imports/functions or expected mappings fail.

- [x] **Step 3: Implement dependency composition**

In `dependencies.py` add:

```python
def get_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    return registry

def get_simple_agent_service(
    session: Session = Depends(get_db_session, scope="function"),
    registry: ModelRegistry = Depends(get_model_registry),
    providers: Mapping[str, BaseLLMProvider] = Depends(get_llm_providers),
    tools: ToolRegistry = Depends(get_tool_registry),
) -> SimpleAgentService:
    return SimpleAgentService(
        session,
        registry=registry,
        providers=providers,
        tools=tools,
    )

def get_agent_service(
    session: Session = Depends(get_db_session, scope="function"),
) -> AgentService:
    return AgentService(session)
```

The GET routes will depend only on `get_agent_service`; never make that dependency call either Provider or Tool dependency.

- [x] **Step 4: Implement safe error mappings**

Add fixed mappings before broader Provider/Service checks:

```python
if isinstance(exc, AgentModelNotFoundError):
    return ErrorSpec(400, "model_not_found", "The requested model is not available")
if isinstance(exc, AgentModelToolsUnsupportedError):
    return ErrorSpec(400, "model_tools_unsupported", "The requested model does not support tools")
if isinstance(exc, AgentProviderUnavailableError):
    return ErrorSpec(503, "provider_unavailable", "The requested provider is unavailable")
if isinstance(exc, AgentRunNotFoundError):
    return ErrorSpec(404, "agent_run_not_found", "Agent run not found")
```

- [x] **Step 5: Run GREEN**

Run the Task 3 test command. Expected: all selected tests pass.

---

### Task 4: Agent Routes and Response Conversion

**Files:**

- Create: `backend/app/api/v1/agents.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_agent_api.py`

**Interfaces:**

- Consumes: `AgentService`, `SimpleAgentService`, ORM `AgentRun`/`ToolCall`, Task 1 schemas.
- Produces: the three `/api/v1/agents/runs` endpoints.

- [x] **Step 1: Write RED OpenAPI and direct-answer tests**

Create a test fixture with temporary SQLite, tools-capable Mock Registry, Mock Provider, and dependency overrides. Assert OpenAPI contains exactly:

```python
assert "/api/v1/agents/runs" in paths
assert "/api/v1/agents/runs/{run_id}" in paths
assert "/api/v1/agents/runs/{run_id}/tool-calls" in paths
assert "/api/v1/agent/runs" not in paths
```

POST a direct-answer request and assert HTTP 201, completed status, goal/final answer, empty ToolCalls, server request ID, and committed Conversation/two Messages/AgentRun rows.

- [x] **Step 2: Run RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -k "openapi or direct_answer" -q
```

Expected: routes return 404 or are absent from OpenAPI.

- [x] **Step 3: Implement converters and routes**

In `api/v1/agents.py` create:

```python
router = APIRouter(prefix="/agents/runs", tags=["agents"])

def to_tool_call_read(row: ToolCall) -> ToolCallRead:
    return ToolCallRead(
        id=row.id,
        tool_call_id=row.tool_call_id,
        agent_run_id=row.agent_run_id,
        conversation_id=row.conversation_id,
        tool_name=row.tool_name,
        arguments=row.arguments_json,
        result=row.result_json,
        status=row.status,
        error=row.error_message,
        started_at=row.started_at,
        ended_at=row.ended_at,
        latency_ms=row.latency_ms,
        created_at=row.created_at,
    )
```

Add the analogous explicit `to_agent_run_read()`, then:

```python
@router.post("", response_model=AgentRunExecutionRead, status_code=201)
async def create_agent_run(
    data: AgentRunCreate,
    service: AgentService = Depends(get_agent_service),
    runner: SimpleAgentService = Depends(get_simple_agent_service),
) -> AgentRunExecutionRead:
    result = await service.run(data, runner=runner)
    return AgentRunExecutionRead(
        **to_agent_run_read(result.agent_run).model_dump(),
        tool_calls=[to_tool_call_read(row) for row in result.tool_calls],
    )

@router.get("/{run_id}", response_model=AgentRunRead)
def get_agent_run(...): ...

@router.get("/{run_id}/tool-calls", response_model=list[ToolCallRead])
def list_agent_run_tool_calls(...): ...
```

Register the router in `app.main` under `settings.api_v1_prefix`.

- [x] **Step 4: Run GREEN**

Run the Task 4 command. Expected: selected OpenAPI and direct-answer tests pass.

---

### Task 5: Tool Execution, Structured Failure, Queries, and Error Paths

**Files:**

- Modify: `backend/tests/test_agent_api.py`
- Modify: production files only when a RED test exposes a defect.

**Interfaces:**

- Consumes: all Tasks 1～4 endpoints.
- Produces: complete S1～S3 behavior and persistence/error evidence.

- [x] **Step 1: Add RED Tool round test**

Override `get_tool_registry` with a new Registry rooted at `tmp_path`; write only a harmless temporary `notes.txt`. Use a sequenced Mock Provider that first requests `read_file` and then returns final text. Assert:

- POST is 201/completed;
- one ToolCall has safe relative arguments, `success`, complete ToolResult, timing, and no absolute path metadata;
- Provider second request contains the correlated Tool observation;
- committed rows reload with the same values;
- `GET .../tool-calls` returns the same call.

- [x] **Step 2: Run the Tool test RED then GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -k "tool_round" -q
```

Expected RED if route conversion/dependency behavior is incomplete; apply the smallest root-cause fix and rerun to PASS.

- [x] **Step 3: Add structured failed-run tests**

Use Provider timeout and max-step Tool response cases. Assert POST remains 201, status is failed, `final_answer is None`, safe fixed error is present, no upstream private diagnostic appears, and the AgentRun/User Message/already executed ToolCalls are committed and queryable. Assert no assistant Message exists for failed runs.

- [x] **Step 4: Run failure tests RED then GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -k "failed_run or max_steps" -q
```

Fix only observed API integration defects, then rerun to PASS.

- [x] **Step 5: Add query and preflight error tests**

Cover:

- GET existing AgentRun;
- GET existing run with empty ToolCalls returns 200 `[]`;
- multiple ToolCalls return deterministic `created_at, id` order;
- unknown run on both GET routes returns safe 404 `agent_run_not_found`;
- malformed UUID returns unified 422;
- blank `input`, unknown field, and non-strict `max_steps` return unified 422;
- missing model and tools-unsupported model return safe 400 and no database rows;
- missing Provider returns safe 503 and no database rows;
- unknown Conversation returns safe 404 and no AgentRun;
- GET routes still succeed while `get_llm_providers` is overridden to raise a secret-bearing exception, proving GET does not resolve it.

- [x] **Step 6: Run query/error tests RED then GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py -k "query or not_found or validation or preflight or without_provider" -q
```

Apply minimal fixes and rerun to PASS.

- [x] **Step 7: Add transaction failure safety test**

Use a Session whose commit raises `SQLAlchemyError("private database diagnostic")`. With `raise_server_exceptions=False`, assert POST does not return 201, returns the unified safe database/internal response selected by the actual failure boundary, and leaks no private diagnostic. Verify a normal Session sees no persisted AgentRun.

- [x] **Step 8: Run all Agent API/service tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py tests/test_agent_service.py -q
```

Expected: all selected tests pass with no real Provider or user database access.

---

### Task 6: Focused Regression and Codex Code Self-Review

**Files:**

- Modify: tests/production only for RED/GREEN defect fixes.

**Interfaces:**

- Consumes: complete backend S1～S3 implementation.
- Produces: focused regression evidence and classified self-review findings.

- [x] **Step 1: Run focused backend regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_api.py tests/test_agent_service.py tests/test_simple_agent.py tests/test_agent_models.py tests/test_agent_migrations.py tests/test_tool_*.py tests/test_chat_api.py tests/test_chat_service.py tests/test_error_handling.py -q
```

Expected: all selected tests pass; the known Starlette/httpx deprecation warning may remain.

- [x] **Step 2: Perform Codex code self-review**

Review exact diffs against the approved spec. Classify findings as must fix, later batch, recorded limitation, or not applicable. Explicitly check:

- singular route did not appear;
- GET dependency graph does not construct Provider/Tool runtime;
- failed AgentRun follows normal commit path;
- preflight and database exceptions roll back;
- response converters cannot expose exception text, SQL fields, absolute path metadata, or credentials;
- Tool result schema handles nullable/non-terminal historical rows;
- ToolCall query verifies parent existence and uses deterministic order without claiming strict sequence;
- POST response preserves runtime ToolCall order;
- OpenAPI schema contains strict field rules;
- no M3 loop/state/migration change and no frontend/later-Plan implementation.

- [x] **Step 3: Fix every must-fix issue with RED/GREEN**

For each defect, add the smallest reproducing test, run it to observe failure, patch the root cause, rerun that test, then rerun Task 6 Step 1. Do not bundle unrelated refactors.

---

### Task 7: Formal Documentation and Execution Record

**Files:**

- Create: `docs/12-agent-api.md`
- Modify: `docs/11-simple-agent-loop.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify: this implementation plan.

**Interfaces:**

- Consumes: verified implementation and actual test results.
- Produces: accurate S1～S3 API reference, status, limitations, next-range handoff, and checked plan items.

- [x] **Step 1: Create `docs/12-agent-api.md`**

Document exact route paths, request/response fields, examples with placeholders only, 201 structured-failure semantics, error codes, transaction ownership, ToolCall ordering limitation, read-only Tool boundary, Provider-free query behavior, and current lack of frontend/streaming/retry/cancel. Do not include a real key, external URL, absolute private path, or live Provider claim.

- [x] **Step 2: Synchronize project docs**

Update `docs/11-simple-agent-loop.md` and architecture/overview/README/CHANGELOG so they state Agent API exists but frontend Agent/ToolCall views remain pending. Link the new formal doc. Preserve M3 historical acceptance statements only when clearly marked as historical.

- [x] **Step 3: Update the Plan 2 execution table**

Only after matching tests pass:

- mark Batch 10 and `P2-M4-S1～S3` complete;
- record plural route decision, `input` request field, 201 failed-run semantics, Provider-free GET queries, TDD evidence, self-review fixes, full verification count, security/boundary checks;
- keep `P2-M4-S4～S6` incomplete and identify it as the exact next batch;
- do not mark M4, Plan 2, M5, or Plan 3 complete.

- [x] **Step 4: Mark implementation-plan checkboxes accurately**

Change each completed item to `[x]` only after its named command/evidence exists. Leave no item checked based on intent.

- [x] **Step 5: Check documentation consistency**

```powershell
Get-ChildItem -LiteralPath docs,docs-plan -Recurse -File -Filter '*.md' |
  Select-String -Pattern 'TBD|TODO|/api/v1/agent/runs|无 Agent API|no current API route' -Encoding UTF8
```

Expected: no unresolved placeholder, accidental singular current route, or stale current-state claim. Historical text is allowed only when explicitly dated/labeled.

---

### Task 8: Fresh Full Verification and Final Handoff

**Files:**

- No production edits unless a fresh RED exposes a defect; any fix must use TDD and repeat affected checks.

**Interfaces:**

- Consumes: complete S1～S3 diff.
- Produces: final evidence ready for the user's manual commit.

- [x] **Step 1: Run complete backend verification**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m pip check
```

Record exact pass count, warnings, and dependency result.

- [x] **Step 2: Verify migrations on a fresh temporary SQLite only**

Create a unique file under `[System.IO.Path]::GetTempPath()`, resolve and verify it stays under that directory, set `DATABASE_URL` only for the child process, then run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
```

Delete only the verified temporary file in `finally`. Never reference or touch `backend/ai_agent_lab.db` or another existing database.

- [x] **Step 3: Run frontend regression**

From `frontend/`:

```powershell
npm run typecheck
npm run test -- --run
npm run build
```

Expected: TypeScript, all Vitest tests, and production build pass. No frontend source changes are expected.

- [x] **Step 4: Run FastAPI smoke with mocks only**

Use TestClient and dependency overrides with temporary SQLite/Mock Provider. Verify health 200, OpenAPI 200, server-controlled request ID, POST Agent Run 201, both GET queries 200, and no real Provider factory/configuration is initialized for GET.

- [x] **Step 5: Run docs, secret, artifact, and Plan-boundary checks**

Verify local Markdown links. Scan tracked/changed text for real secret patterns while recognizing documented placeholders/test literals. Confirm status contains no `.env`, SQLite DB, `__pycache__`, `.pyc`, coverage, or frontend `dist` artifacts. Confirm no changes under:

- `backend/alembic/`
- `backend/app/models/`
- `frontend/src/`
- `backend/app/providers/`
- `backend/app/tools/`

Confirm no singular Agent route, `web_fetch` runtime, RAG, Embedding, Memory, MCP, Shell/write/delete Tool, retry/cancel/resume, frontend M4 S4～S6, or Plan 3 implementation appeared.

- [x] **Step 6: Run final Git checks**

```powershell
git diff --check
git status --short --branch
git diff --stat
git diff -- backend/app backend/tests docs README.md README_CN.md CHANGELOG.md docs-plan
```

Confirm `HEAD` and `origin/main` remain at the starting commit, nothing is staged, and every changed file belongs to S1～S3/docs/evidence.

- [x] **Step 7: Final Codex self-review and handoff**

Re-read the approved design and source P2-M4-S1～S3 rows. Report exact requirement-to-evidence coverage, must-fix RED/GREEN fixes, later-batch items, accepted limitations, not-applicable items, full verification, Git state, and whether the repository can enter `P2-M4-S4～S6`.

Suggested manual commit message after every check passes:

```text
feat(agent): add agent run api
```
