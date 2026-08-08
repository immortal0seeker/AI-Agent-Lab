# Plan 4 M2 S1～S3 LLM Trace Integration Design

## Objective

Implement the first Plan 4 M2 batch by connecting the existing Trace
foundation to all current Chat-oriented LLM execution paths:

- non-streaming Chat;
- streaming Chat;
- Naive RAG Chat's LLM call.

Every successful path must persist one completed `TraceRun` and one completed
`llm_call` `TraceStep` with standardized prompt-version, Provider/model,
token/cost, and latency metadata. Every attempted Provider call that raises an
`LLMProviderError` must persist a failed Run/Step without retaining partial
business records or unsafe Provider diagnostics.

## Scope

### Included

- `P4-M2-S1`: service-level LLM Trace hooks for non-streaming Chat, streaming
  Chat, and the LLM portion of RAG Chat;
- `P4-M2-S2`: strict LLM Step input/output metadata plus stable prompt-version
  identifiers;
- `P4-M2-S3`: durable, safe failed Trace records for Provider errors;
- compatibility with existing Conversation, Message, `LLMCall`, `RagQuery`,
  HTTP, and SSE behavior;
- Mock-Provider and temporary-SQLite verification;
- current-state documentation and a Codex-only batch review.

### Excluded

- Simple Agent LLM calls and Tool calls;
- RAG retrieval Runs/candidates, retrieval Steps, prompt/source/answer Steps;
- Trace API, response `trace_run_id`, and frontend Timeline;
- cancellation lifecycle persistence;
- Advanced RAG, query rewrite, hybrid search, parent-child retrieval, rerank,
  evaluation, Memory, Agent Runtime v2, Human Approval, MCP, OCR, and
  multimodal behavior;
- schema migration or changes to the `trace_runs` / `trace_steps` tables.

The RAG Chat hook in this batch records only its LLM call. `P4-M2-S4～S6`
remain responsible for retrieval candidates and RAG-specific prompt/source/
answer visibility.

## Selected Architecture

Use an explicit service-level LLM Trace coordinator rather than a Provider
decorator or API-route wrapper.

```text
ChatService.complete ───────┐
ChatService.stream_complete ├─> LLMTraceRecorder -> TraceService
RagService.chat ────────────┘
```

`LLMTraceRecorder` belongs in `backend/app/observability/`. It owns only the
LLM-specific mapping between product calls and the generic M1 Trace lifecycle:

- create a `chat` or `rag_chat` Run;
- add one `llm_call` Step;
- validate and serialize LLM Step metadata;
- apply successful usage totals to the Run;
- finish or fail the Run/Step with safe fields.

`TraceService` remains the generic lifecycle owner and continues to flush but
never commit or roll back. Provider adapters remain independent of SQLAlchemy,
Trace models, request context, and product run types. FastAPI routes remain
thin.

## Prompt Version Contract

Create stable identifiers for the two currently implemented prompt shapes:

```text
chat-history-v1
naive-rag-v1
```

`chat-history-v1` means the Provider receives the persisted Conversation
history in its current ordered ChatMessage representation. It applies to both
non-streaming and streaming Chat.

`naive-rag-v1` means the current `RagPromptBuilder` output for Naive RAG Chat.
The identifier does not claim that the full built prompt is persisted in this
batch.

Changing a prompt shape later requires a new identifier; existing Trace rows
must retain the version used when they were created.

## LLM Step Metadata Contract

Add strict Pydantic schemas under the Trace schema boundary. Unknown fields
are rejected, identifiers are stripped and length-bounded, message counts are
positive, and usage/cost/latency values are non-negative.

The Step input metadata is:

```json
{
  "provider": "openai_compatible",
  "requested_model": "example-model",
  "prompt_version": "chat-history-v1",
  "stream": false,
  "message_count": 1
}
```

The completed Step output metadata is:

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

Unknown Provider usage or pricing remains explicit JSON `null`, following the
existing `LLMCallMetrics` contract. Cost remains an eight-decimal fixed-point
string in JSON. `TraceStep.output_json` is `null` on failure.

The metadata does not contain full Conversation history, RAG context, raw
Provider requests/responses, HTTP bodies, credentials, exception text, stack
locations, or filesystem paths.

## TraceRun Contract For LLM Calls

Successful Calls populate:

- `run_type`: `chat` or `rag_chat`;
- `input_text`: the current user input/query;
- valid `conversation_id` and `user_message_id` correlations;
- requested Provider and final resolved response model;
- Run `metadata_json`: prompt version and streaming flag;
- input/output/total tokens, Decimal estimated cost, overall Run latency, and
  final output text;
- one completed `llm_call` child Step.

The current API response schemas do not add `trace_run_id`. Trace query APIs
and UI navigation remain `P4-M2-S7～S9` work.

## Transaction And Failure Design

### Successful non-streaming Chat and RAG Chat

Business records, the existing `LLMCall`, TraceRun, and TraceStep share the
request Session. The generic request dependency commits them together after
the service returns. Any database failure rolls back the whole unit.

### Successful streaming Chat

Streaming already owns its Session lifetime and explicit success commit. The
Trace records join that existing transaction and commit before the terminal
`done` event, together with Conversation, Message, and `LLMCall` records.

### Provider failure

When an attempted Provider call raises `LLMProviderError`:

1. retain only an immutable, safe Trace start snapshot in memory;
2. roll back the incomplete business transaction, including its provisional
   Trace, Conversation/Message/RagQuery, and `LLMCall` state;
3. reuse the same Session to create a standalone failed TraceRun and failed
   `llm_call` TraceStep;
4. store only the exception class name, such as `ProviderTimeoutError`;
5. explicitly commit this failed audit transaction in the product service;
6. re-raise the original Provider exception so existing HTTP/SSE error mapping
   and status codes remain unchanged.

For a failed new Chat, the rolled-back Conversation and user Message do not
exist, so the durable failed Trace has no correlation foreign keys. For an
existing Conversation or RAG Chat, the valid pre-existing Conversation may be
retained; a rolled-back user Message is never referenced.

If the failed Trace transaction itself cannot commit, the service rolls it
back, emits only a structured class/code diagnostic without prompt or Provider
message text, and re-raises the original Provider exception. Trace persistence
must not mask the product failure.

Model lookup failure, missing Provider configuration, retrieval failure, and
database failure do not create a fake `llm_call` Step when a Provider call was
not reliably attempted. Client cancellation/`GeneratorExit` retains the
current rollback-only behavior because cancellation lifecycle methods are not
part of S1～S3.

## Integration Behavior

### Non-streaming Chat

Create the Run after the Conversation and user Message exist and immediately
before the Provider segment. Complete the Step after response validation and
metrics calculation. Complete the Run only after the assistant Message,
legacy `LLMCall`, and successful-turn state are ready.

### Streaming Chat

Create the Run before consuming the Provider stream. The LLM Step spans stream
consumption through final response validation. It uses the resolved model and
final usage reported by the stream. Commit the completed Trace with the
existing successful turn before emitting `done`.

### RAG Chat

Create a `rag_chat` Run after the existing Conversation and new user Message
are available. This batch adds only one `llm_call` Step around the final
Provider call. Retrieval and prompt building remain unrepresented Steps until
S4～S6, although their wall-clock time can contribute to the enclosing Run
latency.

## Compatibility Requirements

- Existing Chat completion, SSE delta/done/error, and RAG Chat response bodies
  remain byte-shape compatible; no new required response field is added.
- Existing `LLMCall` rows remain the operational call record and keep their
  current fields/relationships.
- Successful business persistence remains atomic with successful Trace
  persistence.
- Provider failures retain existing HTTP status/error codes and SSE behavior.
- Existing logging continues to omit user content and raw Provider diagnostics.
- Direct Service construction in tests remains simple; the recorder may be
  constructed from the existing Session rather than added as a new global
  dependency.

## TDD Strategy

### Cycle 1: Prompt Versions And Metadata

Write failing tests for stable version constants, strict input/output schema
serialization, unknown-field rejection, bounded identifiers, positive message
counts, null usage/pricing, non-negative metrics, and eight-decimal cost
strings. Implement only the schemas and serialization needed for GREEN.

### Cycle 2: Non-streaming Chat

Write failing Service/API tests proving one completed Run/Step on success and
one durable failed Run/Step on Provider failure. Verify Conversation, Message,
legacy `LLMCall`, response, cost, and error-redaction compatibility. Implement
the recorder and non-streaming hook minimally.

### Cycle 3: Streaming And RAG Chat

Write failing tests for streaming success/failure and RAG Chat success/failure.
Verify resolved models, final usage, prompt versions, Run types, valid
correlations, business rollback, and safe failed audit persistence. Reuse the
same recorder rather than duplicating metadata logic.

Every production behavior must be preceded by a test that fails for the
expected missing-feature reason. Tests use Mock Providers, synthetic
credentials/content, and temporary SQLite only; no real Provider or network
Tool is called.

## Verification And Documentation

Matching verification covers the new LLM Trace tests plus existing Trace,
Chat, RAG, API-error, and LLM-usage tests. Completion also requires the full
backend suite from an explicit system-temporary SQLite/storage environment,
`pip check`, Markdown local-link validation, secret/private-key and artifact
scans, `git diff --check`, staged-path/ref checks, and Codex self-review.

Frontend typecheck/Vitest/build and browser replay are not required because no
frontend or response contract changes. Docker/Qdrant smoke is not required
because no vector-store, retrieval, payload, or Compose behavior changes.

Update current-fact documentation only:

- `docs/30-trace-observability.md`;
- `docs/01-architecture.md`;
- `README.md` and `README_CN.md` stage wording;
- `CHANGELOG.md` under Unreleased;
- the Plan 4 execution table for Batch 4/S1～S3 only;
- a Codex-only S1～S3 review record.

Do not modify the user-owned, untracked `PROJECT_LEARNING_CHECKLIST.md`.

## Acceptance Criteria

1. Non-streaming Chat, streaming Chat, and RAG Chat success each persist one
   completed Run with exactly one completed `llm_call` Step.
2. Step metadata exposes prompt version, Provider, requested/resolved model,
   streaming flag, message count, token usage, eight-decimal cost string, and
   latency without raw history/context or Provider diagnostics.
3. Run totals and output agree with the successful operational `LLMCall` and
   Provider response.
4. Mock Provider failures persist one failed Run/Step with class-name-only
   error text while provisional business rows and legacy `LLMCall` rows remain
   rolled back.
5. Existing HTTP/SSE/RAG response contracts and error codes remain unchanged.
6. No Agent, Tool, retrieval candidate, Trace API/frontend, cancellation,
   Advanced RAG, or later-Plan runtime is implemented.
7. Focused and full verification pass, Codex self-review has no remaining
   must-fix, and the batch remains unstaged for the user's manual commit.
