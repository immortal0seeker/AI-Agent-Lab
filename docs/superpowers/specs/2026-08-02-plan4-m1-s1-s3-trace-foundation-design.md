# Plan 4 M1 S1～S3 Trace Foundation Design

## Status And Scope

This design covers only `P4-M1-S1～S3` from the current Plan 4 execution
table:

1. recheck and record the Plan 3 handoff baseline;
2. add `TraceRun` / `TraceStep` persistence models and API-facing schemas;
3. define stable Trace run types, step types, and lifecycle statuses.

The execution table is authoritative for this batch. Although the older
all-in-one Plan 4 document groups Trace Service and Trace Context into its
generic “Step 3”, the current execution table assigns those behaviors to
`P4-M1-S4～S6`. This batch therefore does not implement Trace Service, Trace
Context, runtime hooks, Trace APIs, frontend Timeline, token-cost helpers,
Advanced RAG, reranking, or evaluation.

The repository remains on the user's `main` workspace. Codex will not create
or switch branches, stage, commit, push, pull, rewrite tags, or read the real
`.env`, credentials, or `backend/ai_agent_lab.db`.

## Acceptance Matrix

| Step | Requirement | Current evidence | Batch deliverable | Verification |
|---|---|---|---|---|
| S1 | Plan 3 Knowledge Base, ingestion, Naive RAG, and `search_knowledge_base` remain a stable base | `v0.3.0` points to the original release commit; `v0.3.1` and `main` point to the post-audit repair commit; the formal Plan 3 audit records full regression and five stable Plan 4 bridges | A fresh, concise handoff record that distinguishes the original release tag from the repair tag without moving either tag | Git refs/status plus focused RAG Query, RAG Chat, Tool, and Agent compatibility tests |
| S2 | `trace_runs` and `trace_steps` ORM/schema/migration are usable and preserve audit integrity | Existing `LLMCall`, `AgentRun`, `ToolCall`, and `RagQuery` models provide local patterns but no unified Trace tables exist | ORM relationships, strict schemas, Alembic `20260802_0008`, model/migration tests | RED/GREEN tests, temporary SQLite upgrade/downgrade/re-upgrade, Alembic model check |
| S3 | Trace run/step types and statuses serialize predictably and reject invalid persisted values | Plan 4 lists run/step types, but there is no central typed contract | `observability/trace_types.py` with string enums used by schema and database constraints | Enum value/JSON-schema serialization tests plus database constraint tests |

## Alternatives Considered

### 1. String Enums Plus Database Check Constraints — Chosen

Use Python `StrEnum` contracts, store their values in ordinary `VARCHAR`
columns, and mirror the allowed values with named database `CHECK`
constraints. Pydantic serializes the values as normal JSON strings, SQLite
can enforce the contract, and a future PostgreSQL-compatible migration does
not depend on vendor enum behavior. Adding a new state remains an explicit
model/schema/migration/test change, as required by the repository state-machine
rules.

### 2. SQLAlchemy Native Enum Columns

Native enums provide stronger database typing on databases that support them,
but SQLite emulates the behavior and future enum changes become
dialect-sensitive. This adds migration complexity without improving the local
workspace contract.

### 3. Python-Only Validation

Python/Pydantic-only validation would be flexible, but direct ORM or migration
writes could persist invalid audit states. A Trace foundation should fail
closed at the database boundary, so this option is rejected.

## Chosen Design

### 1. Trace Type Contracts

`backend/app/observability/trace_types.py` owns three string enums:

- `TraceRunType`: `chat`, `agent`, `rag_query`, `rag_chat`, `evaluation`,
  `tool`;
- `TraceStatus`: `pending`, `running`, `completed`, `failed`, `cancelled`;
- `TraceStepType`: `build_context`, `llm_call`, `tool_call`, `rag_retrieve`,
  `query_rewrite`, `bm25_search`, `vector_search`, `hybrid_fusion`,
  `parent_child_expand`, `rerank`, `build_prompt`, `final_answer`,
  `eval_metric`.

The status set is deliberately shared by runs and steps. “Pending” represents
a record created before work starts; “cancelled” is terminal but distinct from
failure. A conditional strategy does not create a fake “skipped” step in this
batch. If a later runtime genuinely needs another state, it must update the
enum, both database constraints, schemas, tests, and documentation together.

Enums are dependency-free and do not import ORM or service modules. This keeps
them safe for models, schemas, future services, and Plan 5 runtime consumers.

### 2. TraceRun Persistence

`backend/app/models/trace.py` defines `TraceRun` with the Plan 4 fields:

- identity and classification: UUID `id`, `run_type`, `status`;
- optional correlations: `conversation_id`, `agent_run_id`,
  `user_message_id`;
- request/result context: nullable `title`, required `input_text`, nullable
  `output_text`;
- provider identity: nullable `provider` and `model`;
- usage: nullable non-negative `total_input_tokens`, `total_output_tokens`,
  `total_tokens`, `estimated_cost`, and `latency_ms`;
- diagnostics: nullable `error_message`, non-null object `metadata_json` with
  an isolated empty-dict default;
- lifecycle: nullable `started_at` / `ended_at` and non-null `created_at` using
  the repository's naive-UTC convention.

Run type and status use `String(32)` columns with named `CHECK` constraints.
Provider/model lengths follow existing Provider contracts. Cost uses
`Numeric(18, 8)`. Token/cost/latency values may be absent while a run is in
progress, but persisted negative values are rejected. This batch does not add
lifecycle transition constraints: the subsequent Trace Service owns
transitions and atomic completion/failure writes.

Correlation IDs are optional because Tool, Evaluation, or standalone RAG
executions may not have every upstream record. Each direct foreign key uses
`ON DELETE SET NULL`, so deleting an operational record preserves the Trace.
Composite ownership foreign keys ensure that a referenced Message or AgentRun
cannot belong to a different Conversation. Pydantic and ORM insert/update
validation require `conversation_id` whenever `user_message_id` or
`agent_run_id` is populated.

This split is deliberate on SQLite: an equivalent database `CHECK` fires after
the Conversation foreign key is cleared but before the Message/AgentRun delete
actions clear their correlations, preventing the approved audit-preserving
delete. Raw maintenance SQL must therefore honor the correlation-presence
invariant; normal application writes pass through both schema and ORM gates.

This follows the approved audit-first deletion policy:

- delete Conversation, AgentRun, or Message: clear the relevant TraceRun link
  and retain the TraceRun;
- delete TraceRun: cascade to all of its TraceSteps;
- never cascade from an operational record into Trace audit history.

Relationships are added to `Conversation`, `Message`, and `AgentRun` with
`passive_deletes=True`; they do not use delete-orphan cascades. No relationship
is added to `RagQuery` in this batch because the Plan 4 model does not yet
define a `rag_query_id` correlation field; RAG runtime integration belongs to
M2.

### 3. TraceStep Persistence

The same model module defines `TraceStep` with:

- UUID `id` and required `trace_run_id`;
- positive, one-based `step_index`, unique within one TraceRun;
- checked `step_type` and `status` string values;
- required bounded `name`;
- non-null object `input_json` with an isolated empty-dict default and nullable
  object `output_json`;
- nullable `error_message`, non-negative nullable `latency_ms`, lifecycle
  timestamps, and `created_at`.

Deleting a TraceRun cascades its steps at the database boundary. The unique
`(trace_run_id, step_index)` constraint gives each Timeline a deterministic
order and rejects races or writer mistakes instead of silently overwriting a
position. This batch only establishes the contract; automatic index allocation
is a Trace Service responsibility in `S4～S6`.

### 4. Pydantic Schemas

`backend/app/schemas/trace.py` provides create/read contracts for runs and
steps. Schemas use `extra="forbid"`, `from_attributes=True` for read models,
strict positive/non-negative integer validation, finite non-negative cost,
bounded identifiers, and `dict[str, JsonValue]` for JSON objects. Blank
`input_text` and blank step names are rejected.

Enum fields use the shared `StrEnum` types, so both validation and generated
JSON Schema expose the exact string values. Read models return database column
names (`metadata_json`, `input_json`, `output_json`) in this internal
foundation; public API aliases are deferred until the Trace API contract is
designed in M2. A nested run-detail/API response schema is also deferred to
avoid fixing query/loading behavior before the Trace API exists.

The model and schema packages re-export the new public contracts. No route or
service imports the schemas in this batch.

### 5. Migration

Alembic revision `20260802_0008` follows `20260801_0007`. It creates
`trace_runs` before `trace_steps`, including named primary, foreign-key,
unique, check, and correlation indexes consistent with the repository naming
convention. Downgrade removes `trace_steps` first and then `trace_runs`.

The migration contains no data backfill because both tables are new. It does
not read or migrate the user's database during tests; lifecycle verification
uses a system-temporary SQLite file and checks upgrade, current head,
autogenerate drift, downgrade to `0007`, and re-upgrade to `0008`.

## Testing Strategy

Implementation follows RED/GREEN in three adjacent slices:

1. **Types and schemas:** add failing enum/schema serialization and rejection
   tests, then implement the dependency-free type module and schemas.
2. **ORM behavior:** add failing model tests for defaults, relationships,
   ordering, audit preservation, cascade, ownership, invalid enum values, and
   negative metrics, then implement the models and back-references.
3. **Migration:** add failing inspector/lifecycle tests for tables, columns,
   constraints, indexes, foreign-key actions, downgrade, and Alembic head,
   then add revision `0008`.

Focused verification includes the new Trace tests plus existing model and
migration suites. S1 re-runs the Plan 3 RAG Query, RAG Chat,
`search_knowledge_base`, and Simple Agent compatibility suites using mocks and
temporary data only. Final batch verification runs the full backend suite,
`pip check`, temporary SQLite migration lifecycle, documentation/local-link
checks, secret/private-key/generated-artifact scans, `git diff --check`, and
Git scope/status/ref checks.

No frontend build or browser run is required because S1～S3 have no frontend or
user-visible runtime path. That decision must be revisited when Trace API/UI
work starts in M2.

## Documentation And Handoff

The implementation records S1 evidence in a formal Plan 4 batch review,
updates the Plan 4 execution table only for S1～S3, adds the new tables to the
architecture documentation, and adds an Unreleased CHANGELOG entry. It does
not create `docs/30-trace-observability.md` early because that is the explicit
`P4-M1-S7` deliverable.

The handoff record must state the exact release history without rewriting it:

- annotated `v0.3.0` remains on the original Plan 3 release commit;
- annotated `v0.3.1` and the starting `main` point to the post-audit repair
  commit;
- Plan 4 begins from the repaired source tree;
- no tag is moved or recreated by Codex.

## Completion Boundary

This batch is complete when S1 has fresh compatibility evidence, S2 models,
schemas, and migration pass focused and lifecycle tests, S3 enum contracts
serialize and reject invalid data, the complete backend regression passes,
documentation matches the implementation, and Codex self-review finds no
must-fix.

Completion does not imply Trace recording is active. Runtime creation,
finishing/failure transitions, context propagation, token/cost helpers, and
all integration hooks remain the next `P4-M1-S4～S6` batch.
