# Plan 4 M1 S1～S3 Trace Foundation Review

## Decision

`P4-M1-S1～S3` establishes a verified Trace persistence foundation without
activating Trace runtime behavior. The repaired Plan 3 RAG/Tool bridge remains
compatible; shared string enums, strict schemas, `TraceRun` / `TraceStep` ORM
models, audit-preserving relationships, and Alembic revision
`20260802_0008` pass focused and complete backend regression.

Codex self-review found no remaining must-fix in this batch. Trace Service,
Trace Context, step writers, token/cost helpers, runtime hooks, APIs, frontend
Timeline, Advanced RAG, reranking, and evaluation are intentionally absent and
remain later Plan 4 Steps.

## Scope And Starting Baseline

- branch: `main`;
- starting HEAD / `origin/main` / annotated `v0.3.1^{}`:
  `6bcf423434556f0862b7047b2dae1d6f26865c08`;
- annotated `v0.3.0^{}`:
  `46ea94afe49c1db9179bbdb9a98093c86206b99f`;
- starting staged paths: zero;
- starting working paths: only the user-approved Plan 4 spec and implementation
  plan created by the required design workflow.

No branch/worktree/stage/commit/push/pull/rebase/merge/tag operation was
performed. Tests did not open `backend/ai_agent_lab.db`, a real `.env`, or real
credentials and did not call paid Providers or network Tools.

## Acceptance Matrix

| Step | Acceptance requirement | Implementation/evidence | Decision |
|---|---|---|---|
| P4-M1-S1 | Plan 3 Knowledge Base, RAG Query/Chat, Tool, and Simple Agent foundation remains usable; release tags are understood | Existing Plan 3 final audit plus fresh RAG/Tool/Agent compatibility group `92 passed, 1` known warning; exact `v0.3.0` / `v0.3.1` refs recorded | Accepted; Plan 4 builds on repaired `v0.3.1` source without moving tags |
| P4-M1-S2 | TraceRun / TraceStep ORM, schemas, migration, ownership and delete behavior | `backend/app/models/trace.py`, `backend/app/schemas/trace.py`, existing-model back-references, Alembic `0008`, model/schema/migration tests | Accepted; operational deletion preserves TraceRun, TraceRun deletion cascades steps |
| P4-M1-S3 | Stable run/step type and status enums with serialization tests | `backend/app/observability/trace_types.py`, schema/ORM checks, `backend/tests/test_trace_types.py` | Accepted; plain string values remain SQLite/PostgreSQL-portable |

## Delivered Contracts

### TraceRun

TraceRun stores run type/status, optional Conversation/AgentRun/user Message
correlations, input/output, Provider/model identity, token/cost/latency fields,
error and metadata objects, and lifecycle timestamps. Negative numeric values,
unknown types/statuses, and blank input are rejected. Metadata defaults are
isolated per row.

Direct correlation foreign keys use `SET NULL`; composite AgentRun/Message
foreign keys reject cross-Conversation ownership. Pydantic and SQLAlchemy
insert/update gates require a Conversation whenever either owned correlation
is present. Deleting an operational record preserves the Trace audit envelope.

### TraceStep

TraceStep stores one checked step type/status, a non-blank name, input/output
objects, latency/error/lifecycle data, and a positive one-based index unique
within its TraceRun. Relationship ordering is deterministic. Deleting the
TraceRun cascades its steps; no operational record owns or deletes steps
directly.

### Boundary

The models are not yet written by Chat, Agent, Tool, or RAG execution. This is
intentional: `P4-M1-S4～S6` own Trace Service/Context and token/cost helpers,
while M2 owns runtime hooks, Trace API, and frontend Timeline.

## TDD And Debugging Evidence

- Enum/schema RED: `34 failed` because the Trace contracts did not exist.
  GREEN: `34 passed` after the minimal enum and Pydantic implementation.
- ORM RED: the new test module could not import Trace models. The first GREEN
  attempt exposed one real SQLite delete failure: an immediate
  correlation-presence `CHECK` fired after Conversation `SET NULL` but before
  Message/AgentRun actions cleared their IDs.
- The deletion failure was isolated with a single test. Removing only those
  two database checks proved final `conversation_id`, `agent_run_id`, and
  `user_message_id` all become `NULL` while TraceRun/TraceStep survive. Schema
  validation plus ORM `before_insert`/`before_update` validation now enforce
  correlation presence; composite foreign keys retain cross-owner rejection.
- A Step-preservation assertion initially used an unpersisted test Step; the
  SQLAlchemy warning identified the fixture error, it was explicitly added to
  the Session, and the original deletion behavior passed.
- ORM/adjacent GREEN: `61 passed` with no warnings.
- Migration RED: `2 failed` because head `0007` had no Trace tables and
  `alembic check` reported the exact pending tables/indexes. One subsequent
  assertion was normalized to treat omitted SQLite inspector action as the SQL
  default `NO ACTION`, matching existing repository tests.
- Trace/model/migration focused GREEN: `72 passed`.

## Verification Evidence

- Plan 3 RAG Query/Chat/Tool/Simple Agent compatibility:
  `92 passed, 1 warning`;
- enum/schema: `34 passed`;
- Trace plus adjacent ORM: `61 passed`;
- Trace plus all existing migration/model contracts: `72 passed`;
- full backend from a system-temporary working directory with synthetic
  SQLite/storage paths: `1091 passed, 1 warning` in 52.24 seconds;
- dependency integrity: `No broken requirements found.`;
- temporary SQLite lifecycle: upgrade through `20260802_0008`,
  `current --check-heads`, `alembic check`, downgrade to `20260801_0007`,
  re-upgrade and final head check all passed; directory cleanup returned true;
- documentation: 124 tracked/new Markdown files and 103 local links/images,
  with zero missing targets;
- hygiene: zero high-confidence secret/private-key hits in changed text, zero
  production network-client additions, zero later-Plan paths, zero tracked
  generated/database artifacts, and no user-database change;
- Git scope: 22 expected modified/new paths, zero staged paths,
  `git diff --check` passed, and branch/HEAD/origin/tags remained at the
  starting baseline;
- the only warning is the existing Starlette/httpx TestClient deprecation.

Frontend typecheck/Vitest/build and browser screenshots were not rerun because
this batch changes no frontend, route, response, or active runtime behavior.
Qdrant was not rerun because the production vector adapter is unchanged and S1
freshly revalidated all Mock-backed RAG/Tool compatibility contracts.

## Findings And Disposition

### Important — Must Fix — Fixed

**An immediate database correlation-presence check blocked the approved audit
retention policy on SQLite.** Conversation deletion applies several foreign-key
actions sequentially. The first `SET NULL` created an intermediate state that
failed the check, preventing deletion. The final design keeps database
cross-owner protection, moves the presence rule to schema plus ORM event gates,
and proves all operational links clear while Trace history remains.

### Minor — Recorded Limitations

- Raw maintenance SQL that bypasses both Pydantic and SQLAlchemy events can
  write an AgentRun/Message correlation with a null Conversation because SQL
  composite foreign keys do not validate rows containing null components.
  Normal application writes use both gates; maintenance SQL must preserve the
  documented invariant explicitly.
- Annotated `v0.3.1` identifies the Plan 3 audit repair source commit, but that
  immutable commit still contains package/OpenAPI/frontend metadata `0.3.0`.
  The published tag is preserved rather than rewritten; Plan 4 will next make
  one coherent metadata transition at its `v0.4.0` release.

### Fix Later

- Trace Service, lifecycle transition enforcement, Trace Context, atomic step
  allocation, and token/cost helpers belong to `P4-M1-S4～S6`.
- Runtime Chat/Tool/RAG hooks, candidate recording, API, and Timeline belong to
  M2.

### Not Applicable

- Advanced retrieval, BM25/hybrid, parent-child, query rewrite, reranking, and
  evaluation are later Plan 4 milestones.
- Memory, Agent Runtime v2, Planner, Human Approval, MCP, OCR, multimodal,
  Browser/Computer Use, PostgreSQL migration, paid Provider calls, and external
  review are outside this batch.

## Codex Self-Review

- Scope: only S1～S3 models/schemas/types/migration/tests/docs were added;
  no Service, Context, API, UI, or later-Plan runtime exists.
- Integrity: ORM and migration columns/types/constraints/indexes/FKs match;
  `alembic check` reports no drift.
- Audit behavior: cross-Conversation references fail; operational deletion
  preserves TraceRun; TraceRun deletion removes TraceStep; JSON defaults are
  isolated; ordering and metrics are bounded.
- Compatibility: full backend and focused Plan 3 bridge groups pass.
- Security: no credentials, real Provider calls, network Tools, user database,
  or generated artifacts are part of the implementation.
- Git: user-owned main/tags remain untouched; the batch remains unstaged for
  manual review and commit.

## Next Batch

The workspace can proceed to `P4-M1-S4～S6` after the user manually commits
this batch. The next batch should implement Trace Service, Trace Context, and
token/cost/latency helper structures without yet wiring the full M2 Timeline.

Suggested commit message:

```text
feat(observability): add trace run and step foundation
```
