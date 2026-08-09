# Plan 4 M2 S7～S9 Trace API And Timeline Design

## 1. Scope

This batch implements only:

- P4-M2-S7: read-only Trace list/detail API;
- P4-M2-S8: frontend Trace API wrapper and TypeScript contracts;
- P4-M2-S9: a responsive Trace workspace and Timeline.

It exposes the Trace, Step, retrieval Run, and retrieval candidate records
implemented through P4-M2-S6. It does not add Trace persistence hooks, change
RAG/Chat responses, add Agent/Tool Trace, implement Advanced Retrieval,
reranking, evaluation, Memory, Agent Runtime v2, Human Approval, MCP, or any
multimodal runtime. P4-M2-S10 still owns the complete M2 review and dedicated
Timeline usage document.

## 2. Accepted Product Choice

Trace is a fourth top-level workspace beside Chat, Agent, and Knowledge. The
workspace shows recent Trace Runs and one selected Run's Timeline. Its stable
URL is:

```text
?workspace=trace&run=<canonical UUID>
```

The page can restore a valid Run deep link after refresh. An absent or invalid
`run` query value does not trigger an invalid API request; the page selects the
first recent Run when one exists and normalizes the URL after that selection.

This batch does not add `trace_run_id` to Chat or RAG response payloads. The
recent-Run list is the approved entry point.

## 3. Backend Architecture

### 3.1 Read Service

Create a read-only `TraceQueryService` in the service layer. It owns SQLAlchemy
queries and not-found policy; the API route owns only parameter/schema
validation and response mapping.

The service provides:

```python
def list_trace_runs(self, *, limit: int) -> list[TraceRun]
def get_trace_detail(self, trace_run_id: UUID) -> TraceDetail
```

`TraceDetail` is a service result containing one `TraceRun`, its ordered
`TraceStep` rows, and its retrieval Runs with ordered candidates. The detail
query must avoid per-candidate N+1 loading by using explicit eager-loading or
bounded explicit queries. It must not initialize LLM, Embedding, Qdrant, or any
Tool runtime.

### 3.2 API Endpoints

Add a router with prefix `/traces` and tag `traces`:

```http
GET /api/v1/traces?limit=50
GET /api/v1/traces/{trace_run_id}
```

List rules:

- `limit` defaults to 50 and accepts strict integers from 1 through 100;
- rows are ordered by `created_at DESC, id DESC`;
- all implemented run types and statuses are included;
- the response is a JSON array of Run summaries and contains no nested Steps or
  candidates.

Detail rules:

- one response contains the complete public Run, Steps ordered by
  `step_index`, retrieval Runs in deterministic `created_at, id` order, and
  candidates ordered by `rank, id`;
- an unknown UUID returns `404 trace_run_not_found` with the existing safe error
  envelope;
- malformed UUIDs and invalid limits use the existing `422 validation_error`;
- reads never mutate Trace state and use the request-owned SQLAlchemy Session.

### 3.3 Public Schemas

Keep existing create/read schemas intact and add dedicated query schemas:

- `TraceRunSummaryRead`: Run identity, type, status, title, a dedicated
  `input_preview` capped at 160 Unicode characters, provider/model, metrics,
  correlations, error, and timestamps;
- `TraceStepRead`: existing complete public Step contract;
- `RagRetrievalCandidateRead`: all existing bounded candidate snapshot fields;
- `RagRetrievalRunRead`: retrieval Run fields plus ordered candidates;
- `TraceRunDetailRead`: complete Run fields plus ordered Steps and retrieval
  Runs.

The API returns the persisted `input_text` and `output_text` only in the detail
response. The list uses a deterministic input preview capped at 160 Unicode
characters so the response remains scan-friendly. API schemas remain strict,
forbid unknown fields, serialize UUID/datetime/Decimal values through Pydantic,
and never reconstruct omitted Prompt/context/vector data.

No ORM field or Alembic migration is needed.

## 4. Frontend Contracts

Create `frontend/src/types/trace.ts` for exact API types:

- run/step type and status unions matching backend string enums;
- `TraceRunSummary`;
- `TraceStep`;
- `RagRetrievalRun` and `RagRetrievalCandidate`;
- `TraceRunDetail`.

JSON metadata uses `Record<string, unknown>`. Cost is represented as a string
because FastAPI/Pydantic serializes the database Decimal without requiring
frontend floating-point arithmetic.

Create `frontend/src/api/traces.ts` with:

```typescript
fetchTraceRuns(limit?: number): Promise<TraceRunSummary[]>
fetchTraceRunDetail(traceRunId: string): Promise<TraceRunDetail>
```

The wrapper follows the existing structured-error boundary and exposes a
`TraceApiError` carrying safe code, request ID, and HTTP status. It normalizes
transport failures and invalid successful JSON without including response
bodies in errors.

## 5. Workspace And URL State

Extend `WorkspaceView` with `trace`. `readWorkspace()` accepts exactly that
value and `WorkspaceSidebar` exposes a fourth navigation button. Chat remains
the default when no workspace is present.

Add Trace URL helpers:

```typescript
readTraceRunId(search: string): string | null
buildTraceRunUrl(href: string, runId: string | null): string
```

They accept canonical UUID-shaped values case-insensitively and preserve
unrelated query parameters. Agent and Trace both use the established `run`
parameter, so `buildWorkspaceUrl()` must clear `run` whenever the target
workspace differs from the workspace encoded by the current URL. It must also
clear `run` when leaving or resetting a selection, preventing an Agent Run ID
from being interpreted as a Trace Run ID or vice versa. The Trace page updates
the URL only for the current mounted selection request.

## 6. Timeline UI

### 6.1 Page Layout

Create `TraceTimelinePage` as a quiet, dense engineering workspace:

- shared `WorkspaceSidebar` on the left;
- Trace header with health status;
- recent Runs column;
- selected Run detail column.

Desktop uses a two-column Trace content area. Narrow screens stack the recent
Runs above detail. IDs, JSON, previews, and errors use bounded containers and
`overflow-wrap: anywhere`; no page-level horizontal overflow is allowed.

### 6.2 Recent Runs

Each Run item displays:

- run type and lifecycle status;
- created/start time;
- 160-character input preview;
- provider/model when present;
- total latency/token/cost summary when present;
- complete Trace Run ID.

The list handles loading, empty, safe error with retry, and selected states.
After a successful list load, an approved valid deep-link ID is loaded even when
it is outside the recent 50. Otherwise the first recent Run is selected. A list
refresh must not replace an explicit current selection unexpectedly.

### 6.3 Run Detail And Steps

The detail header displays run type/status, provider/model, timestamps,
latency/token/cost metrics, correlations, complete ID, input/output, and safe
error text when present.

`TraceStepTimeline` renders ordered Step cards with:

- step index, type, name, status;
- latency and timestamps;
- safe error text;
- collapsed read-only input/output metadata JSON.

For a `rag_retrieve` Step, its output `retrieval_run_id` links to the matching
retrieval Run included in the same detail response. The card renders retrieval
strategy, Knowledge Base ID, query/Top-K/threshold, latency/counts/embedding
identity, and ordered candidates. Candidate rows show rank/final rank,
selection, source, available score fields, Document/Chunk IDs, bounded preview,
and metadata.

A missing or malformed `retrieval_run_id` is rendered as ordinary Step metadata
rather than crashing the page. Zero candidates render an explicit empty state.

### 6.4 Async State

The page has independent list and detail state machines. It ignores responses
after unmount and uses a monotonically increasing request token or equivalent
abort policy so a slower prior detail request cannot overwrite a newer
selection. A detail failure keeps the recent list usable and offers retry for
that Run.

## 7. Error And Security Boundaries

- `TraceRunNotFoundError` maps to stable `404 trace_run_not_found` without
  echoing the requested ID.
- Database failures continue through the existing safe database error mapping.
- API/frontend errors never include SQL text, raw response bodies, credentials,
  Provider diagnostics, or hidden Prompt/context content.
- The API exposes only already-persisted bounded audit fields. Candidate content
  remains the 500-character preview created by P4-M2-S4～S6.
- This read-only feature performs no external network operation beyond the local
  frontend-to-backend API request.

## 8. TDD And Verification

Backend RED/GREEN coverage must prove:

- list default/boundary limits, empty state, and deterministic ordering;
- detail Step/retrieval/candidate ordering and zero-candidate behavior;
- completed and failed Run serialization;
- unknown UUID 404 and malformed UUID/limit 422;
- no Provider, Tool, Embedding, or Qdrant dependency is resolved for Trace
  reads;
- existing Trace/RAG/Chat behavior remains compatible.

Frontend RED/GREEN coverage must prove:

- API success, structured error, transport failure, and invalid successful JSON;
- Trace workspace/run URL parsing and navigation;
- App/Sidebar Trace entry;
- page list loading/empty/error/success, deep-link restore, detail error/retry,
  and stale-response protection;
- ordered Steps, failed status, JSON disclosure, Retrieval summary, candidate
  order, score/source/IDs, and zero-candidate rendering.

Fresh completion gates include matching backend tests, full backend with a
system-temporary SQLite database, `pip check`, frontend typecheck/Vitest/build,
Markdown/local-link and secret/artifact/scope scans, `git diff --check`, and
Codex self-review.

Browser acceptance uses intercepted synthetic local API responses at
`1440×900` and `390×844`. It verifies recent Runs, RAG Chat selection, Step and
candidate expansion, deep-link restoration, failed Trace display, zero failed
requests, zero console warnings/errors, and zero horizontal overflow. It does
not use a real Provider, Qdrant collection, user database, `.env`, or credential.

## 9. Documentation

Update:

- `README.md` and `README_CN.md` current Plan 4 progress;
- `CHANGELOG.md` Unreleased section;
- `docs/01-architecture.md` Trace query/UI data flow;
- `docs/30-trace-observability.md` public API and Timeline scope;
- the Plan 4 execution table Batch 6 status;
- a P4-M2-S7～S9 Codex review record with exact RED/GREEN and verification
  evidence.

Do not create `docs/31-trace-timeline.md`; P4-M2-S10 owns that dedicated usage
document and the M2 final review.

## 10. Acceptance Summary

The batch is complete when:

1. Recent Trace Runs and a complete selected detail can be queried without
   runtime Provider dependencies.
2. Steps and candidates are deterministic, safe, and source-traceable.
3. The Trace workspace restores a deep link and clearly renders Chat and RAG
   Timelines across desktop and narrow layouts.
4. Loading, empty, error, success, failed-Trace, zero-candidate, and stale
   request states are tested.
5. Existing Chat/RAG APIs and persisted Trace contracts remain unchanged.
6. All fresh verification and Codex self-review gates pass with no remaining
   must-fix finding.
