# Plan 4 M1 Trace Foundation Final Review

## Decision

`P4-M1-S1～S7` is accepted. Plan 4 M1 now provides a stable, documented Trace
foundation: persistence and ownership constraints, shared enums and schemas,
strict lifecycle writes, caller-owned transactions, request-local context, and
JSON-safe token/cost/latency metadata. Fresh focused and complete backend
regression plus a temporary SQLite migration lifecycle found no remaining
Critical or Important issue and no M1 must-fix.

This decision does not claim product runtime integration. Chat, RAG, Tool, and
Agent execution still do not create Trace records; Trace query APIs, Timeline
UI, aggregation/cancellation policy, Advanced RAG, reranking, and evaluation
remain later Plan 4 work.

## Scope And Git Baseline

- S7 started on branch `main` at
  `7d183f8176ff0e2b20365ecab8de57a4cfa6e993`, with `origin/main` at the same
  commit and a clean, unstaged working tree.
- The repaired Plan 3 release baseline remains annotated `v0.3.1^{}` at
  `6bcf423434556f0862b7047b2dae1d6f26865c08`.
- The M1 implementation history and evidence are recorded in the
  [S1～S3 review](2026-08-02-plan4-m1-s1-s3-review.md) and
  [S4～S6 review](2026-08-02-plan4-m1-s4-s6-review.md).
- S7 changes only Markdown documentation and review material. No production,
  test, migration, API, frontend, or runtime file changed.
- No branch/worktree, stage, commit, push, pull, rebase, merge, or tag operation
  was performed. The user retains manual Git ownership.

## S1-S7 Acceptance Matrix

| Step | Acceptance requirement | Implementation and evidence | Decision |
|---|---|---|---|
| P4-M1-S1 | Confirm the Plan 3 bridge and release baseline | Fresh RAG/Tool/Agent compatibility checks in the S1～S3 review; `v0.3.1` remains the repaired Plan 3 baseline | Accepted |
| P4-M1-S2 | Add TraceRun/TraceStep persistence, ownership, deletion, schema, and migration contracts | ORM and schemas, Alembic `20260802_0008`, focused model/schema/migration tests, and fresh migration lifecycle | Accepted |
| P4-M1-S3 | Add stable run/step type and status contracts | Shared string enums, database checks, schema serialization, and enum tests | Accepted |
| P4-M1-S4 | Add strict Trace lifecycle writes | Flush-only `TraceService`, checked transitions, deterministic step ordering, failure cleanup, and rollback tests | Accepted |
| P4-M1-S5 | Add request-local Trace Context | ContextVar binding/restoration/isolation, automatic Step lifecycle, safe error recording, and exception re-raise tests | Accepted |
| P4-M1-S6 | Add token/cost/latency metadata helpers | Decimal cost calculation, legacy-import compatibility, JSON-safe Step metadata, and persisted round-trip tests | Accepted |
| P4-M1-S7 | Publish the current contract and close M1 | Formal Trace documentation, bilingual status/architecture synchronization, fresh full verification, and this Codex-only review | Accepted |

## Delivered Foundation

The canonical implemented contract is
[Trace Observability Foundation](../30-trace-observability.md). TraceRun keeps
the audit envelope and optional business correlations; TraceStep provides a
positive, unique, one-based order within its run. Direct operational foreign
keys use `SET NULL`, composite ownership constraints use `NO ACTION`, and
TraceRun deletion cascades its steps. Cost uses `Numeric(18, 8)` and public
schemas enforce non-negative usage and latency values.

`TraceService` creates running records from pending input, accepts Step writes
only on running runs, and permits terminal transitions only from running rows
with start times. Elapsed UTC durations are clamped to non-negative
milliseconds. Writes flush for IDs and constraints but never commit or roll
back; the calling product transaction owns atomicity.

Trace Context uses ContextVar tokens with `finally` restoration, including
nested bindings and copied-context isolation. Automatic Step failure clears
partial output, persists only the exception class name, and re-raises the
original exception. Explicit service errors must already be product-normalized.

The canonical usage helper returns a fresh JSON-safe object with token counts,
fixed eight-decimal cost strings, and latency. Existing Chat/RAG imports remain
object-identical through the compatibility facade, but those product paths are
not yet Trace writers.

## Fresh Verification Evidence

- Focused Trace/model/schema/migration/usage plus Chat/RAG compatibility group:
  `116 passed` in 12.94 seconds.
- Complete backend suite from a validated system-temporary working directory,
  with explicit temporary SQLite and document-storage paths: `1113 passed, 1
  warning` in 51.86 seconds. The warning is the existing Starlette/httpx
  TestClient deprecation.
- Dependency integrity: `No broken requirements found.`
- Temporary SQLite migration lifecycle: upgrade to `20260802_0008 (head)`,
  `current --check-heads`, `alembic check`, downgrade to `20260801_0007`,
  re-upgrade, and final head check all exited zero; the validated temporary
  directory was removed.
- Final documentation gate: 131 tracked/new Markdown files and 115 local
  links/images checked, with zero missing targets.
- Final scope/hygiene gate: exactly eight approved Markdown paths changed; zero
  non-Markdown, production/test, generated/database artifact, high-confidence
  secret/private-key, or `backend/ai_agent_lab.db` Git changes.
- Final Git gate: `git diff --check` passed; staged paths remained zero; branch
  remained `main`; HEAD and `origin/main` remained
  `7d183f8176ff0e2b20365ecab8de57a4cfa6e993`; `v0.3.1^{}` remained
  `6bcf423434556f0862b7047b2dae1d6f26865c08`.

Frontend typecheck, Vitest, build, and headed browser replay were not rerun:
S7 changes documentation only, and M1 introduced no frontend, response, route,
or user-visible runtime integration. Docker/Compose/Qdrant smoke was not rerun
because no ingestion, retrieval, vector payload, collection, or Compose path
changed.

## Findings And Disposition

### Must Fix - Fixed

- The original SQLite correlation-presence `CHECK` prevented the intended
  audit-preserving delete sequence because foreign-key actions occurred in an
  order that temporarily violated the check. Presence validation moved to the
  schema and ORM insert/update boundary, while composite ownership foreign keys
  still reject cross-Conversation records. Focused deletion and migration tests
  cover the repaired contract.
- The first TraceContext implementation evaluated a class self-reference during
  Python 3.11 import and raised `NameError`. Postponed annotation evaluation
  fixed the root cause; context and complete regression tests pass.
- S7 found stale project-facing statements that Plan 4 had not started and that
  Trace Service/Context were still future M1 work. README, Chinese README,
  architecture, execution status, and the canonical Trace document now describe
  the current boundary without claiming M2 runtime.

### Fix Later

- M2 owns Chat/RAG/Tool/Agent Trace hooks, aggregation policy, Trace list/detail
  APIs, and the frontend Timeline. Later Plan 4 milestones own Advanced RAG,
  reranking, and evaluation. None was pulled into M1.

### Recorded Limitations

- Raw maintenance SQL can bypass the ORM/schema correlation-presence invariant;
  normal product writes must use those validated boundaries.
- Concurrent writers to one TraceRun are not serialized by a new lock. The
  current local-first flow allocates the next index and relies on the unique
  database constraint as the final race guard.
- Trace writes share the caller's transaction. Caller rollback removes the
  uncommitted Trace by design; persisting a normalized failure requires the
  product integration layer to choose and commit that transaction deliberately.
- A broad read-only PowerShell discovery command during S4～S6 accidentally
  touched the prohibited `backend/ai_agent_lab.db`. It did not write, migrate,
  delete, or rebuild the file, and no usable business content was retained.
  Subsequent discovery used explicit file whitelists; final Git checks show no
  database change.

### Not Applicable

- Frontend/browser, Docker/Qdrant, real Provider/network calls, Memory, Agent
  Runtime v2, Human Approval, MCP, OCR, multimodal work, and later-Plan runtime
  are outside the S7 documentation batch and were neither changed nor invoked.

## Codex Self-Review

- Scope matches `P4-M1-S7`: only formal documentation, status synchronization,
  planning records, and the consolidated review changed.
- The documentation was reconciled against Trace ORM, schema, enum, service,
  context, usage-helper, migration, and focused-test sources.
- Transaction ownership, safe automatic errors, optional correlation semantics,
  deletion behavior, index uniqueness, and JSON cost representation are stated
  consistently.
- No current document presents M2 runtime hooks, Trace API/UI, Advanced RAG,
  reranking, evaluation, or later-Plan behavior as implemented.
- Codex self-review is the only review gate. No Claude Code, Fable, or other
  external review was requested, run, awaited, or cited.

No Critical or Important finding and no remaining must-fix was found.

## M2 Entry Gate

1. **Trace ORM/schema/migration integrity — stable.** Ownership, deletion,
   ordering, validation, head migration, downgrade, and re-upgrade are verified.
2. **Lifecycle Service and caller-owned transactions — stable.** Legal and
   illegal transitions, flush-only writes, rollback behavior, failure cleanup,
   and clock regression are covered.
3. **Request-local ContextVar and safe automatic failures — stable.** Unbound,
   bound, nested, copied, successful, and exceptional flows are verified without
   persisting arbitrary exception text.
4. **Token/cost/latency compatibility — stable.** Decimal precision, JSON-safe
   serialization, persistence round-trip, and legacy Chat/RAG imports are
   verified.
5. **Boundary clarity — stable.** Limitations are explicit and hygiene review
   found no accidental M2 or later-Plan runtime in this batch.

Plan 4 M1 may close. After the user manually commits S7, the project may enter
`P4-M2-S1～S3`.

## Git Handoff

The S7 batch remains unstaged and uncommitted in the current `main` workspace.
The user should review and create the commit manually. No release tag is part
of this milestone.

Suggested commit message:

```text
docs(observability): complete trace foundation review
```
