# Plan 4 M2 S7～S9 Trace API And Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Trace list/detail API and a responsive fourth Trace workspace that can replay Chat and RAG Runs as ordered Steps and retrieval candidates.

**Architecture:** A new `TraceQueryService` performs bounded deterministic SQLite reads and returns a typed aggregate without initializing Providers or Qdrant. A thin FastAPI router maps that aggregate to strict public schemas. The React workspace uses a typed API wrapper, URL-restored Run selection, request-generation guards, focused list/detail/step/candidate components, and synthetic browser acceptance.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, pytest, React 19, TypeScript 5.9, Vitest/jsdom, Vite, Playwright browser acceptance.

## Global Constraints

- Work only on `P4-M2-S7～S9`; P4-M2-S10 documentation/review and all Advanced RAG/Evaluation/Plan 5 runtime remain out of scope.
- Keep routes thin: route validation and response mapping call a service that owns database queries.
- Do not change Trace ORM fields, Alembic head `20260808_0009`, Chat/RAG response schemas, or persistence hooks.
- List limit defaults to 50, accepts 1～100, and orders Runs by `created_at DESC, id DESC`.
- Detail orders Steps by `step_index`, retrieval Runs by `created_at, id`, and candidates by `rank, id`.
- Candidate API/UI content remains the persisted 500-character preview; never reconstruct full Prompt, RAG context, vector payload, or arbitrary metadata.
- Agent and Trace share the existing `run` query key; switching to a different workspace must remove an incompatible `run` value.
- Use only Mock/synthetic data and system-temporary SQLite. Do not read `backend/ai_agent_lab.db`, real `.env`, secrets, browser credentials, or call real Providers/Qdrant/network Tools.
- Follow strict RED → GREEN → REFACTOR. Codex must not stage or commit; the user performs one manual verified-batch commit.

---

### Task 1: Trace Query Schemas And Read Service

**Files:**
- Create: `backend/app/schemas/trace_query.py`
- Create: `backend/app/services/trace_query_service.py`
- Create: `backend/tests/test_trace_query_schemas.py`
- Create: `backend/tests/test_trace_query_service.py`

**Interfaces:**
- Consumes: `TraceRun`, `TraceStep`, `RagRetrievalRun`, `RagRetrievalCandidate`, `TraceRunRead`, `TraceStepRead`.
- Produces: `TraceRunSummaryRead`, `RagRetrievalCandidateRead`, `RagRetrievalRunRead`, `TraceRunDetailRead`, `TraceRunListItem`, `TraceRetrievalDetail`, `TraceDetail`, `TraceQueryService.list_trace_runs(limit=...)`, and `TraceQueryService.get_trace_detail(...)`.

- [ ] **Step 1: Write strict schema RED tests**

Create exact construction/serialization tests proving `input_preview` is at most 160 characters, UUID/datetime/Decimal serialize correctly, nested candidates remain ordered input data, unknown fields fail, JSON metadata rejects non-JSON values, and counts/ranks/latencies/scores reject invalid values.

```python
TRACE_ID = UUID(int=1)
STEP_ID = UUID(int=2)
RETRIEVAL_ID = UUID(int=3)
CANDIDATE_ID = UUID(int=4)
KNOWLEDGE_BASE_ID = UUID(int=5)
DOCUMENT_ID = UUID(int=6)
CHUNK_ID = UUID(int=7)
CONVERSATION_ID = UUID(int=8)
USER_MESSAGE_ID = UUID(int=9)


def test_trace_detail_schema_serializes_nested_public_contract() -> None:
    now = datetime(2026, 8, 9, 12, 0, 0)
    candidate = RagRetrievalCandidateRead(
        id=CANDIDATE_ID,
        retrieval_run_id=RETRIEVAL_ID,
        chunk_id=CHUNK_ID,
        document_id=DOCUMENT_ID,
        rank=1,
        final_rank=1,
        source="dense",
        dense_score=0.91,
        sparse_score=None,
        fused_score=None,
        rerank_score=None,
        selected=True,
        content_preview="Architecture source",
        metadata_json={"filename": "architecture.md"},
        created_at=now,
    )
    retrieval = RagRetrievalRunRead(
        id=RETRIEVAL_ID,
        trace_run_id=TRACE_ID,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        strategy_name="naive_vector",
        original_query="Where is the design?",
        rewritten_query=None,
        top_k=5,
        candidate_count=1,
        selected_count=1,
        score_threshold=0.5,
        latency_ms=12,
        metadata_filter_json={"embedding_model": "mock-embedding"},
        strategy_config_json={},
        created_at=now,
        candidates=[candidate],
    )
    step = TraceStepRead(
        id=STEP_ID,
        trace_run_id=TRACE_ID,
        step_index=1,
        step_type="rag_retrieve",
        name="Retrieve knowledge base",
        status="completed",
        input_json={"top_k": 5},
        output_json={"retrieval_run_id": str(RETRIEVAL_ID)},
        error_message=None,
        latency_ms=12,
        started_at=now,
        ended_at=now,
        created_at=now,
    )
    detail = TraceRunDetailRead(
        id=TRACE_ID,
        run_type="rag_chat",
        conversation_id=CONVERSATION_ID,
        agent_run_id=None,
        user_message_id=USER_MESSAGE_ID,
        title=None,
        status="completed",
        input_text="Where is the design?",
        output_text="The design is in the architecture document.",
        provider="mock",
        model="mock-chat",
        total_input_tokens=7,
        total_output_tokens=5,
        total_tokens=12,
        estimated_cost=Decimal("0.00000700"),
        latency_ms=18,
        error_message=None,
        metadata_json={"prompt_version": "naive-rag-v1"},
        started_at=now,
        ended_at=now,
        created_at=now,
        steps=[step],
        retrieval_runs=[retrieval],
    )
    payload = detail.model_dump(mode="json")
    assert payload["steps"][0]["step_index"] == 1
    assert payload["retrieval_runs"][0]["candidates"][0]["rank"] == 1
    assert payload["estimated_cost"] == "0.00000700"


def test_trace_summary_rejects_preview_over_160_characters() -> None:
    with pytest.raises(ValidationError):
        TraceRunSummaryRead(
            id=TRACE_ID,
            run_type="rag_chat",
            status="completed",
            title=None,
            input_preview="界" * 161,
            conversation_id=None,
            agent_run_id=None,
            user_message_id=None,
            provider=None,
            model=None,
            total_input_tokens=None,
            total_output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            latency_ms=0,
            error_message=None,
            started_at=None,
            ended_at=None,
            created_at=datetime(2026, 8, 9, 12, 0, 0),
        )
```

- [ ] **Step 2: Run schema tests and verify RED**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_trace_query_schemas.py -q
```

Expected: collection fails because `app.schemas.trace_query` does not exist.

- [ ] **Step 3: Implement strict public schemas**

Use `ConfigDict(extra="forbid", from_attributes=True)` and existing enums. Define exact read shapes:

```python
class TraceRunSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    run_type: TraceRunType
    status: TraceStatus
    title: str | None
    input_preview: str = Field(min_length=1, max_length=160)
    conversation_id: UUID | None
    agent_run_id: UUID | None
    user_message_id: UUID | None
    provider: TraceProviderIdentifier | None
    model: TraceModelIdentifier | None
    total_input_tokens: StrictInt | None = Field(default=None, ge=0)
    total_output_tokens: StrictInt | None = Field(default=None, ge=0)
    total_tokens: StrictInt | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    latency_ms: StrictInt | None = Field(default=None, ge=0)
    error_message: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class RagRetrievalCandidateRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    retrieval_run_id: UUID
    chunk_id: UUID
    document_id: UUID
    rank: StrictInt = Field(gt=0)
    final_rank: StrictInt | None = Field(default=None, gt=0)
    source: Literal["dense", "sparse", "hybrid", "parent", "rerank"]
    dense_score: FiniteFloat | None = None
    sparse_score: FiniteFloat | None = None
    fused_score: FiniteFloat | None = None
    rerank_score: FiniteFloat | None = None
    selected: StrictBool
    content_preview: str = Field(min_length=1, max_length=500)
    metadata_json: dict[str, JsonValue]
    created_at: datetime


class RagRetrievalRunRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    trace_run_id: UUID
    knowledge_base_id: UUID
    strategy_name: str = Field(min_length=1, max_length=64)
    original_query: str = Field(min_length=1, max_length=20_000)
    rewritten_query: str | None = Field(default=None, min_length=1, max_length=20_000)
    top_k: StrictInt = Field(ge=1, le=100)
    candidate_count: StrictInt = Field(ge=0, le=100)
    selected_count: StrictInt = Field(ge=0, le=100)
    score_threshold: FiniteFloat | None
    latency_ms: StrictInt = Field(ge=0)
    metadata_filter_json: dict[str, JsonValue]
    strategy_config_json: dict[str, JsonValue]
    created_at: datetime
    candidates: list[RagRetrievalCandidateRead]


class TraceRunDetailRead(TraceRunRead):
    steps: list[TraceStepRead]
    retrieval_runs: list[RagRetrievalRunRead]
```

- [ ] **Step 4: Write service RED tests**

Use temporary SQLite and real ORM rows. Prove empty list, default caller limit behavior, deterministic Run tie ordering, Unicode preview truncation to 159 characters plus `…`, Step ordering, retrieval/candidate tie ordering, zero candidates, and not-found behavior.

```python
def test_trace_query_service_returns_deterministic_nested_detail(session: Session) -> None:
    service = TraceQueryService(session)
    detail = service.get_trace_detail(TRACE_ID)
    assert [step.step_index for step in detail.steps] == [1, 2, 3, 4]
    assert [item.record.id for item in detail.retrievals] == [RETRIEVAL_A, RETRIEVAL_B]
    assert [row.rank for row in detail.retrievals[0].candidates] == [1, 2]


def test_trace_query_service_raises_safe_not_found(session: Session) -> None:
    with pytest.raises(TraceRunNotFoundError):
        TraceQueryService(session).get_trace_detail(uuid4())
```

- [ ] **Step 5: Run service tests and verify RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_query_service.py -q
```

Expected: collection fails because `TraceQueryService` and `TraceRunNotFoundError` do not exist.

- [ ] **Step 6: Implement the read aggregate and bounded queries**

Define service-owned immutable aggregates and explicit bounded queries:

```python
@dataclass(frozen=True, slots=True)
class TraceRunListItem:
    record: TraceRun
    input_preview: str


@dataclass(frozen=True, slots=True)
class TraceRetrievalDetail:
    record: RagRetrievalRun
    candidates: tuple[RagRetrievalCandidate, ...]


@dataclass(frozen=True, slots=True)
class TraceDetail:
    record: TraceRun
    steps: tuple[TraceStep, ...]
    retrievals: tuple[TraceRetrievalDetail, ...]


class TraceRunNotFoundError(Exception):
    def __init__(self, trace_run_id: UUID) -> None:
        self.trace_run_id = trace_run_id
        super().__init__("Trace run not found")


class TraceQueryService:
    def list_trace_runs(self, *, limit: int) -> list[TraceRunListItem]:
        statement = (
            select(TraceRun)
            .order_by(TraceRun.created_at.desc(), TraceRun.id.desc())
            .limit(limit)
        )
        return [
            TraceRunListItem(
                record=row,
                input_preview=_input_preview(row.input_text),
            )
            for row in self._session.scalars(statement)
        ]

    def get_trace_detail(self, trace_run_id: UUID) -> TraceDetail:
        record = self._session.get(TraceRun, trace_run_id)
        if record is None:
            raise TraceRunNotFoundError(trace_run_id)
        steps = tuple(
            self._session.scalars(
                select(TraceStep)
                .where(TraceStep.trace_run_id == trace_run_id)
                .order_by(TraceStep.step_index, TraceStep.id)
            )
        )
        retrieval_rows = tuple(
            self._session.scalars(
                select(RagRetrievalRun)
                .where(RagRetrievalRun.trace_run_id == trace_run_id)
                .order_by(RagRetrievalRun.created_at, RagRetrievalRun.id)
            )
        )
        retrieval_ids = [row.id for row in retrieval_rows]
        candidate_rows = () if not retrieval_ids else tuple(
            self._session.scalars(
                select(RagRetrievalCandidate)
                .where(RagRetrievalCandidate.retrieval_run_id.in_(retrieval_ids))
                .order_by(
                    RagRetrievalCandidate.retrieval_run_id,
                    RagRetrievalCandidate.rank,
                    RagRetrievalCandidate.id,
                )
            )
        )
        grouped: dict[UUID, list[RagRetrievalCandidate]] = {
            row.id: [] for row in retrieval_rows
        }
        for candidate in candidate_rows:
            grouped[candidate.retrieval_run_id].append(candidate)
        return TraceDetail(
            record=record,
            steps=steps,
            retrievals=tuple(
                TraceRetrievalDetail(row, tuple(grouped[row.id]))
                for row in retrieval_rows
            ),
        )
```

Implement `_input_preview(value)` as the original string when length is at most 160, otherwise `value[:159] + "…"`.

- [ ] **Step 7: Run Task 1 GREEN and adjacent model/schema regressions**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_query_schemas.py tests/test_trace_query_service.py tests/test_trace_schemas.py tests/test_trace_models.py tests/test_retrieval_schemas.py tests/test_retrieval_models.py -q
```

Expected: all selected tests pass with no new warning.

- [ ] **Step 8: Record the Task 1 checkpoint without Git mutation**

Run `git diff --check` and inspect `git status --short`; do not stage or commit.

---

### Task 2: Thin Trace API And Safe Errors

**Files:**
- Create: `backend/app/api/v1/traces.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/errors.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_trace_api.py`

**Interfaces:**
- Consumes: Task 1 service/results/schemas and `get_db_session`.
- Produces: `GET /api/v1/traces`, `GET /api/v1/traces/{trace_run_id}`, `get_trace_query_service`, and stable `trace_run_not_found` mapping.

- [ ] **Step 1: Write API RED tests**

Build a temporary SQLite FastAPI fixture without Provider overrides. Test OpenAPI paths, empty list, default/explicit limit, ordering, exact summary/detail JSON, completed and failed Runs, zero candidates, unknown UUID 404, malformed UUID/limit 422, and SQL error 503 redaction.

```python
def test_trace_api_reads_without_runtime_provider_dependencies(trace_api_context: Any) -> None:
    client, _, dependency_calls = trace_api_context
    response = client.get("/api/v1/traces?limit=25")
    assert response.status_code == 200
    assert dependency_calls == []


def test_trace_api_returns_safe_unknown_run(trace_api_context: Any) -> None:
    client, _, _ = trace_api_context
    response = client.get(f"/api/v1/traces/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "trace_run_not_found"
    assert response.headers["x-request-id"]
```

- [ ] **Step 2: Run API tests and verify RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_api.py -q
```

Expected: OpenAPI/requests fail because the Trace router is absent.

- [ ] **Step 3: Implement dependency, router, mapping, and error registration**

Add the dependency:

```python
def get_trace_query_service(
    session: Session = Depends(get_db_session, scope="function"),
) -> TraceQueryService:
    return TraceQueryService(session)
```

Add route contracts:

```python
router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceRunSummaryRead])
def list_trace_runs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    service: TraceQueryService = Depends(get_trace_query_service),
) -> list[TraceRunSummaryRead]:
    return [to_trace_summary(row) for row in service.list_trace_runs(limit=limit)]


@router.get("/{trace_run_id}", response_model=TraceRunDetailRead)
def get_trace_run_detail(
    trace_run_id: UUID,
    service: TraceQueryService = Depends(get_trace_query_service),
) -> TraceRunDetailRead:
    return to_trace_detail(service.get_trace_detail(trace_run_id))
```

Register the router in `main.py`. Map `TraceRunNotFoundError` before generic exceptions:

```python
if isinstance(exc, TraceRunNotFoundError):
    return ErrorSpec(404, "trace_run_not_found", "Trace run not found")
```

Register its exception class with `unified_error_handler` so direct API calls receive the safe envelope.

- [ ] **Step 4: Run Task 2 GREEN and API compatibility tests**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_api.py tests/test_trace_query_service.py tests/test_trace_query_schemas.py tests/test_chat_api.py tests/test_rag_api.py tests/test_agent_api.py -q
```

Expected: all selected tests pass with only the existing TestClient warning if emitted.

- [ ] **Step 5: Record the Task 2 checkpoint without Git mutation**

Run `git diff --check`, inspect OpenAPI only through `TestClient`, and confirm no migration file or runtime Provider code changed.

---

### Task 3: Frontend Trace Types, API, URL, And Navigation

**Files:**
- Create: `frontend/src/types/trace.ts`
- Create: `frontend/src/api/traces.ts`
- Create: `frontend/src/api/traces.test.ts`
- Modify: `frontend/src/utils/agentUrl.ts`
- Modify: `frontend/src/utils/agentUrl.test.ts`
- Modify: `frontend/src/components/WorkspaceSidebar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 2 JSON contracts and existing API URL/error envelope conventions.
- Produces: exact Trace TypeScript types, `TraceApiError`, `fetchTraceRuns`, `fetchTraceRunDetail`, `WorkspaceView="trace"`, `readTraceRunId`, `buildTraceRunUrl`, and the fourth workspace route.

- [ ] **Step 1: Write API wrapper RED tests**

Use exact synthetic summary/detail fixtures. Assert URLs, default/explicit limit, detail path encoding, structured errors, network failures, non-JSON failures, and successful non-JSON responses.

```typescript
await fetchTraceRuns();
await fetchTraceRuns(25);
await fetchTraceRunDetail(traceId);

expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
  "http://localhost:8000/api/v1/traces?limit=50",
  "http://localhost:8000/api/v1/traces?limit=25",
  `http://localhost:8000/api/v1/traces/${traceId}`,
]);
```

- [ ] **Step 2: Run API tests and verify RED**

Run:

```powershell
cd frontend
npm test -- src/api/traces.test.ts
```

Expected: collection fails because `api/traces.ts` and `types/trace.ts` do not exist.

- [ ] **Step 3: Implement exact types and safe API wrapper**

Define string unions for every backend enum and exact nested objects. Implement the existing safe wrapper pattern with a Trace-specific error:

```typescript
export class TraceApiError extends Error {
  readonly code: string | null;
  readonly requestId: string | null;
  readonly status: number | null;
}

export function fetchTraceRuns(limit = 50): Promise<TraceRunSummary[]> {
  return requestTraceJson<TraceRunSummary[]>(`/traces?limit=${limit}`);
}

export function fetchTraceRunDetail(traceRunId: string): Promise<TraceRunDetail> {
  return requestTraceJson<TraceRunDetail>(
    `/traces/${encodeURIComponent(traceRunId)}`,
  );
}
```

`requestTraceJson()` catches fetch failures, parses JSON once, never includes response bodies in errors, and returns `TraceApiError("Trace API returned invalid JSON", {status})` for a successful non-JSON response.

- [ ] **Step 4: Write URL/navigation RED tests**

Update the URL tests to prove all four workspaces, valid/invalid Trace UUID, setting/clearing Trace Run, and incompatible `run` cleanup across Agent/Trace/Knowledge/Chat transitions.

```typescript
expect(readWorkspace("?workspace=trace")).toBe("trace");
expect(readTraceRunId(`?workspace=trace&run=${TRACE_ID}`)).toBe(TRACE_ID);
expect(
  buildWorkspaceUrl(
    `http://localhost:5173/?workspace=agent&run=${AGENT_ID}`,
    "trace",
  ),
).toBe("http://localhost:5173/?workspace=trace");
```

Update `App.test.tsx` to expect a Trace page skeleton for `?workspace=trace`, and add a Sidebar-render assertion for the fourth `Trace workspace` button.

- [ ] **Step 5: Run URL/navigation tests and verify RED**

Run:

```powershell
npm test -- src/utils/agentUrl.test.ts src/App.test.tsx
```

Expected: assertions fail because `trace` is not an accepted workspace and no page/sidebar entry exists.

- [ ] **Step 6: Implement URL helpers and workspace wiring**

Extend the union and route:

```typescript
export type WorkspaceView = "chat" | "agent" | "knowledge" | "trace";

export function readTraceRunId(search: string): string | null {
  const runId = new URLSearchParams(search).get("run");
  return runId !== null && UUID_PATTERN.test(runId) ? runId : null;
}

export function buildTraceRunUrl(href: string, runId: string | null): string {
  const url = new URL(href);
  runId === null ? url.searchParams.delete("run") : url.searchParams.set("run", runId);
  return url.toString();
}
```

In `buildWorkspaceUrl()`, read the current encoded workspace before mutation and delete `run` when the resolved current workspace differs from the target workspace. Preserve unrelated `conversation` and hash values.

Add the `ChartNoAxesCombined` icon and Trace button to `WorkspaceSidebar`; extend its discriminated prop union with `activeWorkspace: "trace"`. Render `TraceTimelinePage` from `App` when selected. At this checkpoint the page exports only the tested loading shell; no final Timeline behavior is added until Task 4 RED tests exist.

- [ ] **Step 7: Run Task 3 GREEN**

Run:

```powershell
npm test -- src/api/traces.test.ts src/utils/agentUrl.test.ts src/App.test.tsx
npm run typecheck
```

Expected: selected tests and TypeScript checking pass.

- [ ] **Step 8: Record the Task 3 checkpoint without Git mutation**

Inspect the frontend diff and confirm no Chat/Agent/Knowledge API contract was changed.

---

### Task 4: Trace Timeline Components And Page State

**Files:**
- Create: `frontend/src/components/trace/TraceRunList.tsx`
- Create: `frontend/src/components/trace/TraceRunList.test.tsx`
- Create: `frontend/src/components/trace/TraceCandidateTable.tsx`
- Create: `frontend/src/components/trace/TraceCandidateTable.test.tsx`
- Create: `frontend/src/components/trace/TraceStepCard.tsx`
- Create: `frontend/src/components/trace/TraceStepTimeline.tsx`
- Create: `frontend/src/components/trace/TraceStepTimeline.test.tsx`
- Create: `frontend/src/pages/TraceTimelinePage.tsx`
- Create: `frontend/src/pages/TraceTimelinePage.test.tsx`
- Create: `frontend/src/pages/TraceTimelinePage.dom.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: Task 3 Trace types/API/URL helpers and shared `WorkspaceSidebar`/health API.
- Produces: recent Run list, Run detail summary, ordered Step Timeline, retrieval/candidate display, and stale-safe page orchestration.

- [ ] **Step 1: Write component RED tests**

Use static rendering for pure presentation. Prove list loading/empty/error/selected states; full IDs; status/type labels; failed Step error; collapsed JSON `<details>`; `rag_retrieve` mapping; candidate ordering and score display; zero candidates; malformed/missing retrieval ID fallback.

```typescript
const html = renderToStaticMarkup(
  <TraceStepTimeline detail={ragTraceDetail} />,
);
expect(html).toContain("rag_retrieve");
expect(html).toContain("build_prompt");
expect(html).toContain("llm_call");
expect(html).toContain("final_answer");
expect(html.indexOf("Rank 1")).toBeLessThan(html.indexOf("Rank 2"));
expect(html).toContain(ragTraceDetail.retrieval_runs[0].knowledge_base_id);
```

- [ ] **Step 2: Run component tests and verify RED**

Run:

```powershell
npm test -- src/components/trace
```

Expected: collection fails because Trace components do not exist.

- [ ] **Step 3: Implement focused presentation components**

Keep data lookup pure and defensive:

```typescript
export function retrievalRunIdForStep(step: TraceStep): string | null {
  const candidate = step.output_json?.retrieval_run_id;
  return typeof candidate === "string" ? candidate : null;
}

export function retrievalForStep(
  step: TraceStep,
  retrievalRuns: RagRetrievalRun[],
): RagRetrievalRun | null {
  const id = retrievalRunIdForStep(step);
  return id === null
    ? null
    : (retrievalRuns.find((item) => item.id === id) ?? null);
}
```

`TraceStepCard` uses `<details><summary>Input metadata</summary><pre>...</pre></details>` and the equivalent output block. `JSON.stringify(value, null, 2)` is presentation-only and never mutates metadata. Candidate score selection displays all non-null score fields with their exact names rather than guessing one universal score.

- [ ] **Step 4: Write mounted page RED tests**

Mock health and Trace API functions in jsdom. Test:

1. list load selects the first Run and writes its URL;
2. valid deep link loads even when absent from recent 50;
3. list empty/error and retry;
4. detail error keeps list usable and retries the same ID;
5. selecting a second Run before the first detail resolves ignores the stale first response;
6. unmount ignores late list/detail responses;
7. failed Run/Step and zero-candidate detail render safely.

```typescript
it("ignores a stale detail response after a newer Run is selected", async () => {
  const first = deferred<TraceRunDetail>();
  vi.mocked(fetchTraceRunDetail)
    .mockReturnValueOnce(first.promise)
    .mockResolvedValueOnce(secondDetail);
  const { container, root } = mountPage();
  await flushEffects();
  clickRun(container, SECOND_TRACE_ID);
  await flushEffects();
  await resolveDeferred(first, firstDetail);
  expect(container.textContent).toContain(secondDetail.output_text);
  expect(container.textContent).not.toContain(firstDetail.output_text);
  act(() => root.unmount());
});
```

- [ ] **Step 5: Run page tests and verify RED**

Run:

```powershell
npm test -- src/pages/TraceTimelinePage.test.tsx src/pages/TraceTimelinePage.dom.test.tsx
```

Expected: missing state/page behavior assertions fail.

- [ ] **Step 6: Implement independent list/detail state machines**

Use discriminated states and generation counters:

```typescript
type TraceListState =
  | { status: "loading" }
  | { status: "ready"; runs: TraceRunSummary[] }
  | { status: "error"; message: string; requestId: string | null };

type TraceDetailState =
  | { status: "idle" }
  | { status: "loading"; runId: string }
  | { status: "ready"; detail: TraceRunDetail }
  | { status: "error"; runId: string; message: string; requestId: string | null };
```

Increment `listRequestRef` and `detailRequestRef` before each request and on unmount. Only the current generation may update state or URL. After list success, prefer the validated initial URL ID; otherwise preserve an already selected ID; otherwise select the first returned Run.

- [ ] **Step 7: Add dense responsive styles**

Add Trace-prefixed classes only. Desktop uses `grid-template-columns: minmax(250px, 320px) minmax(0, 1fr)`. Candidate rows use a compact CSS grid/table inside an overflow-bounded component, while the page itself remains `min-width: 0`. Under the existing `@media (max-width: 720px)`, stack list/detail, constrain list height, wrap IDs/previews/JSON with `overflow-wrap: anywhere`, and ensure `.workspace-navigation` accommodates four equal buttons.

- [ ] **Step 8: Run Task 4 GREEN and frontend regression**

Run:

```powershell
npm test -- src/components/trace src/pages/TraceTimelinePage.test.tsx src/pages/TraceTimelinePage.dom.test.tsx src/App.test.tsx src/utils/agentUrl.test.ts
npm run typecheck
npm test
npm run build
```

Expected: all selected and complete frontend tests pass, TypeScript passes, and production build succeeds.

- [ ] **Step 9: Record the Task 4 checkpoint without Git mutation**

Inspect the frontend diff, verify every async state is represented, and confirm page-level horizontal overflow rules exist for desktop and narrow layouts.

---

### Task 5: Documentation, Browser Acceptance, Full Regression, And Self-Review

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/30-trace-observability.md`
- Modify: `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`
- Create: `docs/reviews/2026-08-09-plan4-m2-s7-s9-review.md`
- Create: `docs/assets/plan4/trace-timeline-desktop.png`
- Create: `docs/assets/plan4/trace-timeline-mobile.png`

**Interfaces:**
- Consumes: completed backend/frontend contracts and fresh verification output.
- Produces: current-scope documentation, reproducible browser evidence, final finding classification, and manual Git handoff.

- [ ] **Step 1: Update current-scope documentation**

Document the two endpoints, list/detail boundaries, deterministic ordering, safe candidate preview, fourth workspace/deep link, async states, and explicit deferrals. Mark only Batch 6/P4-M2-S7～S9 complete. Do not create `docs/31-trace-timeline.md` or mark S10 complete.

- [ ] **Step 2: Run matching backend verification**

Run the new Trace service/schema/API tests plus existing Trace/RAG/Chat API/service/model groups in one command. Expected: zero failures and only the known Starlette/httpx deprecation warning if still emitted.

- [ ] **Step 3: Run full backend in isolated temporary state**

Create a GUID-named directory under `[IO.Path]::GetTempPath()`, validate its resolved path remains beneath the system temp root, set `DATABASE_URL` to a SQLite file there and `DOCUMENT_STORAGE_ROOT` to an `uploads` child, run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Use terminating PowerShell errors, preserve the external command exit code, remove only the validated temporary directory in `finally`, and confirm removal. Never fall back to the repository database.

- [ ] **Step 4: Re-run complete frontend verification**

Run:

```powershell
npm run typecheck
npm test
npm run build
```

Record exact file/test/module counts.

- [ ] **Step 5: Run synthetic browser acceptance**

Invoke the Playwright skill before browser automation. Start only the local frontend dev server. Intercept `/api/v1/health`, `/api/v1/traces`, and `/api/v1/traces/{id}` with complete synthetic completed/failed Chat/RAG payloads. At `1440×900` and `390×844`, verify:

- Trace navigation and recent Run selection;
- deep-link restoration;
- full RAG four-Step order;
- metadata expansion and ordered candidates;
- failed Run/Step rendering;
- zero failed requests, console warnings/errors, and horizontal overflow.

Save sanitized synthetic screenshots as the two declared Plan 4 assets. Inspect both images before handoff and verify they contain no real credential, user data, local absolute path, browser chrome/profile data, or unsanitized Provider diagnostics.

- [ ] **Step 6: Run repository hygiene checks**

Run `git diff --check`; scan all tracked plus intended untracked Markdown links; scan changed files for high-confidence secrets/private keys, new network clients/Tools, generated artifacts, later-Plan runtime paths, and database files; verify staged paths are zero; verify branch, HEAD, `origin/main`, and annotated release tag refs are unchanged from the batch baseline.

- [ ] **Step 7: Perform Codex self-review and fix with TDD if needed**

Classify every finding as must fix, fix later, recorded limitation, or not applicable. Check API ordering/query counts, safe errors, nested schema fidelity, URL collision cleanup, stale response protection, responsive overflow, scope, secret boundaries, and documentation accuracy. Any Critical/Important current-batch issue requires a reproducing RED test, minimal fix, and fresh matching/full regression.

- [ ] **Step 8: Complete the formal review and handoff**

Write exact RED/GREEN evidence, verification counts, browser evidence, findings, limitations, and next-step gate into the review record. Leave all changes unstaged on `main`. Suggest this manual commit message:

```text
feat(observability): add trace api and timeline
```
