# Knowledge Base Design

## Scope

Plan 3 Milestone 1 establishes the persistence and management boundary for
Knowledge Bases. Through `P3-M4-S3`, the backend can create, list, read, update,
and delete Knowledge Base metadata, upload one validated Document through a
service-owned HTTP API, and synchronously parse, clean, and chunk Markdown,
TXT, or text-layer PDF through independent processing boundaries. It also
provides a vendor-neutral Embedding Provider/result contract, runtime Registry,
OpenAI-compatible adapter, Qdrant VectorStore, stable Chunk payload, the
document vector-ingestion pipeline, and an independent Top-K Retriever.

The first M2 batch stores `.md`, `.txt`, and `.pdf` bytes and creates the
initial Document row. The second adds pure parsers. The final M2 batch composes
the Parser, Cleaner, and Chunker in the upload transaction, persists
`DocumentChunk` rows, and exposes final parse/chunk states. M3 S1～S6 add the
Embedding abstraction, validated batch output, exact-name Provider selection,
concrete protocol adapter, and lazy initialization. M3 S7～S9 add the
VectorStore abstraction, Qdrant adapter, and stable Chunk payload. M3 S10～S12
complete the upload-to-parse-to-clean-to-chunk-to-embed-to-upsert flow, persist
each Qdrant point ID on its owning Chunk, and transition the Document embedding
state. M4 S1～S3 add query embedding, Knowledge-Base-filtered Top-K search, and a
stable source result. RAG answers and the frontend Knowledge Base workspace
remain assigned to later Plan 3 steps.

## Storage Responsibilities

SQLite remains the default and long-term supported primary database. It owns:

- Knowledge Base configuration metadata;
- Document identity, file metadata, and ingestion lifecycle state;
- Document Chunk text, source metadata, and persisted vector identifiers;
- RAG query audit metadata and retrieved-chunk snapshots.

Qdrant is Plan 3's vector-storage service. Its VectorStore runtime can
create/check a COSINE collection, upsert points, search under a Knowledge Base
filter, and delete under Knowledge Base plus Document ownership filters. The
ingestion pipeline selects the configured collection and stores each returned
point UUID in `document_chunks.vector_id`; Qdrant still owns only vectors and
search payloads, while SQLite owns lifecycle and audit state.

Deleting a Knowledge Base that still owns any Document returns HTTP 409. The
database RESTRICT constraint is the final concurrency gate, and the service
preserves the Knowledge Base, Documents, chunks, and locally uploaded bytes.
Deleting an empty Knowledge Base may still cascade its independent RagQuery
audit rows. M2 does not contact Qdrant or delete a Qdrant collection; Document
deletion and local-file lifecycle coordination remain later-step limitations.

## Ownership Graph

```text
KnowledgeBase
├── Document
│   └── DocumentChunk
└── RagQuery
    ├── optional Conversation
    └── optional answer Message from that Conversation
```

All identities are UUID v4 values. SQLite stores timezone-naive UTC datetimes
because it does not preserve timezone information consistently.

## KnowledgeBase

The `knowledge_bases` table owns:

| Field | Contract |
|---|---|
| `id` | UUID primary key |
| `name` | Required, trimmed, non-blank, at most 255 characters |
| `description` | Optional text |
| `embedding_provider` | Optional provider name, at most 100 characters |
| `embedding_model` | Optional model name, at most 255 characters |
| `vector_store` | Required storage name; defaults to `qdrant` |
| `vector_collection_name` | Optional collection name, at most 255 characters |
| `created_at` | Creation time in UTC |
| `updated_at` | Last metadata update time in UTC |

`ck_knowledge_bases_name_not_blank` enforces the non-blank name rule at the
database boundary.

## Document Lifecycle

The `documents` table belongs to one Knowledge Base and records:

| Field group | Fields and constraints |
|---|---|
| Identity and ownership | `id`, required `knowledge_base_id` |
| File identity | `filename`, `original_filename`, `file_path` |
| File validation bridge | `file_type` in `md`, `txt`, `pdf`; non-negative `file_size`; 64-character `file_hash` |
| Parse lifecycle | `parse_status`: `uploaded`, `parsing`, `parsed`, `failed` |
| Chunk lifecycle | `chunk_status`: `pending`, `chunking`, `chunked`, `failed` |
| Embedding lifecycle | `embedding_status`: `pending`, `embedding`, `ready`, `failed` |
| Diagnostics and source metadata | optional `error_message`, `metadata_json` |
| Audit time | `created_at`, `updated_at` |

Document upload creates the row as `uploaded` / `pending` / `pending`, then
processes it within the request transaction. Full success returns `parsed` /
`chunked` / `ready`. Expected parser failures return `failed` / `failed` /
`failed`; text that is empty after cleaning returns `parsed` / `failed` /
`failed`. Embedding Provider or VectorStore operation failures preserve the
parsed chunks and return `parsed` / `chunked` / `failed` with a fixed safe
diagnostic and no persisted `vector_id` values.

The unique `(knowledge_base_id, file_hash)` pair is the final same-Knowledge-
Base duplicate gate. Different Knowledge Bases may own the same hash. The
Document foreign key uses RESTRICT so a non-empty Knowledge Base cannot be
deleted. The unique `(id, knowledge_base_id)` pair supports a composite
ownership check for chunks.

## Embedding Provider Boundary

`app.providers.embedding` owns the vendor-neutral runtime boundary introduced
by M3 S1～S6. `EmbeddingProvider` exposes asynchronous `embed_texts()` and
`embed_query()` methods and a normalized Provider name. `EmbeddingResult`
returns ordered same-dimension finite vectors, the actual model identity, and
immutable batch-level `EmbeddingUsage`; malformed empty, mixed-dimension, or
non-finite output is rejected before any future Vector Store call.

`EmbeddingProviderRegistry` stores Provider instances in registration order and
selects one by the exact caller-owned configuration name. Duplicate and missing
names fail explicitly. It still does not read Settings or initialize API
credentials.

`OpenAICompatibleEmbeddingProvider` is the first concrete adapter. It sends a
single float-encoded batch/query request to `/embeddings`, orders the response
by explicit indexes, preserves returned model/usage, and rejects malformed or
wrong-dimension vectors. The factory reads independent lazy Embedding Settings
and unwraps the masked key only during initialization. Safe exceptions do not
copy remote bodies, source text, vector values, or credentials. Document state
updates, Qdrant calls, persisted vector IDs, and ingestion orchestration remain
outside this Provider boundary and are composed by `DocumentIngestionService`
plus `app.rag.ingestion_pipeline`. VectorStore calls still belong to the
boundary below.

## VectorStore And Qdrant Payload Boundary

`app.rag.vectorstores` owns the asynchronous Naive RAG storage boundary added
by M3 S7～S9. `VectorStore` exposes collection ensure, non-empty point upsert,
Knowledge Base search, ownership-scoped Document delete, and client close.
Inputs and results use UUIDs, finite non-empty vectors, a 1～100 search limit,
finite scores, and immutable Pydantic contracts. The concrete
`QdrantVectorStore` uses the official client pinned to Qdrant 1.15.x.

The default configuration is:

| Setting | Default | Contract |
|---|---:|---|
| `QDRANT_URL` | `http://localhost:6333` | HTTP(S) endpoint without embedded credentials, query, or fragment |
| `QDRANT_COLLECTION_NAME` | `ai_agent_lab_chunks` | 1～255 ASCII letters, digits, `.`, `_`, or `-` |
| `QDRANT_TIMEOUT_SECONDS` | `10` | Integer from 1 through 300 seconds |

Initialization remains lazy. The factory uses the configured Embedding
dimension and permits a Knowledge Base caller to override the default
collection name. `ensure_collection()` creates one default COSINE dense-vector
collection or checks the existing size/distance. Named vectors, different
dimensions, and different distances fail closed; the adapter never rebuilds or
deletes an incompatible existing collection.

Every Chunk payload contains:

```text
knowledge_base_id, document_id, chunk_id, filename, chunk_index,
content, heading, page_number, metadata
```

UUIDs serialize as canonical lowercase strings. `metadata` stays nested and
must be a JSON-safe object with string keys and finite numbers. The builder
checks that the Document and Chunk share both Document and Knowledge Base
ownership, copies mutable metadata, and preserves the fields consumed by M4's
`RetrievalResult`.

Qdrant search always applies an exact `knowledge_base_id` filter and returns
payload without vectors. Document deletion applies both `knowledge_base_id` and
`document_id`, preventing a wrong identifier from deleting another Knowledge
Base's points. SDK and network failures become fixed safe operation errors;
malformed collection/search responses become safe response errors. Neither
path copies endpoint diagnostics, payload content, vectors, or exception causes
into application errors.

## Naive Retriever Boundary

`app.rag.retriever.Retriever` is the independent orchestration boundary added
by M4 S1～S3. It receives an `EmbeddingProvider` and `VectorStore` at
construction; it does not read Settings, use a database Session, choose a
Provider/collection, or own client lifecycle. Its asynchronous `retrieve()`
accepts a query, Knowledge Base UUID, `top_k` defaulting to 5, and an optional
finite score threshold.

All input is checked before a potential Provider call. Top-K is a strict
non-boolean integer from 1 through 100. A valid query is sent unchanged to
`embed_query()`. The result must contain exactly one vector whose dimension
matches the VectorStore. The Retriever then creates one `VectorSearchQuery`
and preserves the returned similarity order without filtering metadata,
deduplicating, merging, or reranking.

`RetrievalResult` is an immutable Pydantic source value containing:

```text
knowledge_base_id, document_id, chunk_id, filename, chunk_index,
content, score, heading, page_number, metadata
```

UUIDs stay strongly typed and serialize canonically. Nested metadata is copied
before exposure. The Retriever rejects an invalid result type, a cross-
Knowledge-Base payload, more results than Top-K, or a result below the requested
threshold as one fixed safe response error; it never returns partial output.
Provider and VectorStore errors keep their existing boundary categories.

## Controlled Document Storage

`DocumentStorage` owns local file I/O behind a framework-neutral async stream
boundary. Its defaults are:

| Setting | Default | Contract |
|---|---:|---|
| `DOCUMENT_STORAGE_ROOT` | `./uploads` | Relative values resolve below the backend root |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `20_971_520` | 20 MiB per non-empty file |
| `DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE` | `50` | Checked before the upload stream is read |
| `DOCUMENT_MAX_PDF_PAGES` | `500` | Configurable up to 10,000 pages |
| `DOCUMENT_MAX_EXTRACTED_CHARACTERS` | `10_000_000` | Configurable up to 100,000,000 characters |
| `DOCUMENT_MAX_MARKDOWN_STRUCTURES` | `20_000` | Combined heading/code-block metadata cap; configurable up to 100,000 |
| `DOCUMENT_MAX_CHUNKS` | `10_000` | Per-Document draft cap; configurable up to 100,000 |
| `RAG_CHUNK_SIZE` | `1_000` | 100 through 10,000 characters |
| `RAG_CHUNK_OVERLAP` | `150` | 0 through 2,000 and smaller than chunk size |

The runtime layout is:

```text
backend/uploads/
├── .staging/
│   └── <random>.part
└── <knowledge_base_uuid>/
    └── <document_uuid>.<md|txt|pdf>
```

Client filenames are display metadata only. Path prefixes are removed, control
characters and invalid names are rejected, and only `.md`, `.txt`, and `.pdf`
suffixes are accepted case-insensitively. The final name and path use generated
UUIDs, so client input cannot overwrite an existing upload. SQLite stores only
the relative POSIX path. Reads and cleanup require its exact lowercase
canonical form; absolute paths, backslashes or mixed separators, dot segments,
UUID case variants, suffix case variants, and ownership/type mismatches fail
before file access. The configured root remains lexical until storage validates
symlink/reparse evidence.

Staging reads at most 64 KiB per request, enforces the configured byte limit
before writing an overflowing chunk, and calculates a lowercase SHA-256 while
streaming. The same hash is rejected within one Knowledge Base and allowed in a
different Knowledge Base. The service precheck gives a readable early failure;
the database unique constraint closes concurrent same-hash races, which the
service normalizes to the same safe duplicate response.

The request database dependency remains the commit/rollback owner. A promoted
file is registered on the Session before the Document flush. Successful commit
forgets that pending cleanup; rollback removes the new file. Staging files are
removed on normal validation and storage failures. A hard process termination
can still leave staging or unreferenced final files, and orphan scanning is
deferred.

## Document Parser Boundary

`app.rag.parsers` contains no FastAPI, SQLAlchemy, service, Provider, Qdrant, or
upload orchestration dependencies. A caller supplies an already authorized
file path and Document UUID. Every parser returns an immutable
`ParsedDocument` with complete extracted `text`, small JSON-compatible
`metadata`, and optional ordered `ParsedPage` values.

Markdown is decoded as strict UTF-8 with optional BOM removal. Its original
markup is preserved while a fence-aware state machine reports ATX/Setext
headings and backtick/tilde code blocks. Heading-like content inside a code
fence is not misclassified. Code-block metadata stores only language and
one-based start/end lines, not a second copy of the full code content.

TXT decoding is deterministic: UTF-8 BOM, UTF-16 LE/BE BOM, or strict UTF-8.
There is no locale-dependent or probabilistic encoding fallback, and invalid
bytes fail safely instead of being silently replaced.

Text-layer PDFs use the bounded `pypdf` dependency. Extraction preserves
one-based page order and joins page text with a stable double-newline boundary.
A PDF with at least one text-bearing page succeeds even when another page is
blank. A document with no extracted text returns a readable limitation stating
that scanned/image-only PDF requires OCR, which Plan 3 does not implement.
Malformed or unreadable files return a generic safe parse error without paths
or third-party diagnostics. Parser work is bounded by the shared page,
extracted-character, and Markdown-structure limits.

## Cleaner, Chunker, And Ingestion

`app.rag.text_cleaner` and `app.rag.chunker` are pure and database-independent.
The Cleaner returns a new immutable parser result. It normalizes CRLF/CR to LF,
removes C0/C1 controls except tab plus a small denylist of layout-unsafe format
characters, collapses whitespace-only blank-line runs, trims outer blank lines,
updates Markdown heading and code-block line numbers, and cleans PDF pages
independently. Blank-line runs inside a validated fenced-code range are
preserved exactly; only ordinary Markdown blank runs are collapsed.

The Chunker uses the configured character window and overlap. When a hard
window boundary is not the end of content, it prefers the last paragraph
boundary in the latter half of the window, then a line boundary, then the hard
boundary. Progress is monotonic. Markdown chunks record the latest heading
visible at their start; PDF chunks never cross pages. Each draft records
zero-based `chunk_index`, exact character count, source format and offsets, plus
optional heading/page provenance. `token_count` is the deterministic estimate
`max(1, ceil(UTF-8 bytes / 4))`, not a model tokenizer result.
The generator stops before appending chunk `max_chunks + 1`, and persisted
headings are capped at the `DocumentChunk.heading` length of 512 characters.

`DocumentIngestionService` owns the composition. It resolves the stored path
against the expected Knowledge Base UUID, Document UUID, and suffix while
rejecting malformed ownership, symlink, and reparse paths. It dispatches the
existing parser, cleans, chunks, writes ordered `DocumentChunk` rows, marks the
Document as embedding, then invokes the vector-ingestion boundary without
committing. That boundary checks Chunk ownership/order, ensures the collection,
embeds all Chunk content as one bounded batch, builds traceable payloads, and
upserts points whose UUIDs equal the owning Chunk UUIDs.

Expected parser/content errors persist safe Document states and no chunks.
Expected Provider/VectorStore errors preserve the parsed chunks, clear all
vector IDs, and persist a safe embedding failure. Storage, SQLAlchemy, and
unexpected programming errors propagate so the request transaction rolls back
the Document, chunks, and promoted file. If an upsert succeeded before that
rollback, a request-scoped compensation callback deletes the Document's points.

## DocumentChunk Integrity

The `document_chunks` table records:

- `id`, `document_id`, and repeated `knowledge_base_id`;
- zero-based, non-negative `chunk_index`;
- `content`, non-negative `token_count`, and non-negative `char_count`;
- optional `heading` and positive `page_number`;
- `metadata_json` source metadata;
- optional `vector_id`;
- `created_at`.

`fk_document_chunks_document_knowledge_base_documents` requires the Document
and repeated Knowledge Base identity to match. This prevents a chunk from being
assigned to a different Knowledge Base than its parent Document.
`uq_document_chunks_document_id_chunk_index` keeps chunk order unique within a
Document. Deleting the parent Document cascades to its chunks.

On successful ingestion, every Chunk stores the canonical Qdrant point UUID in
`vector_id`; that UUID is intentionally the same as the Chunk UUID. Failed
vector ingestion never leaves partial SQLite vector identifiers.

## RagQuery Bridge

The `rag_queries` table is the future Naive RAG audit bridge. It records:

- required `knowledge_base_id` and original `query`;
- `retrieved_chunks_json`, preserving the selected source snapshot;
- optional `conversation_id` and `answer_message_id`;
- optional non-negative `latency_ms`;
- `created_at`.

An answer Message may only be linked when a Conversation is present. The
composite answer-message foreign key prevents linking an answer from a different
Conversation. Deleting an answer Message clears the optional reference and
preserves the query; deleting its Conversation or Knowledge Base cascades to the
query.

The standalone Retriever does not write audit rows. Retrieval/answer HTTP
workflows and `rag_queries` persistence remain assigned to M4 S4+.

## Knowledge Base Service

`KnowledgeBaseService` owns the five metadata operations:

| Method | Behavior |
|---|---|
| `create_knowledge_base` | Adds and flushes one validated Knowledge Base |
| `list_knowledge_bases` | Orders by `created_at` descending, then `id` ascending |
| `get_knowledge_base` | Returns one row or raises `KnowledgeBaseNotFoundError` |
| `update_knowledge_base` | Changes only supplied fields and advances `updated_at` |
| `delete_knowledge_base` | Deletes and flushes only an empty row; non-empty returns `KnowledgeBaseNotEmptyError` |

The service flushes but does not commit. The request-scoped database dependency
owns commit, rollback, and session close, keeping transaction behavior uniform
across API routes.

## HTTP API

All routes use the plural kebab-case prefix `/api/v1/knowledge-bases`.

| Method | Path | Success | Response |
|---|---|---|---|
| `POST` | `/api/v1/knowledge-bases` | `201` | `KnowledgeBaseRead` |
| `GET` | `/api/v1/knowledge-bases` | `200` | Ordered list of `KnowledgeBaseRead` |
| `GET` | `/api/v1/knowledge-bases/{knowledge_base_id}` | `200` | `KnowledgeBaseRead` |
| `PATCH` | `/api/v1/knowledge-bases/{knowledge_base_id}` | `200` | Updated `KnowledgeBaseRead` |
| `DELETE` | `/api/v1/knowledge-bases/{knowledge_base_id}` | `204` | Empty body |
| `POST` | `/api/v1/knowledge-bases/{knowledge_base_id}/documents` | `201` | Final synchronous `DocumentRead` |

`PATCH` is a partial update. At least one field must be supplied. The mutable
fields are `name`, `description`, `embedding_provider`, `embedding_model`,
`vector_store`, and `vector_collection_name`. Explicit `null` clears nullable
fields; `name` and `vector_store` cannot be `null`. Unknown fields and blank
bounded names fail schema validation.

The route layer validates input, calls the service, and shapes the response. It
does not own persistence logic.

Deleting a Knowledge Base that still owns a Document returns HTTP `409` with
`knowledge_base_not_empty` and the safe message `Delete documents before
deleting the knowledge base`.

The Document upload request is `multipart/form-data` with one required `file`
field. Upload now runs the complete vector-ingestion pipeline. There are still
no Document list, detail, chunk-query, retry, or delete routes through M4 S3.

## Error And Transaction Behavior

An unknown UUID on detail, update, or delete returns:

```json
{
  "error": {
    "code": "knowledge_base_not_found",
    "message": "Knowledge base not found",
    "request_id": "..."
  }
}
```

The response is HTTP `404` and does not echo the missing UUID. Request
validation failures use the shared safe `422` response. SQLAlchemy failures use
the shared safe `503 database_error` response.

Document upload errors use stable responses without filenames, file content,
hashes, absolute paths, or internal diagnostics:

| HTTP | Code | Meaning |
|---:|---|---|
| `400` | `document_file_invalid` | Missing/invalid filename or empty file |
| `413` | `document_too_large` | Configured byte limit exceeded |
| `415` | `document_type_unsupported` | Suffix is not `.md`, `.txt`, or `.pdf` |
| `409` | `document_duplicate` | Same hash exists in this Knowledge Base |
| `409` | `knowledge_base_document_limit_reached` | Knowledge Base reached its configured count |
| `503` | `document_storage_error` | Controlled staging/promotion/cleanup failed |
| `503` | `embedding_provider_unavailable` | Embedding Provider configuration or initialization failed before upload |
| `503` | `vector_store_unavailable` | VectorStore initialization failed before upload |

Processing-limit failures remain successful HTTP 201 Document resources. They
use the fixed message `Document exceeds the processing limit.`, set parse/chunk
failure states according to the phase, and persist no partial chunk rows.

Expected parse/content failures are successful HTTP 201 resource creation, not
transport failures. Invalid encoded or unreadable content persists
`parse_status=failed` and `chunk_status=failed`. Content that is empty after
cleaning persists `parse_status=parsed` and `chunk_status=failed`. Both expose a
bounded safe `error_message` and create no chunks.

Embedding or vector-operation failures are also successful HTTP 201 Document
resources because the resource and parsed chunks remain inspectable. They set
`embedding_status=failed`, expose only `Document embedding failed.` or
`Document vector storage failed.`, and persist no vector IDs. Initialization
errors happen before file streaming and use the safe 503 responses above.

Successful requests commit after the route returns. Any exception rolls the
request transaction back before the session closes. Request-scoped asynchronous
callbacks compensate Qdrant writes on rollback and close the Qdrant client at
session finalization. Compensation is best-effort: an abrupt process crash or a
Qdrant cleanup outage can still leave orphan points, which a later maintenance
workflow must reconcile. Tests use newly created temporary SQLite databases and
never read or modify the user database.

## Verification

The S7～S8 TDD checkpoints are:

- schema RED: `KnowledgeBaseUpdate` import failed before implementation;
- schema GREEN: `35 passed`;
- service RED: service/domain-error import failed before implementation;
- schema and service GREEN: `41 passed`;
- API RED: `13 failed, 1 warning` because the routes and error mapping did not
  yet exist;
- schema, service, and API GREEN: `54 passed, 1 warning`.

The warning is the existing Starlette `TestClient` / httpx deprecation warning.
Fresh M1 verification then reached:

- focused schema/model/migration/service/API: `76 passed, 1 warning`;
- complete backend: `583 passed, 1 warning`;
- dependency integrity: `No broken requirements found`;
- frontend regression: `18` files / `90` tests, typecheck, and production build
  with `1813` transformed modules;
- fresh temporary-SQLite Alembic head `20260726_0005`, checked at head with no
  new upgrade operations;
- `86` Markdown files and `69` local links/images with `0` missing targets.

The M2 S1～S3 TDD checkpoints are:

- storage/config RED: upload errors and storage exports were absent;
- storage/config GREEN: `34 passed`;
- service RED: `DocumentService` was absent;
- storage/service GREEN: `26 passed`;
- adjacent config/model/schema/service regression: `97 passed`;
- API RED: `20 failed, 1 warning` because the route and mappings were absent;
- API GREEN: `20 passed, 1 warning`;
- focused M1 plus upload regression: `136 passed, 1 warning`.

The M2 S4～S6 parser TDD checkpoints are:

- Markdown RED: parser package missing at collection;
- Markdown GREEN: `4 passed`;
- TXT RED: `parse_txt` missing at collection;
- Markdown/TXT GREEN: `10 passed`;
- PDF RED: `parse_pdf` missing at collection;
- all three Parser GREEN after the UTF-32 BOM regression fix: `16 passed`;
- parser plus adjacent upload/model/schema regression:
  `117 passed, 1 warning`.

The M2 S7～S9 processing TDD checkpoints are:

- Cleaner RED: `clean_parsed_document` was absent at collection; GREEN:
  `4 passed`;
- Settings RED: six missing-bound/relationship assertions failed; GREEN:
  `22 passed`;
- Chunker RED: chunk contracts were absent at collection; Cleaner/config/
  Chunker GREEN: `40 passed`;
- stored-path resolver RED: `12 failed, 18 passed`; GREEN: `30 passed`;
- ingestion success RED: `DocumentIngestionService` was absent; success GREEN:
  `3 passed`;
- expected-content RED: three parser/empty-content exceptions escaped while
  three success cases passed; precise failure handling GREEN: `6 passed`;
- upload integration RED: eight new lifecycle/chunk assertions failed while 24
  existing cases passed; GREEN: `32 passed, 1 warning`;
- complete focused M2 regression: `179 passed, 1 warning`;
- final infrastructure-boundary/API regression: `30 passed, 1 warning`.

Fresh completion verification reached:

- complete backend: `698 passed, 1 warning`;
- dependency integrity: `No broken requirements found`;
- frontend regression: `18` files / `90` tests, typecheck, and production build
  with `1813` transformed modules;
- fresh temporary-SQLite Alembic head `20260726_0005`, checked at head with no
  new upgrade operations and verified temporary-directory cleanup;
- `92` Markdown files and `69` local links/images with zero read errors or
  missing targets.

The 2026-08-01 M1/M2 audit-remediation verification reached:

- focused backend: `208 passed, 1 warning`;
- complete backend: `735 passed, 1 warning`;
- dependency integrity: `No broken requirements found`;
- fresh temporary-SQLite Alembic head `20260801_0006`, including check-heads,
  autogenerate check, downgrade to `20260726_0005`, and re-upgrade;
- frontend: `18` files / `90` tests, typecheck, and production build with
  `1813` transformed modules;
- `95` Markdown files, `69` local links/images, and zero missing targets;
- Compose syntax passed; current Docker runtime health was not checked because
  the local daemon was unavailable.

The M3 S1～S3 Embedding Provider verification reached:

- base/result RED at missing package import; GREEN: `17 passed`;
- Registry RED at missing exports; adjacent Provider GREEN: `58 passed`;
- strict-number self-review RED: `4 failed, 17 passed`; final Provider-adjacent
  GREEN: `62 passed`;
- focused backend: `303 passed, 1 warning`; complete backend:
  `765 passed, 1 warning`;
- dependency integrity: `No broken requirements found`;
- temporary-SQLite upgrade/current/check/downgrade/re-upgrade at head
  `20260801_0006`, followed by verified temporary-directory cleanup;
- frontend: `18` files / `90` tests, typecheck, and production build with
  `1813` transformed modules;
- live local `qdrant/qdrant:v1.15.4` on `127.0.0.1:6333` with
  `healthz check passed`;
- `97` Markdown files, `69` local links/images, and zero missing targets.

The M3 S4～S6 OpenAI-compatible Embedding verification reached:

- adapter/base RED at missing concrete exports; GREEN: `48 passed`;
- Settings/factory RED at missing factory module; GREEN: `52 passed`;
- Provider/LLM/config adjacent regression: `192 passed`;
- response-error safety review RED: `6 failed, 21 passed`; final adapter GREEN:
  `27 passed`;
- complete backend: `811 passed, 1 warning`; dependency integrity:
  `No broken requirements found`;
- temporary-SQLite upgrade/current/check/downgrade/re-upgrade at head
  `20260801_0006`, followed by verified temporary-directory cleanup;
- frontend: `18` files / `90` tests, typecheck, and production build with
  `1813` transformed modules;
- live local `qdrant/qdrant:v1.15.4` on `127.0.0.1:6333` with
  `healthz check passed`;
- `100` Markdown files, `75` valid local links/images, and zero missing
  targets; zero high-confidence secrets, executable later-Plan runtime, or
  tracked artifacts.

The M3 S7～S9 Qdrant VectorStore verification reached:

- contract/payload RED at missing package import; GREEN: `30 passed`;
- adapter/config RED at missing exports; SDK shape calibration GREEN:
  `107 passed`;
- traceability self-review RED: `2 failed, 42 passed`; write-status self-review
  RED: `4 failed, 21 passed`; final VectorStore/config focused:
  `113 passed`;
- complete backend: `880 passed, 1 warning`; dependency integrity:
  `No broken requirements found`;
- temporary-SQLite upgrade/current/check/downgrade/re-upgrade at head
  `20260801_0006`, followed by verified temporary-directory cleanup;
- frontend: `18` files / `90` tests, typecheck, and production build with
  `1813` transformed modules;
- live local Qdrant create/check, two-point upsert, two Knowledge Base filtered
  searches, ownership-scoped delete, post-delete isolation, and verified random
  temporary-collection cleanup;
- `102` Markdown files, `75` valid local links/images, and zero missing
  targets; zero high-confidence secrets, added private-key headers, executable
  later-Plan runtime, or tracked artifacts.

The M3 S10～S12 document vector-ingestion verification reached:

- pipeline RED at missing module and GREEN `8 passed`; callback/factory/error
  mapping GREEN `22 passed, 1 warning`; service/API RED
  `38 failed, 11 passed` and GREEN `49 passed, 1 warning`;
- focused backend `312 passed, 1 warning`; complete backend
  `900 passed, 1 warning`; dependency integrity `No broken requirements found`;
- temporary-SQLite upgrade/current/check/downgrade/re-upgrade at head
  `20260801_0006`, followed by verified temporary-directory cleanup;
- frontend `18` files / `90` tests, typecheck, and production build with
  `1813` transformed modules;
- live local Qdrant full ingestion using temporary SQLite/files and a Mock
  Embedding Provider: ready state, matching Chunk/point IDs, one search hit,
  ownership-scoped delete to zero hits, and verified random collection cleanup;
- `106` Markdown files, `84` valid local links/images, and zero missing targets;
  zero high-confidence secrets, private-key headers, executable later-Plan or
  network-Tool runtime, and tracked artifacts.

The M4 S1～S3 Naive Vector Retriever verification reached:

- `RetrievalResult` import RED, then schema/knowledge adjacent GREEN
  `46 passed`;
- Retriever module RED, then happy-path/contract GREEN `57 passed`;
- strict input error export RED, then Retriever GREEN `18 passed`;
- response error export RED, then Retriever GREEN `24 passed`;
- Codex self-review reproduced Top-K/threshold contract escape as
  `2 failed, 24 deselected`; an oversized integer threshold then reproduced an
  uncaught overflow as `1 failed, 5 passed, 21 deselected`. Both fixes are in
  final Retriever GREEN `27 passed`;
- Embedding/VectorStore/ingestion adjacent focused `169 passed`; complete
  backend `938 passed, 1 warning`; dependency integrity
  `No broken requirements found`;
- live local Qdrant with a deterministic Mock query embedding returned one
  correct Top-1 Chunk above threshold, preserved Knowledge Base isolation, and
  removed the random temporary collection; matching-prefix remainder was zero;
- temporary-SQLite migration round trip remained at head `20260801_0006` and
  its directory was removed; frontend typecheck, `18` files / `90` tests, and
  production build with `1813` transformed modules passed;
- `108` Markdown files, `84` valid local links/images, and zero missing targets;
  zero high-confidence secrets, private-key headers, executable later-Step or
  network-Tool runtime, and tracked artifacts.

The active Plan 3 execution table contains the security, scope, artifact, and
Git gates. No verification command read or modified `backend/ai_agent_lab.db`.

## Deferred Capabilities

The following remain outside completed Plan 3 through M4 S3:

- Document list, detail, chunk-query, delete, local-file deletion, and orphan
  recovery workflows;
- live Embedding service acceptance, automatic retry/splitting, persisted call
  audit/cost, and hard-crash orphan reconciliation;
- RAG Prompt, RAG query/chat runtime, audit writes, and Agent Tool integration;
- frontend Knowledge Base, upload, RAG Chat, and source display;
- Advanced RAG, Hybrid Search, Rerank, Evaluation, Memory, OCR, and multimodal
  capabilities.

See [Architecture](01-architecture.md) for the wider workspace boundaries.
