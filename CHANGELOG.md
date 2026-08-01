# Changelog

All notable changes to AI Agent Lab are documented in this file.

## [Unreleased]

### Added

- Added synchronous upload-to-vector ingestion that composes parsing, cleaning,
  Chunking, configured batch Embedding, Qdrant collection validation, and
  waited point upsert behind an independently tested pipeline boundary.
- Persisted canonical Chunk UUID point IDs and final Document embedding states;
  expected Provider/VectorStore failures retain safe failed records without
  partial vector IDs.
- Added the formal Document ingestion operations guide and Plan 3 M3 review,
  with Mock API end-to-end coverage and a cleaned real temporary-Qdrant smoke.
- Added a vendor-neutral asynchronous VectorStore contract with validated
  collection, point, query, result, and safe error boundaries.
- Added a Qdrant 1.15.x adapter and lazy collection/timeout configuration for
  COSINE collection create/check, waited vector upsert, Knowledge-Base-filtered
  search, and ownership-scoped Document vector deletion.
- Added a strict Chunk payload builder with canonical Knowledge Base, Document,
  and Chunk UUIDs plus filename, index, content, heading/page provenance, and
  nested JSON-safe source metadata for later Retriever results.
- Added an OpenAI-compatible Embedding adapter with batched `/embeddings`
  requests, query embedding, response-index ordering, actual model/token usage,
  and strict configured-dimension validation.
- Added independent lazy Embedding Settings and initialization with masked
  credentials, bounded dimensions/timeouts, safe HTTP/network/response errors,
  and mock-only Provider verification.
- Added the formal Embedding Provider operations guide covering configuration,
  model/dimension invariants, batching, errors, cost, privacy, and current
  vector-ingestion limitations.
- Added a vendor-neutral asynchronous `EmbeddingProvider` contract with
  immutable validated batch vectors, model identity, token usage, and separate
  text/query methods.
- Added an ordered runtime `EmbeddingProviderRegistry` that selects instances
  by exact configured name and reports safe duplicate or missing registrations.
- Added pure text cleaning with stable newline/blank-line normalization,
  bounded invisible-character removal, Markdown heading remapping, and
  independent PDF page preservation.
- Added configurable naive Chunking with paragraph/line boundary preference,
  bounded overlap, ordered indices, deterministic token estimates, and
  Markdown heading/PDF page provenance.
- Added synchronous parser/Cleaner/Chunker orchestration to Document upload:
  successful requests persist `DocumentChunk` rows, expected content failures
  persist safe visible lifecycle states, and infrastructure failures roll back
  database rows and promoted files.
- Added independent Markdown, TXT, and text-layer PDF parsers with a shared
  immutable result contract, heading/code-block metadata, deterministic
  UTF-8/UTF-16 BOM decoding, ordered PDF page provenance, and a readable
  scanned-PDF/OCR limitation.
- Added bounded `pypdf` support for text-layer PDF extraction without OCR,
  layout recovery, table reconstruction, or image interpretation.
- Added controlled multipart Document upload for `.md`, `.txt`, and `.pdf`
  files with bounded streaming, UUID-owned relative paths, 20 MiB and
  50-document defaults, SHA-256 validation, same-Knowledge-Base duplicate
  rejection, safe upload errors, and rollback file cleanup.
- Added `python-multipart` as a runtime dependency and explicit setuptools
  package discovery so the backend editable install includes only `app*`.
- Started Plan 3 from the published `v0.2.1` baseline with a pinned local
  Qdrant Compose service, named vector-data volume, backend `QDRANT_URL`
  setting, disabled Qdrant telemetry, and explicit `knowledge/` / `rag/`
  package boundaries.
- Added focused foundation tests and Qdrant startup/health instructions while
  preserving SQLite as the primary business and audit database.
- Added `KnowledgeBase`, `Document`, `DocumentChunk`, and `RagQuery` ORM and
  schema contracts with ownership, lifecycle, hash, metadata, vector, and query
  audit fields. Alembic revision `20260726_0005` creates the four SQLite tables
  with composite ownership and answer-message consistency constraints.
- Added a service-owned Knowledge Base metadata CRUD API with partial updates,
  deterministic listing, safe not-found responses, request-scoped
  commit/rollback, focused temporary-SQLite coverage, and the formal M1 data
  model/API reference.

### Security And Reliability

- Added request-transaction async rollback callbacks so a SQLite commit failure
  after Qdrant upsert best-effort deletes the Document vectors before the owned
  Qdrant client is closed; callback failures cannot mask the original error.
- Provider and VectorStore initialization failures now return stable safe HTTP
  503 errors before a Document/file is created, while runtime ingestion failures
  persist fixed messages without copying content, vectors, credentials, URLs,
  response bodies, or internal diagnostics.
- VectorStore operations fail closed on collection dimension/distance/shape
  mismatch, reject non-finite or wrong-dimension vectors and malformed payloads,
  suppress Qdrant exception causes, and never copy remote diagnostics into safe
  application errors.
- Qdrant search and deletion apply mandatory ownership filters; the local live
  acceptance used and removed a random temporary collection without touching
  existing collections.
- Bound the local Qdrant port to `127.0.0.1` and added configurable limits for
  PDF pages, extracted characters, Markdown structures, and per-Document chunks.
- Enforced exact canonical stored paths, retained storage-root symlink/reparse
  evidence until validation, bounded persisted headings, and preserved fenced
  Markdown blank lines while remapping structure line metadata.
- Removed duplicated code content from Markdown metadata and converted
  processing-limit failures into fixed safe Document lifecycle errors without
  partial chunk persistence.
- Added Alembic revision `20260801_0006` with fail-closed historical duplicate
  detection, same-Knowledge-Base hash uniqueness, Knowledge Base Document
  deletion restriction, and safe answer-Message `SET NULL` behavior.
- Made non-empty Knowledge Base deletion a stable HTTP 409 that preserves
  metadata and controlled files, and normalized only the Document hash unique
  race to the existing safe duplicate response.

## [0.2.1] - 2026-07-20

### Security And Reliability

- Enforced standard JSON and a 64 KiB UTF-8 limit for Tool arguments, plus a
  4096-character path schema limit for the built-in file Tools.
- Expanded private-key filename/container filtering, rejected recognized
  private-key content under arbitrary names, and prohibited user-supplied
  symlink or Windows reparse-point traversal.
- Bounded `list_dir` enumeration to `max_entries + 1` children per visited
  directory instead of materializing an unbounded directory.
- Enforced deny-by-default Agent dispatch: only `read_only` Tools execute, and
  unknown, invalid, oversized, or blocked call arguments are redacted before
  persistence.
- Defined `max_steps` as an atomic ToolCall execution budget, added a
  configurable whole-run timeout, and persisted one-based per-run unique
  `ToolCall.sequence_index` values through a backward-compatible migration.
- Added an optional `MODEL_REGISTRY_PATH` workflow with an ignored local file
  and a tracked secret-free Tool-capable example; the default Registry remains
  `supports_tools=false`.
- Made synchronous Agent results recoverable after leaving the page by storing
  only the run UUID in tab-scoped session storage; explicit run URLs still take
  priority and stale responses still cannot rewrite the Chat URL.
- Corrected ToolCall UI labels, summarized large argument payloads, and added
  mounted jsdom coverage for submit, restore, leave/reopen, structured failure,
  transport failure, and model-load failure flows.
- Synchronized backend, OpenAPI, frontend, lockfile, and documentation metadata
  to `0.2.1` without moving or recreating the published `v0.2.0` tag.

### Known Limitations

- Agent execution remains synchronous/non-streaming and sequential, with no run
  list, polling, cancel/resume/retry, or parallel Tool execution.
- Provider decisions are not strictly replayable and Agent calls are not linked
  to `LLMCall` usage/cost or later-Plan AgentStep/Trace records.
- Verification remains Mock-only; it does not prove live Provider Tool
  capability, and `web_fetch` remains deferred with no executable surface.

## [0.2.0] - 2026-07-19

### Added

- Added Provider-neutral assistant Tool Call and Tool observation messages with exact OpenAI-compatible serialization.
- Added a backend-only Simple Agent service for direct answers or a bounded non-streaming loop with 1～10 Provider decisions and a default of 3.
- Added per-Tool timeout enforcement, ordered multi-round observations, and bounded Provider observation JSON without truncating persisted ToolResult data.
- Added structured persisted Agent failures for maximum steps, Provider failures, invalid Provider results, and missing final text.
- Added AgentRun and ToolCall execution persistence with safe Tool failure observations, correlated results, timeout status, and timing metadata.
- Added validated Agent API schemas plus synchronous create, AgentRun query, and ToolCall query endpoints under `/api/v1/agents/runs`.
- Added persistent HTTP 201 responses for structured failed Agent runs and Provider-independent history queries with safe 404/error envelopes.
- Added a dedicated responsive Agent workspace with typed Agent API wrappers, tools-capable model filtering, and Chat/Agent sidebar navigation.
- Added bounded ToolCall cards and timeline states for arguments, status, latency, result summaries, safe errors, and traceable AgentRun/Conversation/Provider/database IDs.
- Added URL-backed AgentRun restoration plus mocked desktop/mobile acceptance for completed, failed, loading, no-model, transport-error, and reload states.
- Added regression coverage that locks `web_fetch` to its documented deferral boundary with no module, export, Registry schema, dependency, API, UI, or network implementation.
- Added sanitized desktop/mobile Agent ToolCall release-candidate screenshots and a consolidated pre-tag Plan 2 boundary document.

### Fixed

- Prevented `list_dir` from following Windows junctions and other reparse points outside the workspace, and corrected exact-limit truncation metadata.
- Blocked common credential files and directories such as `.npmrc`, `.netrc`, `.git-credentials`, `.aws`, `.kube`, and cloud credential JSON files from read-only tools.
- Made registered Tool definitions immutable and required Provider-exported parameter schemas to have a JSON-serializable object root.
- Enforced that an AgentRun's optional user Message belongs to the same Conversation through an additive Alembic migration.
- Rejected non-finite Tool timeouts, cross-round duplicate Tool Call IDs, and oversized escaped observation envelopes before they can break an Agent transaction.
- Prevented a late Agent response from updating state or rewriting the URL after the user leaves the Agent workspace.
- Rejected non-finite Tool argument values as non-standard JSON and extended the documented `.env*` path boundary to `.envrc` across shared policy and builtin Tools.
- Aligned backend package, FastAPI OpenAPI, frontend package, and lockfile release metadata with `0.2.0`.

### Known Limitations

- Plan 2 release verification uses Mock Providers and local synthetic browser data; it does not prove live Provider Tool capability, and the tracked example model remains `supports_tools=false`.
- Agent execution and Tool Calling are synchronous/non-streaming. There is no AgentRun list, polling, cancel/resume/retry, parallel Tool execution, or persisted cancelled-run policy.
- ToolCall has no strict persisted step sequence, and Agent Provider calls are not linked to `LLMCall` usage/cost rows.
- `web_fetch` remains explicitly deferred with no executable surface.

## [0.1.0] - 2026-07-13

### Added

- FastAPI and React/Vite project foundations with service-specific environment examples.
- SQLite/SQLAlchemy/Alembic persistence for conversations, messages, and successful LLM calls.
- Vendor-neutral LLM contracts, an OpenAI-compatible adapter, and a strict Model Registry.
- Non-streaming and SSE Chat with model selection, recent conversations, and refresh recovery.
- Successful-call token, estimated cost, and Provider latency persistence.
- Safe request IDs, classified HTTP/SSE errors, redacted request/model-call logs, and mocked regression coverage.
- Responsive Chat workspace states and sanitized desktop/mobile release screenshots.

### Security And Reliability

- Provider, database, validation, and unexpected failures return fixed readable responses without exposing credentials, SQL, upstream bodies, or complete messages.
- Failed and cancelled turns roll back instead of leaving partial persisted conversation state.
- Terminal SSE errors release the frontend response reader, and stale conversation-list refreshes cannot overwrite newer state.
- Release verification uses mocks and a fresh temporary database; it does not call a real Provider or modify the user's local database.

### Known Limitations

- Live DeepSeek/OpenRouter connectivity is configuration-supported but not exercised by release verification.
- Token, estimated cost, and latency are persisted on `LLMCall` but are not displayed in the frontend.
- Provider retries/fallback, persistent failed-call audit rows, and Plan 4 Trace are not implemented.
- SSE failures after response start use a terminal `event: error` frame on an HTTP 200 stream.
- `models.json` is not yet declared as wheel/sdist package data; the supported current workflow is an editable source install.
- Older ignored local SQLite databases can predate the current foreign-key indexes and are not automatically rebuilt.
- Conversation pagination/search/rename/delete and Markdown rendering are deferred.
