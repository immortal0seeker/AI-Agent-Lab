# Architecture

## Current Architecture Stage

This document describes the Plan 1 architecture delivered by `v0.1.0` and the
Plan 2 Tool Calling foundation built on top of it. The repository has
completed `P1-M1-S1` through `P1-M4-S8`, including the health
flow, database and Provider foundations, transactional Conversation and Chat
services, non-streaming and SSE Chat routes, Registry model selection,
conversation navigation, refresh recovery, successful-call usage persistence,
structured errors, request-linked logging, focused regression coverage,
recoverable frontend initialization states, clean-start documentation, release
materials, and the expanded final review. Plan 1 remains closed. Plan 2 has
completed implementation, final review, release, and the `P2-M5-S8` tag gate:
Tool contracts, Registry, validation,
read-only path policy, AgentRun/ToolCall persistence, and the executable
`read_file` and `list_dir` builtins are available. The Provider contract now
accepts typed Tool definitions and normalizes non-streaming Tool Calls; an
independent adapter converts the Registry in stable order, and the
OpenAI-compatible adapter maps `tools` without leaking vendor payloads into
services. `web_fetch` remains deferred. A backend-only `SimpleAgentService`
now owns a bounded multi-step loop, observation backfill, per-Tool timeout,
structured failure results, observation compaction, and AgentRun/ToolCall
persistence. Validated plural Agent create/query routes expose that service. A
dedicated frontend Agent workspace consumes the synchronous API and renders
bounded ToolCall audit details. M5 adds safety regression coverage plus
sanitized desktop/mobile release evidence; no network Tool is implemented at
this stage. The final review revalidated all five Plan 3 bridge contracts, and
the user published `v0.2.0` from commit `0e3f3a6` and the subsequent `v0.2.1`
  audit patch from commit `872310b`. Plan 3 starts from `v0.2.1`; its
  `P3-M6-S1～S6` release candidate adds Qdrant configuration, explicit
  `knowledge/` and `rag/`
ownership boundaries, four knowledge persistence models, a service-owned
Knowledge Base CRUD API, controlled validated Document upload, and independent
Markdown/TXT/text-layer-PDF parsers composed with pure cleaning, naive
Chunking, and synchronous `DocumentChunk` persistence. The subsequent M1/M2
audit patch binds Qdrant to loopback, enforces canonical stored paths and
processing ceilings, and adds final database constraints. M3 S1～S6 add the
vendor-neutral Embedding Provider/result contract, an ordered runtime Registry,
and a concrete OpenAI-compatible adapter with independent lazy configuration,
safe HTTP/response errors, and strict dimension checks. M3 S7～S9 add a
vendor-neutral asynchronous VectorStore contract, a Qdrant 1.15.x adapter, and
the stable Chunk payload bridge required by M4. M3 S10～S12 add an independently
  tested upload-to-vector pipeline, persisted Chunk point IDs and Document
  embedding states, plus request-transaction vector compensation. M4 S1～S3 add
  an independent Top-K Retriever and immutable source result contract. M4
  S4～S6 add a bounded Prompt Builder, a retrieval-only Query service/route, and
  a non-streaming RAG Chat service/route that persists Message and LLMCall rows.
  M4 S7～S8 persist a RagQuery audit for each successful Query/Chat/Tool
  retrieval and add a bounded read-only Knowledge Base search Tool to the
  existing Simple Agent through lazy request-scoped RAG initialization. M5
  adds the responsive Knowledge workspace, controlled upload/status flow, and
  a typed current-session RAG Chat with exact source and audit-ID display. M6
  revalidates every backend/frontend boundary, publishes sanitized release
  screenshots, synchronizes runtime metadata to `0.3.0`, and records the
  Codex-only final review. The user then published annotated tag `v0.3.0` at
  commit `46ea94a`. A subsequent independent Plan 3 audit repaired embedding
  identity isolation and compatible concurrent collection creation in the
  current working tree without adding Plan 4 runtime; the tag intentionally
  remains at the original release commit pending the user's manual follow-up
  release decision.

The first architectural goal is a thin, understandable web application foundation:

```text
React frontend -> FastAPI API routes -> services -> providers / database
```

API routes should remain thin. Validation belongs at the schema boundary, business logic belongs in services, and provider details stay behind provider adapters.

## Repository Structure

```text
AI-Agent-Lab/
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/
│       ├── core/
│       ├── db/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       ├── providers/
│       │   ├── embedding/
│       │   └── llm/
│       ├── knowledge/
│       ├── rag/
│       └── tools/
│           ├── base.py
│           ├── registry.py
│           ├── security.py
│           ├── validation.py
│           └── builtin/
│               ├── list_dir.py
│               ├── read_file.py
│               └── search_knowledge_base.py
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       └── types/
├── docs/
├── docs-plan/
└── docs-local/
```

The complete directory tree will be created incrementally. Plan 1 should not create future-plan modules before they are needed.

## Backend Boundaries

The backend uses FastAPI.

Current backend layers:

| Layer | Responsibility |
|---|---|
| `api/` | HTTP routes and response shaping |
| `schemas/` | Pydantic request and response contracts |
| `services/` | Chat, conversation, Agent query, Knowledge Base CRUD, Document upload/ingestion, Naive RAG query/chat, and application logic |
| `agents/` | Backend-only Simple Agent orchestration and Agent domain errors |
| `providers/` | LLM abstractions/adapters plus the M3 Embedding abstraction, validated batch result, runtime Registry, and OpenAI-compatible adapter/factory |
| `knowledge/` | Plan 3 structured knowledge metadata plus controlled Document storage; models live in `models/` and service policy lives in `services/` |
| `rag/` | Plan 3 document-processing and Naive RAG boundary; parsers, Cleaner, naive Chunker, ingestion pipeline, VectorStore/Qdrant, source payload, Top-K Retriever, bounded Prompt Builder, and audited Query/Chat orchestration exist through M4 S8 |
| `tools/` | Tool contracts, Registry, schema validation, read-only policy, and the bounded `search_knowledge_base` adapter |
| `db/` | SQLAlchemy session/database setup plus request-scoped async rollback callbacks and resource finalizers |
| `models/` | ORM models |
| `core/` | Config, logging, and error handling |

The first backend endpoint is implemented:

```text
GET /api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "ai-agent-lab-backend"
}
```

## Database Foundation

The current backend database layer uses SQLite, SQLAlchemy 2, and Alembic.
`DATABASE_URL` defaults to `sqlite:///./ai_agent_lab.db`, while schema creation
is owned by migrations rather than application startup.

SQLite is the default and long-term supported primary database for this
local-first, primarily single-user workspace. It is not a temporary database
that must be replaced after Plan 1. SQLAlchemy and Alembic should preserve
reasonable portability, but PostgreSQL is only an optional compatibility path
if the product later gains server deployment, multi-user access, or sustained
concurrent writes. Future modules should optimize for reliable local SQLite
operation without adding PostgreSQL-specific infrastructure preemptively.

Plan 3 adds Qdrant as a separate vector-storage service configured through
`QDRANT_URL`, `QDRANT_COLLECTION_NAME`, and `QDRANT_TIMEOUT_SECONDS`; it does
not replace SQLite business or audit persistence. The
Qdrant adapter can create/check one COSINE collection, upsert validated points,
search under a mandatory Knowledge Base filter, and delete under Knowledge Base
plus Document ownership filters. Upload ingestion writes Chunk points through
that adapter, while Query/Chat/Tool retrieval writes audit state only to SQLite.

The initial migration creates:

- `conversations`
- `messages`
- `llm_calls`

The Plan 2 M1 migration adds:

- `agent_runs`
- `tool_calls`

Plan 3 revision `20260726_0005` adds:

- `knowledge_bases`
- `documents`
- `document_chunks`
- `rag_queries`

All model IDs use UUID v4 values. Datetimes are stored as timezone-naive UTC
values because SQLite does not preserve timezone information consistently.
Deleting a conversation cascades to its messages and LLM calls. Deleting an
individual message preserves its LLM call records and sets `message_id` to
`NULL`.

`AgentRun` belongs to one Conversation and may reference the user Message that
started it. Deleting the Conversation cascades through its AgentRuns and
ToolCalls; deleting only that Message preserves the run and sets
`user_message_id` to `NULL`. `ToolCall` belongs to one AgentRun and repeats its
Conversation ID for direct lookup. A composite foreign key prevents that
Conversation identity from differing from its parent run.

Both records use UUID database identities. `ToolCall.tool_call_id` is a separate
string correlation identity and is unique within one AgentRun. Each ToolCall
also has a positive one-based `sequence_index`, unique within its AgentRun and
used for query order. Tool arguments and results use JSON columns. Named status
checks, non-negative latency checks, timestamps, and lookup indexes establish
persistence integrity without introducing an Agent runtime state machine.

`Document` belongs to one `KnowledgeBase`; `DocumentChunk` repeats the
knowledge-base identity beside its document identity, and a composite foreign
key rejects cross-knowledge-base chunks. Lifecycle checks bound parse, chunk,
and embedding states, while SHA-256 length, file type, numeric, metadata, and
vector fields form the later ingestion bridge. A same-Knowledge-Base hash
unique constraint is the final duplicate gate. Deleting a knowledge base that
still owns a Document is restricted; its RAG query audit records continue to
follow their independent database cascade.

`RagQuery` stores the original query, requested `top_k`, retrieval latency, and
the ordered retrieved-chunk JSON snapshot. It may
reference one answer Message only when a Conversation is also present, and a
composite foreign key rejects an answer from a different Conversation.
Deleting only the answer Message clears that optional reference and preserves
the query record. Revision `20260801_0007` backfills Top-K 5 for older rows and
enforces the persisted 1～100 range.

Foreign-key columns used by conversation and message lookups are indexed.
SQLAlchemy metadata uses a stable naming convention for primary keys, foreign
keys, indexes, unique constraints, and check constraints so future Alembic
migrations can reference schema objects predictably on SQLite.

The Knowledge Base create, read, and partial-update schemas feed five thin
plural `/api/v1/knowledge-bases` routes. `KnowledgeBaseService` owns create,
deterministically ordered list, detail, supplied-field update, and delete
behavior. It flushes changes while the request-scoped database dependency owns
commit, rollback, and session close. Unknown detail/update/delete IDs receive a
safe `knowledge_base_not_found` response. Deleting a non-empty Knowledge Base
returns safe HTTP 409 and preserves the Knowledge Base, Documents, chunks, and
controlled files. Empty deletion affects SQLite metadata only; no Qdrant client
or collection deletion exists in M1/M2.

`DocumentService` now validates the Knowledge Base and its 50-document default
limit before reading an upload, then delegates bounded staging, suffix checks,
SHA-256 calculation, and UUID path promotion to `DocumentStorage`. It rejects
same-hash content within one Knowledge Base while allowing it across different
Knowledge Bases. The service flushes but does not commit; Session callbacks
remove newly promoted files on request rollback. One thin multipart route,
`POST /api/v1/knowledge-bases/{knowledge_base_id}/documents`, returns the
final synchronous processing state in `DocumentRead`.

`app.rag.parsers` is a database- and API-independent extraction boundary.
Markdown preserves source markup and reports headings and fenced code blocks
without duplicating code content in metadata;
TXT uses deterministic strict UTF-8/BOM decoding; text-layer PDF extraction
uses `pypdf` and preserves one-based pages. Text-empty PDFs return the explicit
Plan 3 OCR limitation. `app.rag.text_cleaner` normalizes extracted text without
mutating parser output, and `app.rag.chunker` creates ordered overlapping
drafts with heading/page provenance. `DocumentIngestionService` resolves the
UUID-owned stored path, dispatches the parser, cleans and chunks, and flushes
ordered `DocumentChunk` rows. It then calls `app.rag.ingestion_pipeline`, which
checks the collection, batches Chunk content through the configured Embedding
Provider, constructs complete points, upserts, and verifies returned IDs. The
service persists `vector_id == str(chunk.id)` and `embedding_status=ready` only
after the whole write succeeds. Expected parser/content/Provider/VectorStore
failures remain committable safe Document resources; storage, database, and
unexpected failures propagate to request rollback.

One immutable processing-limit contract bounds PDF pages, extracted
characters, Markdown structures, and generated chunks. The Cleaner preserves
blank-line multiplicity inside fenced code and remaps heading/code-block line
metadata; the Chunker bounds persisted headings to the schema's 512-character
limit.

After a successful Qdrant upsert, the service registers an asynchronous Session
rollback callback. A later request commit failure rolls back SQLite and the
controlled file, deletes vectors under both Knowledge Base and Document
  ownership, and only then closes the request-owned Qdrant client. Hard-crash
  reconciliation, Document query/delete, and RAG answer generation remain
  deferred. The
complete contract is documented in [Knowledge Base Design](20-knowledge-base-design.md)
and [Document Ingestion Pipeline](22-document-ingestion-pipeline.md).

## Tool Calling Foundation

Plan 2 M1 defines an asynchronous `Tool` boundary and consistent `ToolResult`,
plus Provider/database-neutral ToolCall transport schemas. `ToolRegistry`
registers exact names in stable order, rejects duplicates, and exports defensive
OpenAI-compatible function schemas. JSON Schema Draft 2020-12 validation checks
tool schemas and arguments without echoing rejected values in errors. Public
Tool arguments/results must be standard JSON; Agent arguments are limited to
65,536 UTF-8 bytes before schema validation.

The read-only security module resolves workspace-relative paths and rejects
absolute, drive, UNC, parent-traversal, sensitive, private-key, Windows alias,
alternate-data-stream, symlink, and reparse-point inputs. Built-in paths are
limited to 4096 characters. File-size and directory-depth limits remain shared
policy helpers.

`ReadFileTool` is the first consumer of this boundary. It validates one `path`
argument, resolves it below an injected workspace root without following a
user-supplied link component, requires a regular file, rejects files over 1 MiB
before reading, rechecks the actual byte length, rejects private-key markers,
NUL, and non-UTF-8 content, removes a UTF-8 BOM, and truncates returned text after
100,000 decoded characters. The read itself requests at most the byte limit plus
one, so a file growth race cannot cause an unbounded allocation. Successful
metadata contains only a normalized
workspace-relative path, encoding, byte/character counts, and truncation state.
Expected validation, security, size, encoding, and filesystem failures become
fixed safe failed `ToolResult` values without raw paths, content, or exception
text. File I/O runs through `asyncio.to_thread`.

`ListDirTool` accepts a workspace-relative `path` and an optional `max_depth`.
Depth 1 lists direct children, the default is 2, and the hard limit is 3. It
returns at most 500 entries by default, ordered by normalized relative path for
non-truncated small directories, with name, `file`/`directory`/`symlink` type,
and regular-file byte size. It scans at most `max_entries + 1` children at each
visited directory and marks truncated output. It
filters sensitive entries before metadata access or recursion, keeps ordinary
dotfiles such as `.gitignore`, reports but never follows discovered symlinks,
and returns fixed safe failures. Directory metadata work also runs through
`asyncio.to_thread`.

The implemented Tool data path is:

```text
Caller-owned ToolRegistry
-> register_builtin_tools()
-> ReadFileTool or ListDirTool
-> argument and workspace security validation
-> bounded UTF-8 read or directory traversal
-> ToolResult
```

The implemented non-streaming Provider definition/response path is:

```text
Caller-owned ToolRegistry
-> build_llm_tool_definitions()
-> ChatRequest.tools
-> OpenAI-compatible payload.tools
-> Provider message.tool_calls
-> normalized LLMToolCall objects
```

The Provider portion transports definitions and parses requests selected by a
model. Malformed argument JSON, non-object
arguments, invalid names/IDs, duplicate IDs, and unrequested Tool Calls become
fixed `ProviderResponseError` values without echoing the raw arguments.
Streaming Tool requests fail locally before HTTP because Tool Call delta
aggregation remains outside the completed non-streaming scope.

The implemented backend Agent path is:

```text
SimpleAgentRequest
-> tools-capable ModelRegistry gate
-> Conversation + user Message + AgentRun(running)
-> provider.chat(history + Tool definitions)
   -> direct text -> assistant Message + AgentRun(completed)
   -> ordered Tool Calls that fit the remaining Tool budget atomically
      -> read-only permission + validation before persistence
      -> timeout-bounded execution + sequenced ToolCall rows
      -> assistant Tool Call message + correlated Tool observations
      -> next provider.chat()
   -> Tool Calls beyond budget -> AgentRun(failed), no partial execution
   -> Provider/blank/whole-run-timeout failure -> structured AgentRun(failed)
```

`max_steps` defaults to 3, is limited to 10, and counts ToolCall execution
attempts. A whole Provider batch that exceeds the remaining budget is rejected
before any call in that batch is persisted or executed. A run that consumes
exactly N Tools may make an N+1 Provider decision for final text. Calls execute
sequentially in Provider order. Only `read_only` Tools may execute; unknown,
invalid, or blocked calls store `{}` arguments and a safe result. Each Tool's
finite timeout maps to `timeout`, and `AGENT_RUN_TIMEOUT_SECONDS` bounds the
entire loop while preserving completed ToolCalls.
Intermediate Tool protocol messages remain in-process because the current
Message table cannot losslessly represent correlation fields. ToolCall rows
retain arguments, complete validated results, status, and timing; only the
Provider observation is compacted when it exceeds the configured character
bound. Runtime failure results remain committable because the service flushes
but does not commit.

The implemented HTTP boundary is:

```text
POST AgentRunCreate
-> AgentService input/content conversion
-> request-scoped SimpleAgentService
-> AgentRunExecutionRead + commit

GET AgentRun / ToolCalls
-> session-only AgentService
-> deterministic read schema
```

The POST response treats a structured failed AgentRun as a persistent HTTP 201
resource; preflight and transaction errors still use rollback and the unified
safe error envelope. The two GET routes never resolve Provider or Tool runtime
dependencies, so history remains readable without a configured Provider key.

`web_fetch` is intentionally absent from this architecture. A future
reassessment must define SSRF-safe address and redirect validation, DNS-
rebinding resistance, bounded streaming, content policy, text extraction,
safe errors, and mock acceptance coverage before exposing a network Tool.

The plural `/api/v1/agents/runs` POST and query routes and frontend Agent/ToolCall
visualization are implemented. ToolCall execution order is strictly persisted
through `sequence_index`; this is not an AgentStep/Trace timeline. Agent
Provider calls are not yet linked to `LLMCall`, and complete Provider
request/response replay remains a later observability concern. See
[Tool Calling Design](10-tool-calling-design.md)
for the detailed boundary, [Simple Agent Loop](11-simple-agent-loop.md) for step
counting and failures, and [Agent API](12-agent-api.md) for the HTTP contract.

## Frontend Boundaries

The frontend uses React + Vite + TypeScript.

Expected Plan 1 frontend areas:

| Area | Responsibility |
|---|---|
| `src/api/` | API client wrappers |
| `src/types/` | Shared TypeScript types |
| `src/pages/` | Page-level views |
| `src/components/` | Feature and layout components |

The UI should feel like an engineering workspace: quiet, dense, readable, and practical. It should not become a marketing landing page.

The frontend includes typed health, Models, Conversations, Messages, Chat,
Agent, Knowledge, and RAG API wrappers, an SSE parser, Zustand Chat/RAG state,
page/component
boundaries, and a responsive Chat workspace. The store guards stale stream and
history callbacks, preserves partial output after Stop, and replaces temporary
messages with canonical backend data after a successful `done` event. It loads
Registry models and recent conversations independently, while
`?conversation=<uuid>` preserves the selected conversation across refreshes.

`App` uses small URL helpers to select the Chat, Agent, or Knowledge workspace without
introducing a router or moving the existing Chat state. `AgentPage` independently
loads health and Registry models, filters to `supports_tools=true`, and owns the
synchronous create/restore flow. The controlled task form, result panel, and
ToolCall timeline/card components render loading, empty, no-model, completed,
structured failed, and transport-error states. Deterministic JSON plus bounded
argument/result summaries keep the audit cards readable, while full AgentRun,
Conversation, ToolCall correlation, sequence, and database IDs remain visible.
`?workspace=agent&run=<uuid>` restores a persisted run through parallel AgentRun
and ToolCall reads. A request gate prevents a late POST response from mutating
state or URL after the Agent page unmounts; the returned UUID is still saved in
tab-scoped session storage so reopening Agent without an explicit run URL can
recover it. An explicit URL has priority, and New task clears the recovery ID.

`ChatPage` separates workspace initialization from ready-state message
rendering through `WorkspaceStatusPanel`:

```text
idle/loading -> initialization progress; composer and model selection disabled
error        -> one safe error plus a manual Retry action
Retry        -> initialize(valid conversation ID from the current URL)
ready        -> empty, conversation loading, streaming, completed, stopped, or Chat error
```

The Retry action reuses the existing Zustand initializer. It does not add an
automatic retry loop, delay, backoff, or new store state. Initialization errors
are rendered in the status panel rather than duplicated in the ready-state
error banner. Conversation-loading and Chat errors continue to use their
existing ready-state presentation.

Backend settings are loaded from `backend/.env` when backend commands run from
the backend directory. Vite loads `frontend/.env` for frontend commands. The
root `.env.example` is documentation-only in the current architecture and is
not automatically consumed by either application.

`DOCUMENT_STORAGE_ROOT` defaults to `backend/uploads`, relative values resolve
from the backend root, `DOCUMENT_MAX_UPLOAD_BYTES` defaults to `20_971_520`,
and `DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE` defaults to `50`. Uploads use
temporary staging and UUID-owned final paths. SQLite owns the Document row;
local storage owns the bytes. Request rollback coordinates the two for normal
failures, while hard-crash orphan recovery and deletion cleanup remain
deferred.

## Plan 1 Data Flow

Plan 1 will evolve toward this flow:

```text
User message
-> Frontend chat UI
-> FastAPI chat route
-> Chat service
-> LLM provider adapter
-> Provider response or stream
-> Conversation persistence
-> Frontend message rendering
```

The current non-streaming flow uses server-owned history:

```text
Chat request with one new user turn
-> request-scoped SQLAlchemy Session
-> Registry model validation and Provider resolution
-> load or create Conversation
-> append user Message and load ordered history
-> BaseLLMProvider.chat()
-> append assistant Message and completed LLMCall
-> commit before the HTTP response is sent
```

Provider failures roll back all records created by that Chat request. On
success, normalized Provider usage, Registry-based estimated cost, and Provider
latency are stored on `LLMCall`. Missing usage leaves token and cost fields
`NULL`; an unknown input or output Registry price also leaves cost `NULL`.

The streaming flow owns a SQLAlchemy Session inside the response generator:

```text
POST /api/v1/chat/stream
-> validate model and resolve Provider
-> append the pending user turn and load ordered history
-> BaseLLMProvider.stream_chat()
-> emit SSE delta events while accumulating assistant text
-> append assistant Message and completed LLMCall
-> commit, then emit one SSE done event
```

If the Provider fails, the completion is empty, or the client cancels before
completion, the uncommitted turn is rolled back. The frontend retains stopped
partial text only in local state.

Streaming latency accumulates only the time spent awaiting Provider chunks, so
SSE consumer backpressure is not counted as model latency. The completed
`LLMCall` is committed before the terminal `done` event.

## Basic Errors And Request Logging

Every HTTP request receives a new server-generated UUID. The backend ignores
client-provided request IDs and returns its value in `X-Request-ID`. A pure ASGI
middleware keeps the same request context active until a streaming response is
fully consumed.

HTTP and SSE failures use the same inner error object:

```json
{
  "error": {
    "code": "provider_timeout",
    "message": "The model provider timed out",
    "request_id": "server-generated-uuid"
  }
}
```

Provider authentication, rate limit, timeout, bad request, server, response,
and unknown failures map to safe application errors. Database and unexpected
errors return fixed messages without exposing SQL, paths, stack text, upstream
response bodies, or credentials. SSE errors remain HTTP 200 after response
streaming has started and terminate with `event: error`.

Standard-library logs record request method/path/status/duration and model-call
provider/model/outcome/latency. They do not record request or response bodies,
complete messages, authorization headers, Provider error bodies, or SQL
parameters. This request-linked logging is a Plan 1 diagnostic foundation, not
the persistent Trace/Timeline system scheduled for Plan 4.

## Provider Principle

External AI capabilities should be provider-based. Plan 1 starts with LLM providers only. Later plans will add other provider families, but they should not be implemented during Plan 1 unless the active step explicitly requires them.

Plan 1 provider target:

- `BaseLLMProvider` defines vendor-neutral asynchronous `chat` and `stream_chat` contracts.
- Typed request, response, chunk, token usage, Tool definition, and Tool Call models isolate future services from vendor payloads.
- `build_llm_tool_definitions()` converts a caller-owned Tool Registry into defensive Provider definitions without executing tools.
- `OpenAICompatibleProvider` maps non-streaming JSON, non-streaming `tools`/`tool_calls`, and text-only streaming SSE responses through `httpx`.
- `create_openai_compatible_provider()` converts application settings into an adapter only when a call path needs one.
- API keys use `SecretStr`, remain optional during health-only startup, and are required with a readable error at Provider initialization.
- Mock transports verify Provider behavior without real credentials or paid API calls.
- `ModelRegistry` loads strict JSON metadata, preserves configuration order, filters by provider, and resolves exact `(provider, model)` identities.
- Registry capability labels describe behavior implemented for each configured model. Streaming is enabled for the example entry; Tool Calling stays disabled because the current batch proves the adapter protocol only and does not verify a real model or Agent path. JSON mode also remains disabled.
- Registry metadata is immutable. Unknown fields, blank names, negative prices, duplicate identities, unreadable files, and invalid JSON fail explicitly.

Plan 3 Embedding provider target through `P3-M3-S6`:

- `EmbeddingProvider` defines vendor-neutral asynchronous batch-text and query
  contracts and owns a normalized, immutable runtime name.
- `EmbeddingResult` preserves ordered vectors, model identity, batch token
  usage, consistent non-zero dimensions, and finite numeric values.
- `EmbeddingProviderRegistry` registers instances in stable order and selects
  one by an exact caller-owned configuration name.
- `OpenAICompatibleEmbeddingProvider` sends batch/query requests to
  `/embeddings`, normalizes safe request/response errors, restores response
  order from indexes, and checks returned vectors against the configured
  dimension.
- Embedding Settings are independent from LLM Settings and remain lazy until
  the concrete factory is called. M3 ingestion selects the configured Provider
  at upload dependency resolution and returns a safe 503 before file creation
  when that configuration is unavailable.

Plan 3 VectorStore, ingestion, retrieval, and Naive RAG target through
`P3-M4-S8`:

- `VectorStore` defines asynchronous collection, upsert, search, ownership
  delete, and client-lifecycle operations behind validated immutable contracts.
- `QdrantVectorStore` is the only Qdrant SDK boundary. It uses one default
  COSINE dense vector, rejects incompatible existing collection configuration,
  recovers a compatible concurrent first-create winner, waits for writes, and
  normalizes SDK failures without exposing diagnostics.
- search always filters `knowledge_base_id`, embedding Provider, and the actual
  Provider-returned model; deletion matches both `knowledge_base_id` and
  `document_id`.
- Chunk payloads store canonical IDs, embedding Provider/model identity,
  filename/index/content, optional heading/page, and nested JSON-safe metadata.
  They provide the source bridge for M4 without implementing a Retriever early.
- `ingest_document_vectors()` rejects count/dimension/ownership/order or point-ID
  contract mismatches before ready state and compensates uncertain upsert
  results.
- SQLite persists every successful Chunk point ID and final Document embedding
  state; request rollback performs best-effort ownership-scoped vector cleanup.
- `RetrievalResult` is an immutable source value containing canonical Knowledge
  Base/Document/Chunk IDs, filename/index/content/score, optional heading/page,
  and copied JSON metadata.
- `Retriever` validates query, Knowledge Base UUID, Top-K (1～100), and optional
  finite score threshold before external calls. It requires exactly one query
  vector with the VectorStore dimension, performs one Knowledge-Base-filtered
  search, and fails closed on invalid result type, ownership, count, or
  threshold. It preserves VectorStore order and does not rerank.
- `RagPromptBuilder` creates one fixed grounded system message, preserves
  user/assistant history, assigns stable one-based source indices, and limits
  only the formatted source context through `RAG_MAX_CONTEXT_CHARACTERS`.
- `RagQueryService` validates Knowledge Base existence and performs retrieval
  without resolving a ModelRegistry/LLM Provider. Every successful retrieval
  writes one RagQuery audit containing requested Top-K, ordered source snapshots,
  and retrieval latency; it never writes Message or LLMCall. The thin route is
  `POST /api/v1/rag/query` and returns the audit ID.
- `RagService` extends retrieval with existing Conversation, Provider, and
  LLMCall boundaries. `POST /api/v1/rag/chat` stores the raw user query and the
  non-streaming assistant answer, returning only sources actually injected in
  the Prompt plus retrieval/Prompt metadata and the linked audit ID. Failure
  rolls back the whole turn and audit.
- The production Simple Agent Registry adds read-only
  `search_knowledge_base` through a lazy executor. It reuses
  `RagQueryService`, restricts Tool Top-K to 1～20, returns bounded source
  summaries, and initializes Embedding/Qdrant only when the Tool executes.

Plan 3 frontend implementation through `P3-M5-S6`:

- `WorkspaceView` has three explicit values: `chat`, `agent`, and `knowledge`;
  unknown URL values still fail safely to Chat.
- `api/knowledge.ts` is the browser boundary for Knowledge Base list/create and
  nested multipart Document upload. It uses the existing safe backend error
  envelope and leaves multipart `Content-Type` construction to the browser.
- `KnowledgeBasePage` owns feature-local list/create/upload state. It composes
  `KnowledgeBaseList`, `KnowledgeBaseCreateForm`, `FileUploadPanel`, and
  `DocumentStatusCard`, then exposes Documents/RAG Chat tabs for the selected
  Knowledge Base.
- Initial list and health requests ignore results after unmount. Create and
  upload serialize conflicting actions, and changing the selected Knowledge
  Base clears the previous upload response.
- The upload view shows only the returned original filename, Document ID, type,
  byte size, creation time, safe processing error, and exact parse/chunk/
  embedding states. It intentionally excludes stored paths, hashes, raw
  metadata, and Provider diagnostics.
- Upload is synchronous, so the page does not poll. Because there are no
  Document list/detail/chunk-query routes, the current page cannot restore a
  persistent Document history or preview Chunks after refresh.
- `api/rag.ts` and `types/rag.ts` define the strict non-streaming Query/Chat
  browser contract. `api/conversations.ts` also exposes robust Conversation
  creation with the same safe structured/transport/invalid-JSON failures.
- The focused Zustand RAG store initializes registered models, creates one
  dedicated Conversation on the first question, reuses it for the current
  session, and ignores aborted or stale requests. It validates response
  Conversation/Knowledge Base ownership plus every source owner/index/count
  before accepting data.
- `RagChatPage`, `RagComposer`, and `RagAnswerPanel` render loading, no-model,
  empty, sending, safe-error, and result states. Source cards keep backend
  order and display filename, Chunk index/content, score, heading/page, stable
  nested metadata, and RagQuery/LLMCall/Conversation correlation IDs.
- RAG Chat is non-streaming and current-session only. There is no RagQuery list
  or detail endpoint, so refresh cannot restore prior RAG turns or source cards.

The Provider stream contract is consumed by `ChatService.stream_complete()` and
the protocol adapter at `POST /api/v1/chat/stream`. The service emits
protocol-neutral domain events; the route owns SSE framing and stream-scoped
Session cleanup. Streaming requests with Tool definitions are explicitly
unsupported and rejected before any Provider HTTP request.

The tracked Registry entry is example configuration. `GET /api/v1/models`
exposes non-secret Registry metadata in configuration order, and the frontend
uses exact `(provider, model)` identities. Conversation defaults remember the
last successfully used registered identity.

Conversation reads remain independent resources:

```text
GET /api/v1/conversations
GET /api/v1/conversations/{conversation_id}/messages
```

The list is ordered by recent successful activity. Messages retain deterministic
creation order. No composite workspace bootstrap endpoint, pagination, rename,
or delete behavior is introduced in M3.

## Plan 3 v0.3.0 Release And Post-Release Audit Gate

M6 closes Plan 3 without changing runtime architecture. Existing focused tests
provide the S1～S4 acceptance evidence: the combined model/API/document-
processing/Embedding/VectorStore/ingestion/Retriever group reached
`339 passed`, and RAG Query/Chat/Tool/Agent reached `112 passed`. Complete
backend regression reached `1024 passed` with one known Starlette/httpx
deprecation warning; the frontend reached `25` files / `149` tests, TypeScript
checking, and a production build of `1826` transformed modules.

The release browser acceptance is deliberately outside production state. A
fresh Playwright session intercepted only local API routes with complete
synthetic Knowledge Base, Document, model, Conversation, RAG answer/source,
usage, and audit resources. It verified desktop `1440×900`, narrow `390×844`,
zero horizontal overflow, zero failed requests, zero console warnings/errors,
and `New RAG chat` reset. The resulting sanitized screenshots are committed in
`docs/assets/plan3/`; no real credential, Provider, user SQLite database, or
network Tool was used.

The local infrastructure gate verified Docker Engine `29.6.2`, running
`qdrant/qdrant:v1.15.4`, restart count zero, loopback-only
`127.0.0.1:6333`, and HTTP 200 health. A random temporary collection exercised
the production Qdrant adapter for collection creation, two-Knowledge-Base
upsert, ownership-filtered search, Document-scoped deletion, and final cleanup.
Temporary-SQLite Alembic upgrade/current/check/downgrade/re-upgrade passed at
head `20260801_0007` and the directory was removed.

The five Plan 4 bridge contracts remain intact: shared
`search_knowledge_base` retrieval/audit, persisted `RagQuery` Top-K/source/
latency/linkage fields, source-rich `DocumentChunk`, RAG response retrieval
metadata/audit identity, and Qdrant Knowledge Base/Document/Chunk payload IDs.
The post-release audit further makes embedding Provider/actual-model identity
part of the payload, query filter, response, and audit snapshot. No Trace,
Advanced RAG, reranking, or evaluation runtime is added. Package, OpenAPI,
frontend, and lockfile metadata is `0.3.0`; annotated tag `v0.3.0` remains at
the original release commit while its audit repair awaits manual release.

## Security Boundaries

Secrets must not be committed.

Configuration examples may include empty variable names, but not real values. API keys should only be supplied through local `.env` files, environment variables, or a future approved secret mechanism.

Do not write secrets to:

- README
- docs
- tests
- fixtures
- screenshots
- logs
- frontend state
- database seed data

## Documentation Boundaries

- `docs-plan/` is the source of planning truth and execution sequencing.
- `docs/` is for formal project documentation that matches implemented or actively scoped behavior.
- `docs-local/` is for ignored local drafts, private review notes, and sensitive temporary material.

## Deferred Capabilities

The current workspace includes read-only Tool execution, the bounded Simple
Agent loop, backend Naive RAG, and the Plan 3 release-candidate Knowledge/RAG
frontend. The
following remain outside the current architecture:

- `web_fetch` or another network Tool
- streaming Tool Calling
- Agent Runtime v2, Planner, Human Approval, cancel/resume/retry, and replay
- a frontend for the Agent knowledge Tool
- persistent Document list/detail/Chunk preview/retry/delete workflows
- Persisted embedding-call usage/cost audit
- Memory systems
- MCP integrations
- Voice and vision
- Desktop packaging

These capabilities should be added only in their planned phases.
