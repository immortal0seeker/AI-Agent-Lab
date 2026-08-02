# Plan 4 M1 S4-S6 Trace Lifecycle Design

## Status And Scope

This design covers only `P4-M1-S4-S6` from the active Plan 4 execution
table:

1. implement the Trace Service lifecycle writer;
2. implement request-local Trace Context and a step context manager;
3. establish reusable token, cost, and latency metadata helpers.

The `P4-M1-S1-S3` Trace ORM, schemas, enums, and migration are the approved
foundation for this batch. This batch does not connect Trace recording to
Chat, RAG, or Agent execution. It does not add an API, frontend Timeline,
Advanced RAG, reranking, evaluation, or any Plan 5 runtime behavior.

Trace records share the caller's SQLAlchemy `Session` and transaction.
`TraceService` may add records and call `flush()`, but it must never call
`commit()` or `rollback()`. The request/service owner remains responsible for
atomic commit, rollback, and for deliberately committing a structured failure
record when a product flow chooses to preserve it.

## Acceptance Matrix

| Step | Requirement | Deliverable | Verification |
|---|---|---|---|
| S4 | Trace Service supports run and step lifecycle writes | `observability/trace_service.py` with strict create/add/finish/fail operations | Unit tests cover success, failure, invalid transitions, deterministic step ordering, and caller-owned rollback |
| S5 | The same request can read its active `trace_run_id` | `observability/trace_context.py` with nest-safe `ContextVar` binding and a step context manager | Tests cover unbound, bound, nested restoration, exception cleanup, and context isolation |
| S6 | Mock LLM usage can be written as token/cost/latency step metadata | `observability/token_cost.py`, with the existing usage module retained as a compatibility facade | Tests cover timing, price calculation, unknown pricing, JSON-safe metadata, and TraceStep persistence |

## Alternatives Considered

### 1. Explicit Lifecycle Service And Context - Chosen

Use one `TraceService` for state transitions, a small `ContextVar`-backed
`TraceContext`, and a reusable usage metadata helper. This keeps transaction
ownership explicit, makes lifecycle behavior independently testable, and
gives M2 integration a stable API without coupling this batch to any runtime.

### 2. Independent Functions

Standalone functions would minimize class structure, but session handling,
state checks, time calculation, and error behavior would be repeated by each
caller. The resulting contract would be harder to keep consistent when Chat,
RAG, and Agent integrations arrive.

### 3. Middleware, Decorators, Or Automatic Runtime Hooks

Implicit instrumentation could reduce call-site code, but it would force
decisions about Chat/RAG/Agent boundaries before their M2 steps. It would also
blur transaction ownership. That integration is intentionally deferred.

## Chosen Design

### 1. TraceService Ownership

`TraceService` is constructed with a synchronous SQLAlchemy `Session`. It
accepts an injectable UTC clock for deterministic tests. It owns Trace
lifecycle mutations only; it does not own HTTP behavior, Provider calls,
application logging, or transaction completion.

The service exposes these operations:

- `create_run(data)`: accepts a pending `TraceRunCreate`, persists a
  `running` run, and sets `started_at`;
- `add_step(run, step_type, name, input_json=None)`: accepts only a running
  run, allocates the next positive step index, persists a running step, and
  sets `started_at`;
- `finish_run(run, ...)` and `fail_run(run, error_message, ...)`;
- `finish_step(step, ...)` and `fail_step(step, error_message, ...)`.

Creation ignores no caller state silently: `create_run` rejects a create
schema whose status is not `pending`. Terminal transitions accept only a
currently `running` record. Repeating completion/failure, mutating a terminal
record, or adding a step to a non-running run raises `TraceStateError` before
the database is changed.

Each terminal operation writes `ended_at`, calculates a non-negative elapsed
duration from the persisted UTC start and end timestamps, and clears fields
incompatible with its terminal state. This remains correct if a running record
is loaded and finished by a different service instance. Completion clears any
error. Failure clears run output or step output unless a later explicit
contract adds partial-output semantics. Error text passed to explicit failure
methods is assumed to have already crossed the product layer's safe-error
normalization boundary.

The service calls `flush()` so generated IDs and constraints are available to
the caller. It never catches an integrity error merely to roll back the
session; transaction recovery belongs to the caller. This matches the
repository service convention and preserves atomicity with business records.

### 2. Deterministic Step Ordering

`add_step` queries the maximum persisted `step_index` for the run and assigns
the next value, starting at one. The existing unique database constraint on
`(trace_run_id, step_index)` remains the final race guard.

AI Agent Lab is a local-first, single-user SQLite workspace. Concurrent
writers to the same TraceRun are not coordinated with a new lock in this
batch. If a future runtime introduces parallel step writers, it must add an
explicit ordering policy rather than weakening the unique constraint.

### 3. Trace Context

`trace_context.py` owns a `ContextVar[UUID | None]`. Its public primitives are:

- `get_trace_run_id()` returning the bound UUID or `None`;
- `bind_trace_run_id(trace_run_id)`, a synchronous context manager that
  restores the previous value in `finally` and therefore supports nesting.

`TraceContext` binds one `TraceService` and one running `TraceRun`. Its
`activate()` context manager binds the run ID for the current execution
context. Its `step(...)` context manager:

1. creates a running TraceStep through the service;
2. yields the step to the caller;
3. completes it on normal exit;
4. on exception, fails it with a safe message containing only the exception
   class name, then re-raises the original exception.

The context manager yields the `TraceStep`. A caller may assign a JSON-safe
`output_json` object to that step during the block; normal exit passes the
current value to `finish_step`. This keeps the context API small while
allowing S6 usage metadata and later M2 candidate/source metadata to be
recorded without finishing the step twice.

The automatic path deliberately does not persist arbitrary `str(exception)`
because exceptions may contain prompts, credentials, filesystem paths, or
Provider diagnostics. Callers that have a normalized public error may invoke
`fail_step` explicitly. Context cleanup always occurs, including nested and
exceptional exits. Context variables provide request/task-local propagation;
the implementation does not introduce process-global mutable state.

### 4. Token, Cost, And Latency Helpers

The existing `services/llm_usage.py` already owns the correct Plan 1/3
behavior for Provider latency measurement and Decimal price estimation. S6
moves that implementation into `observability/token_cost.py`, the location
required by the Plan 4 execution table, and keeps the old module as a narrow
compatibility facade so existing Chat/RAG imports and tests remain stable.

The helper retains these contracts:

- elapsed time uses a monotonic clock and never returns a negative value;
- token counts come from validated `TokenUsage` objects;
- cost uses model input/output prices per million tokens;
- cost is `None` when usage or either price is unavailable;
- known cost is rounded to eight decimal places with `ROUND_HALF_UP`.

`LLMCallMetrics.to_step_metadata()` returns a fresh JSON-safe dictionary for
TraceStep `output_json`. Decimal cost is serialized as a fixed-point string
to avoid float precision loss. Absent usage values remain explicit `None`
values, and `latency_ms` is always a non-negative integer. S6 proves that
metadata built from a mock `TokenUsage` can be persisted by `finish_step`.

This batch does not aggregate multiple steps into run totals automatically.
M2 callers will have the required Provider-call boundaries and can supply
explicit run metrics without coupling the Trace foundation to one aggregation
policy prematurely.

## Testing Strategy

Implementation follows RED/GREEN in three adjacent slices:

1. add failing TraceService tests, then implement run/step lifecycle writes;
2. add failing context tests, then implement binding and `TraceContext.step`;
3. add failing usage metadata and persistence tests, then extract the existing
   helper implementation into `observability/token_cost.py` with compatible
   re-exports.

Focused tests use in-memory or temporary SQLite sessions and injected clocks.
They cover strict transitions, ordering, caller-owned rollback, nested context
restoration, exception re-raising, safe automatic error text, context
isolation, token/cost/latency edge cases, and JSON persistence. No real
Provider, network Tool, secret, `.env`, or user database is accessed.

Matching regression includes existing Trace model/schema/migration tests and
existing LLM usage tests. Final verification runs the full backend suite,
`pip check`, source formatting/static checks configured by the project,
documentation/local-link checks, secret/private-key/artifact scans,
`git diff --check`, and Git scope/status/staged/ref checks.

No frontend or browser verification is required because S4-S6 expose no API
or UI behavior. That decision must be revisited in the later Trace API/UI
batch.

## Documentation And Handoff

The implementation updates the Plan 4 execution table for S4-S6, adds an
Unreleased CHANGELOG entry if the current repository convention requires one,
and records a batch review with RED/GREEN evidence and self-review findings.
It does not create `docs/30-trace-observability.md`; that remains the explicit
`P4-M1-S7` deliverable.

The final handoff reports changed files, focused/full verification, transaction
semantics, scope exclusions, remaining limitations, Codex self-review, and a
suggested manual commit message. Codex does not stage, commit, push, or create
or move a tag.

## Completion Boundary

S4-S6 are complete when Trace lifecycle writes, request-local context, the
step context manager, and mock usage metadata persistence all pass fresh
tests; the full backend regression and repository checks pass; documentation
matches the implementation; and Codex self-review finds no must-fix issue.

Completion does not mean Trace recording is active in Chat, RAG, or Agent
runtime paths. Those hooks remain in their assigned M2 batches.
