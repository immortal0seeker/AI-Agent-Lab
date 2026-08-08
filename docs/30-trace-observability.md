# Trace Observability Foundation

## Current Scope

Plan 4 M1 provides a persistent, reusable Trace foundation. It defines one
`TraceRun` audit envelope, ordered `TraceStep` children, strict schemas and
database constraints, lifecycle writes, request-local context propagation, and
JSON-safe token/cost/latency metadata.

Plan 4 M2 S1～S6 activate that foundation for Chat and Naive RAG. Chat and the
final LLM call in RAG Chat write `llm_call`; standalone RAG Query also writes
`rag_retrieve`, while RAG Chat writes ordered `rag_retrieve`, `build_prompt`,
`llm_call`, and `final_answer` Steps plus durable retrieval Run/candidate rows.
There is still no Agent/Tool Trace, Trace API, or frontend Timeline.

SQLite remains the business and audit database. Qdrant remains vector storage
only and is not involved in Trace persistence.

## Component Map

| Component | Responsibility |
|---|---|
| [`trace_types.py`](../backend/app/observability/trace_types.py) | Dependency-light run, step, and status string enums |
| [`trace.py` ORM](../backend/app/models/trace.py) | `TraceRun` / `TraceStep` persistence, constraints, relationships, and ownership validation |
| [`trace.py` schemas](../backend/app/schemas/trace.py) | Strict create/read validation and JSON-safe public field types |
| [`20260802_0008`](../backend/alembic/versions/20260802_0008_trace_foundation.py) | `trace_runs` / `trace_steps` schema migration |
| [`retrieval.py` ORM](../backend/app/models/retrieval.py) | Retrieval Run/candidate audit snapshots, constraints, ordering, and Trace ownership |
| [`retrieval.py` schemas](../backend/app/schemas/retrieval.py) | Strict retrieval/Prompt/final-answer persistence and Step metadata contracts |
| [`20260808_0009`](../backend/alembic/versions/20260808_0009_rag_retrieval_trace.py) | `rag_retrieval_runs` / `rag_retrieval_candidates` schema migration |
| [`trace_service.py`](../backend/app/observability/trace_service.py) | Run/step lifecycle mutations and deterministic step-index allocation |
| [`trace_context.py`](../backend/app/observability/trace_context.py) | Request/task-local Trace ID binding and step context management |
| [`token_cost.py`](../backend/app/observability/token_cost.py) | Provider latency timing, token/cost calculation, and Trace metadata serialization |
| [`prompt_version.py`](../backend/app/observability/prompt_version.py) | Stable `chat-history-v1` and `naive-rag-v1` prompt-shape identifiers |
| [`llm_trace.py`](../backend/app/observability/llm_trace.py) | Service-level LLM Run/Step coordination and safe Provider-failure audit transaction |
| [`retrieval_recorder.py`](../backend/app/rag/retrieval_recorder.py) | Naive RAG retrieval/Prompt/answer Step orchestration and safe retrieval/failure snapshots |
| [`llm_usage.py`](../backend/app/services/llm_usage.py) | Compatibility re-exports for existing Chat/RAG callers |

The implemented dependency direction is:

```text
Trace enums
-> ORM / schemas
-> Trace Service
-> Trace Context

LLM TokenUsage + ModelInfo
-> token/cost helper
-> JSON-safe TraceStep output metadata

Chat Service / RAG Service
-> LLM Trace Recorder
-> Trace Service

RAG Query Service / RAG Service
-> RAG Trace Recorder
-> Retrieval audit models + Trace Service
```

## TraceRun Contract

`TraceRun` is the cross-cutting audit envelope for a single observable
execution. The model supports future Chat, Agent, RAG, Tool, and Evaluation
writers without replacing existing `LLMCall`, `AgentRun`, `ToolCall`, or
`RagQuery` records.

| Field group | Fields | Contract |
|---|---|---|
| Identity | `id`, `run_type`, `status` | UUID v4 identity; checked string enum values |
| Optional correlations | `conversation_id`, `agent_run_id`, `user_message_id` | Indexed UUID links; AgentRun/Message correlations require their owning Conversation |
| Request/result | `title`, `input_text`, `output_text` | Title is at most 255 characters; input is required and non-blank; output is nullable |
| Provider identity | `provider`, `model` | Optional bounded identifiers; no secret or credential field exists |
| Usage totals | `total_input_tokens`, `total_output_tokens`, `total_tokens`, `estimated_cost`, `latency_ms` | Nullable, non-negative metrics; cost is `Numeric(18, 8)` |
| Diagnostics | `error_message`, `metadata_json` | Nullable normalized error and non-null isolated JSON object |
| Lifecycle | `started_at`, `ended_at`, `created_at` | Timezone-naive UTC values, matching the repository SQLite convention |

The LLM Trace Recorder copies the single supported LLM Step metrics into the
Run totals. The generic Trace Service still does not automatically aggregate
multiple Steps; later multi-call runtimes must choose and test an explicit
aggregation policy.

## TraceStep Contract

Each `TraceStep` belongs to exactly one `TraceRun`.

| Field group | Fields | Contract |
|---|---|---|
| Identity/order | `id`, `trace_run_id`, `step_index` | UUID v4; required parent; positive one-based index unique within one Run |
| Classification | `step_type`, `name`, `status` | Checked string enums; name is required, non-blank, and at most 255 characters |
| Data | `input_json`, `output_json` | Non-null isolated input object and nullable output object |
| Diagnostics | `error_message`, `latency_ms` | Nullable error and non-negative elapsed milliseconds |
| Lifecycle | `started_at`, `ended_at`, `created_at` | Timezone-naive UTC values |

The relationship orders Steps by `step_index`, so a future Timeline has a
deterministic sequence. `TraceService.add_step()` queries the current maximum
index and assigns the next value; the unique database constraint is the final
race guard.

## Types And Statuses

Run types:

```text
chat
agent
rag_query
rag_chat
evaluation
tool
```

Step types:

```text
build_context
llm_call
tool_call
rag_retrieve
query_rewrite
bm25_search
vector_search
hybrid_fusion
parent_child_expand
rerank
build_prompt
final_answer
eval_metric
```

Shared persisted statuses:

```text
pending
running
completed
failed
cancelled
```

The enums reserve stable vocabulary for later Plan 4 integrations. Presence in
an enum does not mean its runtime strategy exists. In M1, `TraceService`
implements creation into `running` and terminal transitions to `completed` or
`failed`; it does not implement a cancellation operation.

## Lifecycle And Transactions

The implemented lifecycle is:

```text
create_run(pending input) -> running TraceRun
running TraceRun -> add_step -> running TraceStep
running TraceStep -> finish_step -> completed TraceStep
running TraceStep -> fail_step -> failed TraceStep
running TraceRun -> finish_run -> completed TraceRun
running TraceRun -> fail_run -> failed TraceRun
```

`create_run()` rejects a create schema whose status is not `pending`.
`add_step()` rejects a non-running Run. Every finish/fail method accepts only a
running record with a start time. Repeated terminal transitions fail with
`TraceStateError` before mutation.

Terminal operations record an end time and calculate elapsed milliseconds from
the persisted UTC start/end values. Clock regression is clamped to zero.
Completion clears an existing error. Failure rejects blank error text and
clears partial output. Explicit `fail_run()` / `fail_step()` callers must pass
an error that has already crossed the product layer's safe-error normalization
boundary.

The Service adds/updates records and calls `Session.flush()` so generated IDs
and database constraints are available immediately. It never commits or rolls
back. The calling request/service owns the transaction:

- successful non-streaming Chat and RAG Chat preserve business and Trace state
  in the same request-owned transaction;
- successful streaming Chat completes both business and Trace state before the
  stream service's existing commit;
- successful standalone RAG Query and RAG Chat persist retrieval audits in the
  same caller-owned transaction as `RagQuery` and other business rows;
- a retrieval failure rolls back provisional business/Trace rows, recreates a
  failed Run and `rag_retrieve` Step, commits that class-name-only audit, and
  re-raises the original exception;
- after an attempted LLM call raises `LLMProviderError`, the Recorder snapshots
  safe identifiers/timestamps, rolls back provisional business and Trace rows,
  recreates one standalone failed Run, replays completed retrieval/Prompt rows
  for RAG Chat, appends the failed LLM Step, commits that audit, and then the
  product service re-raises the original Provider exception;
- a failed new Chat Run is uncorrelated because its provisional Conversation
  was rolled back; failures in an existing Chat/RAG Conversation retain only
  that valid Conversation correlation and never reference the rolled-back user
  Message;
- Trace audit persistence is best-effort: if it fails, only the Trace exception
  class is logged and the original Provider exception remains authoritative.

Early streaming consumer cancellation and RAG Prompt-construction failures
before an LLM attempt use the existing rollback path and deliberately leave no
durable Trace.

## Trace Context

`bind_trace_run_id()` stores a UUID in a `ContextVar` and resets the exact token
in `finally`. Nested bindings restore the outer ID, exceptional exits do not
leak it, and copied execution contexts retain independent values.

`TraceContext.activate()` binds one Run ID for a wider request block.
`TraceContext.step()` also binds that ID, adds a running Step, and owns its
terminal transition:

```python
with trace_context.activate():
    with trace_context.step(
        TraceStepType.LLM_CALL,
        name="Call model",
    ) as trace_step:
        trace_step.output_json = metrics.to_step_metadata()
```

Normal exit completes the Step with its current `output_json`. If an ordinary
application exception exits the block, the context clears partial output,
stores only the exception class name, marks the Step failed, restores the
previous ContextVar value, and re-raises the original exception. It does not
persist arbitrary exception text, prompts, filesystem paths, Provider
diagnostics, or credentials.

The context manager does not automatically finish or fail the enclosing Run.
The product flow owns the Run outcome.

## Token, Cost, And Latency Metadata

`ProviderLatencyTimer` uses `perf_counter()` and can accumulate multiple
measured sections. Negative clock deltas and the exposed millisecond value are
clamped to zero.

`build_llm_call_metrics()` copies validated `TokenUsage` counts. When usage and
both per-million model prices are available, estimated cost is:

```text
(
  input_tokens * input_price_per_1m
  + output_tokens * output_price_per_1m
) / 1_000_000
```

The result uses `Decimal`, `ROUND_HALF_UP`, and eight decimal places. Cost is
`None` when usage or either price is unavailable. Zero prices remain known
prices rather than becoming null.

`LLMCallMetrics.to_step_metadata()` returns a fresh JSON-safe object:

```json
{
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 500,
    "total_tokens": 1500,
    "estimated_cost": "0.00125000"
  },
  "latency_ms": 123
}
```

The Decimal cost is a fixed-point string to avoid float precision loss. Unknown
values remain explicit JSON nulls. The existing Chat/RAG service imports still
resolve to the exact canonical helper objects through the compatibility module.
The three M2 S1～S3 runtime paths serialize strict Step contracts:

```json
{
  "provider": "openai_compatible",
  "requested_model": "example-model",
  "prompt_version": "chat-history-v1",
  "stream": false,
  "message_count": 1
}
```

```json
{
  "provider": "openai_compatible",
  "model": "resolved-model",
  "prompt_version": "chat-history-v1",
  "usage": {
    "input_tokens": 5,
    "output_tokens": 3,
    "total_tokens": 8,
    "estimated_cost": "0.00000700"
  },
  "latency_ms": 12
}
```

The schemas are frozen, reject unknown fields, require positive message counts,
and keep costs as fixed eight-decimal strings. Step JSON excludes full Chat
history, RAG context/source bodies, raw Provider payloads, and exception text.

## Naive RAG Trace Contract

Every traced retrieval owns one `RagRetrievalRun` linked to its `TraceRun`.
It stores `naive_vector`, the original query, Knowledge Base ID, requested
Top-K/threshold, result/selection counts, elapsed milliseconds, and the exact
Embedding Provider/model identity used by the vector filter. `Retriever` returns
that identity even for zero hits through an additive `RetrievalBatch`; the
existing tuple-returning method remains compatible.

Candidates are ordered by positive one-based rank. For Naive Vector retrieval,
`rank` and `final_rank` match, `source` is `dense`, the retrieval score is stored
as `dense_score`, and every returned candidate is selected. Each row preserves
Chunk/Document snapshot IDs, a Unicode-safe preview capped at 500 characters,
filename/index/heading/page and embedding identity, plus only these nested Chunk
metadata fields when present: `source_format`, `start_char`, `end_char`, and
`heading_level`. Raw VectorStore payloads and arbitrary metadata are excluded.

The successful Step order is deterministic:

```text
RAG Query: rag_retrieve
RAG Chat:  rag_retrieve -> build_prompt -> llm_call -> final_answer
```

The retrieval Step records strategy, Knowledge Base ID, Top-K/threshold and the
retrieval Run/counts. The Prompt Step records `naive-rag-v1`, context size, and
ordered candidate/Document/Chunk references with included-character/truncation
facts; it never stores the expanded Prompt or source bodies. The final-answer
Step records RagQuery, answer Message, and LLMCall IDs plus source/character
counts; answer text remains in the Trace Run output and business Message.

RAG Chat reuses its existing Trace Run, and the LLM Recorder can complete the
`llm_call` Step without prematurely completing that Run. Standalone Query and
RAG Chat API responses remain unchanged; P4-M2-S7 will expose Trace reads.

## Persistence And Deletion

Migration `20260802_0008` creates `trace_runs` before `trace_steps` and drops
them in reverse order during downgrade.

Migration `20260808_0009` creates retrieval Runs followed by candidates and
drops them in reverse order. A Trace Run deletion cascades through retrieval
Runs and candidates. Knowledge Base, Document, and Chunk IDs are intentional
snapshots without source foreign keys, so deleting operational source records
does not erase completed retrieval evidence.

Optional operational correlations preserve the audit envelope:

- direct Conversation, AgentRun, and user Message foreign keys use
  `ON DELETE SET NULL`;
- composite `(agent_run_id, conversation_id)` and
  `(user_message_id, conversation_id)` foreign keys reject cross-Conversation
  ownership and use `NO ACTION`;
- Pydantic and ORM insert/update validation require `conversation_id` whenever
  an AgentRun or user Message correlation is present;
- deleting a `TraceRun` cascades to all of its `TraceStep` children.

SQLite applies several `SET NULL` actions sequentially when a Conversation is
deleted. An immediate database check for correlation presence would block the
approved audit-preserving deletion during an intermediate state. Therefore the
presence rule lives at the Pydantic and ORM boundaries, while the composite
foreign keys retain database cross-owner protection. Raw maintenance SQL that
bypasses both application gates must preserve the same invariant explicitly.

## Security And Reliability Boundaries

- Trace schemas reject unknown fields, blank required text/names, invalid enum
  values, negative metrics, and malformed JSON values.
- Automatic context failures persist only exception class names. Explicit
  failure methods assume already-normalized safe text.
- Provider/model fields identify execution configuration; they never store API
  keys or secret references.
- Product LLM failure records persist only the exception class name on the Run
  and Step. Raw Provider diagnostics are neither persisted nor added to log
  extras.
- Retrieval failure records use the same class-name-only rule. Candidate
  metadata is allowlisted and previews are capped at 500 characters.
- JSON payloads are intended for bounded, traceable metadata. M1 does not add
  a generic raw Provider-payload logger.
- The Service shares the business transaction and never creates a hidden audit
  Session, avoiding SQLite lock contention and orphan audit writes.
- Concurrent writers to one Run are not serialized by a new lock. The current
  local-first, primarily single-user boundary uses next-index allocation plus
  the unique constraint as the final guard.
- Run/Step cancellation behavior and multi-Step metric aggregation are not
  implemented by the generic lifecycle service. M2 explicitly leaves early
  streaming cancellation and Prompt-construction failure unpersisted.
- `search_knowledge_base` disables standalone retrieval Trace because a durable
  inner audit commit would violate the existing Agent-owned transaction. Agent
  and Tool Trace must be introduced together in a later batch.

## Verification

The executable contracts live in:

- [`test_trace_models.py`](../backend/tests/test_trace_models.py)
- [`test_trace_schemas.py`](../backend/tests/test_trace_schemas.py)
- [`test_trace_types.py`](../backend/tests/test_trace_types.py)
- [`test_trace_migration.py`](../backend/tests/test_trace_migration.py)
- [`test_trace_service.py`](../backend/tests/test_trace_service.py)
- [`test_trace_context.py`](../backend/tests/test_trace_context.py)
- [`test_llm_usage.py`](../backend/tests/test_llm_usage.py)
- [`test_llm_trace.py`](../backend/tests/test_llm_trace.py)
- [`test_chat_service.py`](../backend/tests/test_chat_service.py)
- [`test_chat_api.py`](../backend/tests/test_chat_api.py)
- [`test_rag_service.py`](../backend/tests/test_rag_service.py)
- [`test_rag_api.py`](../backend/tests/test_rag_api.py)
- [`test_retrieval_models.py`](../backend/tests/test_retrieval_models.py)
- [`test_retrieval_schemas.py`](../backend/tests/test_retrieval_schemas.py)
- [`test_retrieval_migration.py`](../backend/tests/test_retrieval_migration.py)
- [`test_rag_trace.py`](../backend/tests/test_rag_trace.py)

Detailed implementation evidence is recorded in the
[S1-S3 review](reviews/2026-08-02-plan4-m1-s1-s3-review.md) and
[S4-S6 review](reviews/2026-08-02-plan4-m1-s4-s6-review.md). The M2 S1～S3
implementation evidence is in the
[LLM Trace review](reviews/2026-08-08-plan4-m2-s1-s3-review.md); M2 S4～S6 is in
the [RAG Trace review](reviews/2026-08-08-plan4-m2-s4-s6-review.md).

## Deferred To Later Plan 4 Batches

- Tool and Agent runtime do not create `TraceRun` / `TraceStep` records.
- No Trace list/detail/step API exists.
- No frontend Trace Timeline exists.
- No automatic multi-Step Run cost aggregation or durable cancellation policy
  exists.
- Failed Prompt construction before an LLM attempt leaves no durable Trace.
- Hybrid/keyword/parent-child/query-rewrite candidates, reranking, and
  evaluation remain later Plan 4 work.

These are explicit boundaries, not partially available features. M2 S7～S10 own
query surfaces, Timeline behavior, and the M2 final review.
