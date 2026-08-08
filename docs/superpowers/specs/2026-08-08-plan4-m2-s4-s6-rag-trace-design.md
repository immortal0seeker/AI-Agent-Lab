# Plan 4 M2 S4-S6 RAG Trace Integration Design

## Objective

Implement only `P4-M2-S4-S6` by extending the existing Trace foundation and
LLM Trace integration with durable Naive RAG retrieval audits, ordered RAG
steps, prompt/source metadata, and answer linkage.

The batch covers standalone RAG Query and RAG Chat. It preserves the current
RAG response contracts and keeps `Retriever`, embedding Providers, and vector
stores independent of SQLAlchemy and Trace concerns.

## Scope

### Included

- `P4-M2-S4`: `rag_retrieval_runs` and
  `rag_retrieval_candidates` models, migration, schemas, and tests;
- `P4-M2-S5`: Naive Retriever success/failure Trace integration and durable
  candidate score/order snapshots;
- `P4-M2-S6`: RAG prompt/source and final-answer Trace steps;
- exactly one TraceRun for each successfully started standalone RAG Query or
  RAG Chat execution;
- durable, class-name-only failed retrieval Trace records;
- preservation of successful retrieval/prompt audit evidence when a later
  RAG Chat LLM Provider call fails;
- Mock Provider, temporary-SQLite, migration, backend/frontend regression,
  documentation, and Codex-only review evidence.

### Excluded

- `P4-M2-S7` Trace query APIs;
- `P4-M2-S8` frontend API/types;
- `P4-M2-S9` Trace Timeline UI;
- exposing `trace_run_id` through existing RAG responses;
- Simple Agent or Tool Trace integration;
- query rewrite, BM25, hybrid retrieval, parent-child retrieval, reranking,
  evaluation, Memory, Agent Runtime v2, Human Approval, MCP, OCR, or
  multimodal behavior;
- a general workflow checkpoint/recovery engine.

## Selected Architecture

Use a dedicated service-level `RAGTraceRecorder`, orchestrated by
`RagQueryService` and `RagService`.

```text
RagQueryService.query -----> RAGTraceRecorder -----> TraceService
          |                         |
          +-----> Retriever         +-----> retrieval audit models

RagService.chat ----------> RAGTraceRecorder -----> LLMTraceRecorder
          |                         |
          +-----> Retriever         +-----> TraceService
          +-----> Prompt Builder
          +-----> LLM Provider
```

`Retriever` remains a pure composition boundary around an Embedding Provider
and Vector Store. It does not receive a Session, TraceRun, recorder, or
request-local context. Routes remain thin. Services retain transaction
ownership. `TraceService` remains flush-only and never commits or rolls back.

The alternatives rejected are direct Trace writes spread through RAG service
methods, which would mix persistence mapping with product logic, and an
event/Hook architecture, which would introduce transaction propagation and
runtime infrastructure beyond the current batch.

### Retriever outcome identity

Candidate rows expose embedding identity when at least one vector matches,
but a zero-hit search has no candidate from which to recover the model used by
the query embedding and vector filter. Add a small immutable Retriever batch
result containing the ordered result tuple plus the resolved embedding
Provider and model identifiers. RAG services use the batch method; the
existing `retrieve()` method remains a compatibility wrapper returning only
the tuple, so `search_knowledge_base` and existing callers do not change.

This is a Retriever output-contract addition only. It does not add Trace,
Session, persistence, or observability dependencies to the Retriever.

## Retrieval Audit Data Model

Migration `20260808_0009` adds two tables.

### `rag_retrieval_runs`

- `id`: UUID primary key;
- `trace_run_id`: required UUID foreign key to `trace_runs.id`, indexed,
  `ON DELETE CASCADE`;
- `knowledge_base_id`: required UUID audit snapshot without a source-table
  foreign key;
- `strategy_name`: required bounded identifier; current value is
  `naive_vector`;
- `original_query`: required non-blank text;
- `rewritten_query`: nullable text and always `NULL` in this batch;
- `top_k`: integer from 1 through 100;
- `candidate_count`: integer from 0 through 100;
- `selected_count`: integer from 0 through 100 and not greater than
  `candidate_count`;
- `score_threshold`: nullable finite float;
- `latency_ms`: required non-negative integer;
- `metadata_filter_json`: required JSON object;
- `strategy_config_json`: required JSON object;
- `created_at`: required UTC-naive timestamp following the repository model
  convention.

Multiple retrieval runs per TraceRun are allowed so later Advanced RAG may
record additional retrieval phases without changing this ownership model.
For the current strategy, `metadata_filter_json` records the exact Knowledge
Base, embedding Provider, and resolved embedding model filters passed to the
Vector Store, including for zero-hit searches. `strategy_config_json` records
only stable Naive retrieval configuration that is not already a first-class
column; it remains an empty object when no additional configuration exists.

### `rag_retrieval_candidates`

- `id`: UUID primary key;
- `retrieval_run_id`: required UUID foreign key to
  `rag_retrieval_runs.id`, indexed, `ON DELETE CASCADE`;
- `chunk_id` and `document_id`: required UUID audit snapshots without source
  table foreign keys;
- `rank`: required positive integer, unique within a retrieval run;
- `final_rank`: nullable positive integer, unique when present within a
  retrieval run;
- `source`: required strategy-source value from `dense`, `sparse`, `hybrid`,
  `parent`, or `rerank`; current value is `dense`;
- `dense_score`, `sparse_score`, `fused_score`, and `rerank_score`: nullable
  finite floats;
- `selected`: required boolean;
- `content_preview`: required non-blank text bounded to 500 characters by the
  strict creation schema;
- `metadata_json`: required JSON object;
- `created_at`: required UTC-naive timestamp.

For Naive Top-K retrieval, each returned item is selected by the retrieval
strategy: `rank == final_rank`, `source == "dense"`, `dense_score` equals the
retrieval result score, the other score fields are `NULL`, and `selected` is
true. Prompt inclusion is a separate decision and is recorded by the
`build_prompt` step.

The candidate metadata snapshot contains filename, chunk index, heading, page
number, embedding Provider/model identity, and only the current ingestion
pipeline's allowlisted chunk keys: `source_format`, `start_char`, `end_char`,
and `heading_level`. JSON-safe validation alone is not a security allowlist;
unknown vector-payload metadata keys are dropped from Trace storage. The
snapshot never adds file paths, vectors, credentials, full Provider payloads,
or full document content.

## Audit Retention And Deletion

Retrieval rows are children of the Trace audit, not of mutable source data.
Deleting a TraceRun deletes its retrieval runs and candidates. Deleting a
Document, DocumentChunk, or eventually an empty Knowledge Base does not delete
or block deletion because the source UUIDs are immutable snapshots rather
than foreign keys.

This intentionally allows audit references to point to source identifiers
that no longer exist. Candidate previews and bounded metadata retain enough
historical evidence for a Trace Timeline while avoiding full-content
duplication. Existing `RagQuery` ownership and deletion behavior is unchanged.

## Trace Step Contracts

Strict Pydantic metadata schemas reject unknown fields, coerced booleans or
numbers, blank identifiers, out-of-range counts, non-finite scores, invalid
UUIDs, and unsafe JSON values.

### `rag_retrieve`

Input metadata contains:

- knowledge base ID;
- strategy name `naive_vector`;
- `top_k`;
- optional score threshold.

Successful output metadata contains:

- retrieval run ID;
- candidate count;
- selected count.

Candidate details and ordering live in the normalized retrieval tables rather
than being duplicated into the Step JSON.

### `build_prompt`

Input metadata contains:

- prompt version `naive-rag-v1`;
- retrieval run ID;
- candidate count.

Successful output metadata contains:

- prompt version;
- context character count;
- used-source count;
- an ordered source list containing source index, candidate ID, document ID,
  chunk ID, included character count, and a truncation flag.

The Step stores neither the assembled prompt, Conversation history, full
retrieved chunks, nor the final context string.

### `final_answer`

Input metadata contains the prompt version, retrieval run ID, and used-source
count. Successful output metadata contains RagQuery ID, answer Message ID,
LLMCall ID, source count, and answer character count. The answer text is not
duplicated in Step JSON; the existing TraceRun `output_text` remains its
single Trace-level location.

## Execution Flow

### Standalone RAG Query

The service validates that the Knowledge Base exists before starting an
execution Trace. It then creates one `rag_query` TraceRun and one running
`rag_retrieve` Step, invokes the pure Retriever batch method, records a
RetrievalRun and ordered candidates, creates the existing RagQuery snapshot,
finishes the Step, and finishes the Run. The request dependency commits all
successful records atomically.

The successful order is:

```text
rag_retrieve -> TraceRun completed
```

No second TraceRun is created by shared internal retrieval logic.

The HTTP RAG Query dependency enables this standalone Trace policy. The
`search_knowledge_base` Tool also reuses the retrieval/query business logic,
but runs inside an Agent-owned transaction. Its dependency explicitly disables
standalone RAG Trace creation for this batch: otherwise a retrieval failure
would roll back or independently commit inside an in-progress Agent run and
would prematurely implement Agent/Tool Trace integration. The Tool retains its
existing RagQuery audit and read-only behavior. Agent-owned retrieval Trace
wiring remains assigned to the later Agent Trace batch.

### RAG Chat

Existing model, Provider, Knowledge Base, and Conversation validation happens
before Trace execution begins. After the user Message is provisionally
created, the service creates one `rag_chat` TraceRun and uses it through the
whole flow.

The successful order is:

```text
rag_retrieve -> build_prompt -> llm_call -> final_answer
```

The retrieval stage creates the legacy RagQuery plus normalized retrieval
audit rows. The prompt stage records only source-selection metadata. The
existing `LLMTraceRecorder.complete_call` gains an explicit option to finish
the LLM Step and apply Run metrics without completing the Run; existing Chat
callers retain the current default behavior. The final-answer stage records
business correlation IDs and then completes the Run with the answer text.

Successful business rows, legacy LLMCall/RagQuery rows, Trace rows, and
retrieval audit rows share one caller-owned transaction.

## Failure And Transaction Semantics

### Pre-execution validation

Missing Knowledge Base, model, Provider, or Conversation failures happen
before the corresponding execution starts and do not create a Trace.

### Retrieval failure

An exception raised by the Retriever boundary, including Embedding or Vector
Store failures, uses this sequence:

1. preserve only an immutable, safe run/step input and timing snapshot;
2. roll back provisional business, Trace, retrieval, and candidate state;
3. recreate a standalone failed `rag_query` or `rag_chat` TraceRun;
4. recreate one failed `rag_retrieve` Step using the original start times;
5. persist only the exception class name;
6. explicitly commit the failed audit and re-raise the original exception.

A failed RAG Chat may retain correlation to a pre-existing Conversation, but
never to the rolled-back user Message. No RetrievalRun or candidate rows are
created for a retrieval that failed.

### LLM Provider failure after successful retrieval

The existing safe Provider-failure behavior remains, but the RAG-specific
recorder reconstructs the completed retrieval and prompt audit before adding
the failed `llm_call` Step. The normalized RetrievalRun and candidate
snapshots are retained because retrieval actually succeeded. Provisional user
Message, RagQuery, assistant Message, and legacy LLMCall rows remain rolled
back. Only the Provider exception class name is stored; the raw message,
request, response, prompt, context, and credentials are excluded.

### Other failures

Cancellation, database faults, and Trace persistence faults use safe rollback
and do not fabricate an audit that may be incomplete or inaccurate. Trace
persistence is best effort and must not mask the original product failure.
A local prompt-construction exception currently follows ordinary atomic
rollback instead of rebuilding a durable failed Trace. General checkpoint and
recovery semantics are recorded as outside this batch.

## Compatibility Requirements

- Existing RAG Query and RAG Chat HTTP response shapes remain unchanged.
- Existing RagQuery snapshots continue to be written for compatibility.
- `trace_run_id` remains internal until `P4-M2-S7-S9`.
- Existing non-RAG Chat Trace behavior and default LLMTraceRecorder completion
  behavior remain unchanged.
- Provider adapters, Retriever, vector stores, and prompt builder remain free
  of database and Trace dependencies.
- FastAPI routes remain thin.
- The `search_knowledge_base` Tool does not create a standalone RAG Trace or
  take over its caller's transaction in this batch.
- No full prompt/context/vector, secret, filesystem path, raw exception text,
  paid Provider response, or real user database is used or persisted.

## TDD Strategy

### Cycle 1: Models, Migration, And Metadata

Write failing tests for ORM ownership, field constraints, rank uniqueness,
Trace cascade deletion, source deletion survival, strict JSON metadata, and
migration structure/lifecycle. Implement the models, exports, schemas, and
`20260808_0009` only after the RED evidence is observed.

### Cycle 2: Standalone RAG Query Trace

Write failing Retriever/service/API tests for the backward-compatible batch
result, candidate scores and ordering, zero-hit Provider/model identity, one
Run per request, legacy RagQuery compatibility, and durable class-only
retrieval failure Trace records. Implement the batch result, recorder, and
public-query orchestration minimally. Add a dependency/integration regression
proving the Agent Tool executor uses the untraced transaction-safe policy.

### Cycle 3: RAG Chat Prompt And Answer Trace

Write failing service/API tests for exact step order, prompt version, ordered
source/candidate mapping, truncation flags, answer IDs, Run totals/output,
zero-hit Chat, and Provider-failure audit reconstruction. Implement the RAG
Chat coordinator and the backward-compatible LLM completion option minimally.

Tests use Mock LLM/Embedding Providers, fake Vector Stores, synthetic
credentials/content, temporary SQLite, and system-temporary storage only. No
real Provider, network Tool, `.env`, credential store, or
`backend/ai_agent_lab.db` is accessed.

## Verification And Documentation

Matching verification covers new retrieval model/schema/recorder tests plus
existing Trace, RAG Query/Chat, Retriever, Prompt, Chat, Provider-error, and
migration tests. Completion also requires:

- full backend tests from explicit system-temporary database/storage paths;
- `pip check`;
- frontend typecheck, Vitest, and build as regression gates;
- temporary SQLite upgrade, current/check-heads, Alembic check, downgrade to
  the previous revision, and re-upgrade;
- Markdown local-link validation;
- secret/private-key, generated-artifact, network-Tool, and later-Plan runtime
  scans;
- `git diff --check`, status, staged-path, ref, and scope checks;
- Codex-only final self-review.

Docker/Qdrant live smoke and headed browser replay are not matching gates
because this batch does not change vector-store adapter behavior, payload
filters, API response contracts, or frontend UI. Their omission is recorded
with that risk rationale in the review.

Current-fact documentation updates include `docs/30-trace-observability.md`,
`docs/23-naive-rag.md`, `docs/01-architecture.md`, README, README_CN,
CHANGELOG, the Plan 4 execution table for Batch 5/S4-S6 only, and a dedicated
Codex review record.

## Acceptance Criteria

1. Successful standalone RAG Query creates one completed `rag_query` Run,
   one completed retrieval Step, one RetrievalRun, and correctly ordered
   candidate rows, including the zero-hit case.
2. Successful RAG Chat creates one completed `rag_chat` Run with exactly the
   ordered retrieval, prompt, LLM, and final-answer Steps.
3. Candidate scores, ranks, selection, bounded previews, and source metadata
   match the validated Retriever results without persisting full context or
   vectors.
4. Prompt metadata identifies the version and exact ordered subset used under
   the context budget; answer metadata preserves all existing audit IDs.
5. Retriever failures persist one class-name-only failed Run/Step after
   rolling back business and candidate rows.
6. RAG Chat Provider failures retain successful retrieval/prompt audit
   evidence and a failed LLM Step while provisional business rows remain
   rolled back.
7. Source deletion does not erase retrieval audit evidence; Trace deletion
   cascades through all retrieval audit rows.
8. Existing RAG/Chat API contracts and non-RAG Trace behavior remain
   compatible.
9. No S7-S9 API/UI, Advanced RAG, evaluation, or later-Plan runtime behavior
   is implemented.
10. Focused and full verification pass, documentation matches implementation,
    and Codex self-review has no remaining must-fix finding.
