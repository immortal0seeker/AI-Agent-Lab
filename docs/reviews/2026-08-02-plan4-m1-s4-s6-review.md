# Plan 4 M1 S4-S6 Trace Lifecycle Review

## Decision

`P4-M1-S4-S6` is complete with no remaining must-fix. The batch adds a
caller-transaction-owned Trace lifecycle writer, request-local nested Trace
context with safe step management, and canonical token/cost/latency metadata
while preserving the existing Chat/RAG LLM usage imports.

Trace recording is not yet active in Chat, RAG, Tool, or Agent execution.
That runtime integration remains deliberately assigned to Plan 4 M2. No API,
frontend, Advanced RAG, reranking, evaluation, or Plan 5 runtime was added.

## Scope And Starting Baseline

- branch: `main`;
- starting HEAD and `origin/main`:
  `06285ca2106daa3a98edbe35dce102d97cd362d8`;
- annotated `v0.3.1^{}`:
  `6bcf423434556f0862b7047b2dae1d6f26865c08`;
- starting working tree and staged set: clean and zero paths;
- no branch/worktree/stage/commit/push/pull/rebase/merge/tag operation was
  performed.

An early PowerShell discovery command used an incorrect `-Include` shape and
expanded beyond the intended AGENTS/Plan whitelist. It caused `Get-Content` to
touch `backend/ai_agent_lab.db`. The command did not write, migrate, delete, or
rebuild the database and its output contained no usable retained business
content. Work stopped immediately, the incident was disclosed in the active
task, and every subsequent read used explicit file whitelists. Final Git
checks show no database change. This is a process-boundary incident, not an
accepted testing technique.

No real `.env`, credential store, paid Provider, or network Tool was accessed.
All database tests used system-temporary SQLite files.

## Acceptance Matrix

| Step | Acceptance requirement | Implementation and evidence | Decision |
|---|---|---|---|
| P4-M1-S4 | Trace Service can create runs, add ordered steps, complete and fail runs/steps | `backend/app/observability/trace_service.py`; strict per-record state transitions, UTC timestamps/non-negative latency, safe explicit errors, automatic step indexes, flush-only persistence; 12 service tests | Accepted |
| P4-M1-S5 | One request/execution context can read its `trace_run_id` | `backend/app/observability/trace_context.py`; nest-safe ContextVar binding, copied-context isolation, activation and success/failure step managers; 6 context tests | Accepted |
| P4-M1-S6 | Mock LLM usage can produce token/cost/latency step metadata | `backend/app/observability/token_cost.py`; Decimal cost and monotonic Provider timer moved from the existing service, JSON-safe metadata added, old module retained as an object-identical facade; 11 usage tests including persisted TraceStep metadata | Accepted |

## Delivered Contracts

### Trace Service

`TraceService` accepts the caller's synchronous SQLAlchemy Session and an
injectable UTC clock. `create_run` accepts only a pending create contract and
persists a running record. `add_step` accepts only a running run, allocates the
next one-based index, validates through the existing strict step schema, and
persists a running step.

Run/step completion and failure accept only running records with start times.
They write terminal status, end time, and clamped non-negative latency.
Completion clears errors; failure rejects blank safe errors and clears partial
output. Repeated or invalid transitions fail before mutation. Every write
flushes for IDs/constraints but never commits or rolls back, so the product
transaction owner controls atomicity. A rollback test proves an uncommitted
Trace disappears with its caller transaction.

### Trace Context

`bind_trace_run_id` uses ContextVar tokens and `finally` restoration, so nested
bindings restore their outer value and copied execution contexts remain
isolated. `TraceContext.activate` binds one run for a wider request block.
`TraceContext.step` binds the same ID, creates a running step, completes it on
normal exit, or fails it and re-raises the original application exception.

Automatic failure persists only the exception class name. It does not persist
arbitrary exception text, prompts, Provider diagnostics, paths, or synthetic
secrets. Explicit callers may pass a product-normalized public error directly
to the service.

### Token, Cost, And Latency Metadata

The previously verified `ProviderLatencyTimer`, eight-decimal Decimal cost
calculation, and `LLMCallMetrics` now live in the Plan-required observability
module. `services/llm_usage.py` explicitly re-exports the exact same objects,
so Chat/RAG imports and behavior remain stable.

`to_step_metadata()` returns a fresh JSON-safe object containing token usage,
fixed-point string cost, and non-negative latency. Unknown usage/pricing stays
explicitly null. A Mock TokenUsage record was written to a completed
TraceStep, committed to temporary SQLite, reloaded, and compared exactly.

## RED/GREEN And Debugging Evidence

- Task 1 RED: `test_trace_service.py` failed collection because
  `app.observability.trace_service` did not exist. GREEN: `12 passed`; Trace
  service plus existing model/schema contracts: `69 passed`.
- Task 2 RED: `test_trace_context.py` failed collection because
  `app.observability.trace_context` did not exist. The first implementation
  run exposed a Python 3.11 forward-reference `NameError`; comparison with the
  existing Trace model identified the missing postponed-annotation import.
  The one-line root-cause fix produced `6 passed`; combined service/context:
  `18 passed`.
- A suspected SQLAlchemy failed-transaction exception-masking case was tested
  against real temporary SQLite. The original IntegrityError remained the
  propagated exception, disproving the hypothesis. The speculative assertion
  was removed and no production behavior was changed for a non-reproduced
  problem.
- Task 3 RED: `test_llm_usage.py` failed collection because
  `app.observability.token_cost` did not exist. GREEN: `11 passed`; S4-S6 plus
  Chat/RAG compatibility: `55 passed`.

## Matching And Full Verification

- Trace service/context/model/schema/type/migration, LLM usage, Chat service,
  and RAG service matching group: `116 passed`;
- complete backend suite from a system-temporary working directory with an
  explicit temporary SQLite URL/storage root: `1113 passed, 1 warning` in
  50.53 seconds on the final completion run;
- warning: the already-known Starlette/httpx TestClient deprecation only;
- dependency integrity: `No broken requirements found.`;
- Markdown/local links: 126 Markdown files, 103 local links/images, zero
  missing targets;
- hygiene: zero high-confidence secret/private-key hits in changed text, zero
  production network-client imports, zero arbitrary exception-text persistence
  hits, zero changed M2/Plan 5 runtime paths, and no user-database Git change;
- `git diff --check`: passed;
- Git refs remained on the starting baseline and staged paths remained zero.

Migration lifecycle was not rerun because this batch changes no ORM model,
metadata registration, or Alembic revision; the matching migration suite is
included in the 116-test group. Frontend typecheck/Vitest/build and browser
replay were not rerun because no route, response, frontend, or user-visible
runtime changed. Docker/Qdrant was not rerun because no ingestion, retrieval,
payload, vector-store, or Compose path changed.

## Codex Self-Review

- Scope: only Trace lifecycle/context/usage helpers, focused tests, and current
  batch documentation changed; no M2 hook or later-Plan runtime exists.
- Transactions: Trace production modules contain no `commit()` or
  `rollback()` call; caller rollback behavior is directly tested.
- State: creation, ordering, completion, failure, repeated transitions,
  missing start time, terminal-run step rejection, blank errors, and clock
  regression are covered.
- Context safety: unbound/bound/nested/copied/exceptional contexts are covered;
  automatic errors store only exception class names and clear partial output.
- Compatibility: legacy and canonical LLM usage imports are object-identical;
  Chat/RAG focused and full backend regression pass.
- Security/hygiene: no secret, real Provider/network call, user database
  mutation, generated artifact, staged path, or unrelated feature is present.

Codex self-review found no Critical or Important code issue and no remaining
must-fix.

## Finding Classification

### Must Fix - Fixed

- The initial TraceContext implementation evaluated a class self-reference at
  import time and raised `NameError`. Adding postponed annotations fixed the
  root cause; all context and full regression tests pass.

### Recorded Process Incident - Remediated

- The overly broad read-only PowerShell discovery touched the prohibited user
  SQLite file. No write or retained business content resulted. The discovery
  method was replaced with explicit whitelists, and final Git checks prove no
  database change.

### Recorded Limitations

- Parallel writers to the same TraceRun are not serialized by a new lock. The
  current local-first single-user path allocates the next index and relies on
  the existing unique database constraint as the final race guard.
- Trace records share the business transaction. A caller rollback removes the
  Trace as designed; preserving a structured failure requires the product
  layer to catch its normalized failure and deliberately commit that request
  transaction.
- Runtime Trace creation, run aggregation, cancellation policy, API/query
  surfaces, and UI remain later Plan 4 work.

### Not Applicable

- Schema migration lifecycle beyond the matching test, frontend/browser,
  Docker/Qdrant, real Provider/network, Advanced RAG, reranking, evaluation,
  Memory, Agent Runtime v2, Human Approval, MCP, OCR, and multimodal work are
  outside S4-S6.

## Git Handoff And Next Step

The batch remains unstaged and uncommitted for user review. After the user
manually commits it, the workspace can proceed to `P4-M1-S7`, which owns the
formal Trace foundation document and M1 completion review. M2 runtime hooks
must not start before that batch is complete.

Suggested commit message:

```text
feat(observability): add trace lifecycle and context
```
