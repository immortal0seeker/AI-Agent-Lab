# Plan 3 M4 S7～S8 RAG Audit And Search Tool Design

## Status And Scope

This design implements only `P3-M4-S7～S8`:

- persist a `rag_queries` audit row for successful retrieval;
- register `search_knowledge_base` in the Tool Registry used by the existing
  Plan 2 Simple Agent loop;
- verify Query, Chat, Tool, migration, transaction, and Agent integration;
- update current Plan 3 documentation and acceptance evidence.

It does not implement frontend work, Advanced RAG, reranking, evaluation,
Trace runtime, Memory, OCR, multimodal behavior, Human Approval, or a new Agent
state. The normal `main` workspace remains unstaged and uncommitted for the
user's manual Git workflow.

## Acceptance Matrix

| Requirement | Current evidence | Gap | Minimal S7～S8 change |
|---|---|---|---|
| Record query and Knowledge Base | `RagQuery` already owns both columns | Query/Chat never create a row | Create one row after successful retrieval |
| Record requested Top-K | Request metadata carries `top_k`; table has no column | Zero-hit retrieval cannot encode Top-K in a chunk list | Add strict `rag_queries.top_k` column and migration |
| Record source IDs | `RetrievalResult` carries KB/Document/Chunk IDs and metadata | No durable snapshot | Store ordered JSON snapshots of successful retrieval results |
| Record latency | `latency_ms` exists with non-negative constraint | Service does not measure retrieval | Measure the retrieval section with `perf_counter()` |
| Query audit | `/rag/query` uses `RagQueryService` | It intentionally wrote nothing through S6 | Persist audit without introducing any LLM dependency |
| Chat audit | Chat persists Message and LLMCall transactionally | No RagQuery links to the turn | Link the same audit row to Conversation and assistant Message |
| Tool contract | Registry supports validated asynchronous read-only tools | No knowledge search Tool | Add bounded `SearchKnowledgeBaseTool` using the query service contract |
| Agent integration | Simple Agent already executes Tool Registry tools | Production registry only contains file tools | Register the RAG Tool through a lazy request-scoped executor |
| Plan 2 compatibility | Agent can answer without calling a tool | Eager RAG dependency creation would require Embedding credentials | Delay Embedding/Qdrant construction until the Tool is actually run |
| Safe failures | Agent normalizes Tool exceptions | Direct Tool errors still need stable output | Return fixed safe failure text for invalid/domain retrieval failures |

## Chosen Architecture

### 1. Durable Audit Schema

Add `top_k INTEGER NOT NULL DEFAULT 5` to `rag_queries` with a database check
constraint requiring values from 1 through 100. The ORM and Pydantic create/read
schemas use the same strict range. A new Alembic head upgrades from
`20260801_0006`, backfills existing rows through the server default, and removes
only the new constraint/column on downgrade.

`retrieved_chunks_json` remains an ordered list. Each entry is the JSON-mode
snapshot of the corresponding `RetrievalResult`, augmented with a one-based
`source_index`. This preserves the source IDs, score, content, filename,
location, and metadata that were actually returned. There is no synthetic
parameter entry in this list; `top_k` is a real column.

### 2. One Retrieval, One Audit Row

`RagQueryService.query()` continues to own Knowledge Base validation and the
single Retriever call. After retrieval succeeds it creates and flushes exactly
one `RagQuery` with:

- `knowledge_base_id` and the unchanged query text;
- requested `top_k`;
- ordered source snapshots;
- non-negative retrieval latency in milliseconds;
- no Conversation or answer link for the query-only endpoint.

`RagQueryResult` exposes the ORM row internally. The public Query response adds
`rag_query_id` while retaining its existing results and retrieval metadata. It
still does not resolve an LLM Provider or generate an answer.

`RagService.chat()` calls the inherited query operation once. After the
assistant Message exists, it links that same audit row to the existing
Conversation and assistant Message. User Message, audit row, assistant Message,
LLMCall, and Conversation update remain in the same request transaction. A
retrieval or Provider failure rolls the complete new turn back, including the
audit row, while preserving previously committed history. The Chat response
also exposes `rag_query_id`.

### 3. Search Tool Boundary

Create `backend/app/tools/builtin/search_knowledge_base.py` with
`SearchKnowledgeBaseTool`. Its JSON Schema accepts only:

- `knowledge_base_id`: required UUID string;
- `query`: required non-blank string, at most 20,000 characters;
- `top_k`: optional integer, default 5, from 1 through 20.

The Tool-level maximum is deliberately lower than the API/Retriever maximum of
100 so the existing 32,000-character Agent observation envelope remains useful.
Each Tool result excerpt is capped at 600 characters. The result is marked
`read_only`: retrieval has no user-data mutation, while the mandatory audit row
is an observability side effect like the existing ToolCall record.

The Tool receives an asynchronous query executor rather than constructing a
Provider or Vector Store itself. Its success output contains:

- concise indexed source excerpts in `content`;
- structured source summaries in `data.results`;
- strategy, result count, requested Top-K, and `rag_query_id` in metadata.

The content prefix explicitly identifies retrieved chunks as untrusted data,
not instructions. Invalid arguments return `Invalid search_knowledge_base
arguments`; missing Knowledge Base or retrieval/provider/vector failures return
`Knowledge base search failed`. Neither path exposes raw exception text, query
text, credentials, local paths, or Provider diagnostics.

### 4. Lazy Agent Registration

The production Agent registry must advertise the new Tool without eagerly
initializing RAG infrastructure. A request-scoped executor captures only the DB
Session and validated Settings. On actual Tool execution it creates the existing
Embedding Provider, Qdrant Vector Store, Retriever, and `RagQueryService`, then
closes the owned Vector Store in `finally`.

`get_tool_registry()` keeps its direct-call behavior for existing tests and
callers: it returns fresh `read_file` and `list_dir` tools. A new
`get_agent_tool_registry()` dependency receives that base registry plus the lazy
executor and adds `search_knowledge_base` for production Agent requests. This
prevents a normal Plan 2 Agent answer from failing merely because Embedding
credentials are absent.

No new Agent runtime state or permission policy is introduced. The existing
Simple Agent validates arguments, records ToolCall rows, enforces `read_only`,
bounds execution time, and serializes the Tool observation.

## Data And Transaction Flows

### Query API

```text
validate request
  -> verify Knowledge Base
  -> embed query and search Qdrant once
  -> create/flush RagQuery audit
  -> return rag_query_id + results + metadata
  -> request dependency commits
```

### RAG Chat

```text
resolve model/provider and existing Conversation
  -> append user Message
  -> retrieve once and flush RagQuery audit
  -> build grounded Prompt and call LLM once
  -> append assistant Message and LLMCall
  -> link RagQuery to Conversation/assistant Message
  -> request dependency commits all rows together
```

### Simple Agent Tool

```text
LLM requests search_knowledge_base
  -> Agent validates bounded arguments
  -> lazy executor initializes current RAG adapters
  -> RagQueryService retrieves and flushes audit
  -> Tool returns safe source summary + rag_query_id
  -> Agent records ToolCall and continues the existing loop
  -> request dependency commits Agent/Tool/RagQuery rows together
```

## Error And Security Boundaries

- Invalid API payloads remain FastAPI/Pydantic `422` responses.
- Unknown Knowledge Bases and existing Retriever/Embedding/VectorStore errors
  retain their current safe API mappings.
- No RagQuery row is written when Knowledge Base validation or retrieval fails.
- Chat Provider failure rolls back its provisional RagQuery row and all new turn
  records.
- Tool failures use fixed safe messages; raw source or Provider diagnostics are
  never put in the error field.
- Audit JSON contains only the already returned retrieval result contract. It
  never contains API keys, HTTP headers, local `.env` content, or LLM prompts.
- Tests use temporary SQLite, deterministic Mock Providers/Vector Stores, and a
  random local Qdrant collection only. The user database is never opened.

## TDD And Verification Design

TDD proceeds in two behavior groups:

1. RagQuery schema/model/migration and Query/Chat audit behavior:
   - write strict `top_k` and migration RED tests;
   - write Query persistence/zero-hit/failure RED tests;
   - write Chat linkage and rollback RED tests;
   - implement the minimal migration and service changes;
   - verify API response IDs and transaction ownership.
2. Search Tool and Simple Agent integration:
   - write missing-module/contract RED tests;
   - write bounded argument and safe failure RED tests;
   - write Agent two-provider-step Tool-call RED test;
   - write lazy production-registry RED proving no eager RAG initialization;
   - implement the Tool, registration, and lazy executor.

Matching verification covers RagQuery model/schema/migration, RAG service/API,
Tool validation/registry, Simple Agent service/API, Retriever, embedding/vector
boundaries, and error paths. A live local Qdrant smoke uses deterministic Mock
Embedding and Mock LLM with temporary SQLite to prove the production Agent Tool
path and its audit; direct Query/Chat audits remain covered by service/API tests.
The smoke deletes and rechecks the random collection in `finally`.

Completion also requires full backend regression, `pip check`, temporary
Alembic upgrade/current/check/downgrade/re-upgrade, frontend typecheck/tests/
build, Compose/Qdrant health, Markdown links, secret/private-key scans,
later-Plan runtime scans, artifact checks, exact diff allowlist,
`git diff --check`, refs, staged paths, and status.

## Alternatives Rejected

1. **Put Top-K in `retrieved_chunks_json`.** Rejected because a zero-hit result
   has no natural entry and a synthetic parameter row would make the source list
   heterogeneous.
2. **Let the Tool call Retriever and write its own audit.** Rejected because it
   duplicates validation, timing, JSON snapshot, transaction, and error logic.
3. **Eagerly inject `RagQueryService` into every Agent request.** Rejected
   because Provider construction requires Embedding configuration even when the
   Agent never calls the knowledge Tool, regressing the stable Plan 2 contract.

## Explicit Deferred Work

- frontend Knowledge Base/RAG pages and source cards (M5);
- RagQuery list/detail APIs or retention controls;
- streaming RAG and streaming Agent execution;
- metadata filters, Hybrid Search, Rerank, Evaluation, Trace runtime, and other
  Advanced RAG behavior (Plan 4);
- Human Approval or new Agent states (later Plans);
- real paid Embedding/LLM Provider acceptance.
