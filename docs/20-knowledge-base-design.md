# Knowledge Base Design

## Scope

Plan 3 Milestone 1 establishes the persistence and management boundary for
Knowledge Bases. Through `P3-M2-S6`, the backend can create, list, read, update,
and delete Knowledge Base metadata, upload one validated Document through a
service-owned HTTP API, and parse Markdown, TXT, or text-layer PDF through an
independent extraction boundary.

The first M2 batch stores `.md`, `.txt`, and `.pdf` bytes and creates the
initial Document row. The second adds pure parsers, but upload still does not
invoke them. The parsers do not clean or chunk content, update Document state,
create embeddings, connect a Qdrant client, retrieve sources, generate RAG
answers, or expose a frontend Knowledge Base workspace. Those capabilities
remain assigned to later Plan 3 steps.

## Storage Responsibilities

SQLite remains the default and long-term supported primary database. It owns:

- Knowledge Base configuration metadata;
- Document identity, file metadata, and ingestion lifecycle state;
- Document Chunk text, source metadata, and future vector identifiers;
- RAG query audit metadata and retrieved-chunk snapshots.

Qdrant is configured as Plan 3's vector-storage service, but the scope through
M2 S3 contains no Qdrant client or Vector Store runtime. The `vector_store`,
`vector_collection_name`, and `vector_id` fields are persistence bridges, not
evidence that a collection or vector has been created.

Deleting a Knowledge Base deletes its SQLite-owned metadata through database
cascades. Through M2 S3 it does not delete locally uploaded bytes, contact
Qdrant, or delete a Qdrant collection; local-file deletion coordination is a
documented later-step limitation.

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

Document upload now creates the initial `uploaded` / `pending` / `pending`
state. Parsing, cleaning, Chunking, and Embedding transitions remain deferred.

Deleting a Knowledge Base cascades to its Documents. The unique
`(id, knowledge_base_id)` pair supports a composite ownership check for chunks.

## Controlled Document Storage

`DocumentStorage` owns local file I/O behind a framework-neutral async stream
boundary. Its defaults are:

| Setting | Default | Contract |
|---|---:|---|
| `DOCUMENT_STORAGE_ROOT` | `./uploads` | Relative values resolve below the backend root |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `20_971_520` | 20 MiB per non-empty file |
| `DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE` | `50` | Checked before the upload stream is read |

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
the relative POSIX path.

Staging reads at most 64 KiB per request, enforces the configured byte limit
before writing an overflowing chunk, and calculates a lowercase SHA-256 while
streaming. The same hash is rejected within one Knowledge Base and allowed in a
different Knowledge Base. The service-level query matches the local-first
single-writer model; concurrent same-hash uploads remain an accepted limitation.

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
fence is not misclassified.

TXT decoding is deterministic: UTF-8 BOM, UTF-16 LE/BE BOM, or strict UTF-8.
There is no locale-dependent or probabilistic encoding fallback, and invalid
bytes fail safely instead of being silently replaced.

Text-layer PDFs use the bounded `pypdf` dependency. Extraction preserves
one-based page order and joins page text with a stable double-newline boundary.
A PDF with at least one text-bearing page succeeds even when another page is
blank. A document with no extracted text returns a readable limitation stating
that scanned/image-only PDF requires OCR, which Plan 3 does not implement.
Malformed or unreadable files return a generic safe parse error without paths
or third-party diagnostics.

Upload does not call these parsers through M2 S6. S7～S9 own cleaning,
Chunking, format dispatch, Document lifecycle transitions, and safe persistence
of parser failures.

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

The presence of `vector_id` does not imply that M1 writes vectors to Qdrant.

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

M1 creates no retrieval or answer-generation runtime, so these rows are not yet
written by an HTTP workflow.

## Knowledge Base Service

`KnowledgeBaseService` owns the five metadata operations:

| Method | Behavior |
|---|---|
| `create_knowledge_base` | Adds and flushes one validated Knowledge Base |
| `list_knowledge_bases` | Orders by `created_at` descending, then `id` ascending |
| `get_knowledge_base` | Returns one row or raises `KnowledgeBaseNotFoundError` |
| `update_knowledge_base` | Changes only supplied fields and advances `updated_at` |
| `delete_knowledge_base` | Deletes and flushes one row |

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
| `POST` | `/api/v1/knowledge-bases/{knowledge_base_id}/documents` | `201` | Initial `DocumentRead` |

`PATCH` is a partial update. At least one field must be supplied. The mutable
fields are `name`, `description`, `embedding_provider`, `embedding_model`,
`vector_store`, and `vector_collection_name`. Explicit `null` clears nullable
fields; `name` and `vector_store` cannot be `null`. Unknown fields and blank
bounded names fail schema validation.

The route layer validates input, calls the service, and shapes the response. It
does not own persistence logic.

The Document upload request is `multipart/form-data` with one required `file`
field. There are no Document list, detail, chunk-query, or delete routes through
M2 S3.

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

Successful requests commit after the route returns. Any exception rolls the
request transaction back before the session closes. Tests use newly created
temporary SQLite databases and never read or modify the user database.

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

The active Plan 3 execution table contains the security, scope, artifact, and
Git gates. No verification command read or modified `backend/ai_agent_lab.db`.

## Deferred Capabilities

The following remain outside `P3-M2-S1～S3`:

- Document list, detail, chunk-query, delete, local-file deletion, and orphan
  recovery workflows;
- automatic parser dispatch, cleaning, Chunking, and lifecycle updates;
- Embedding Provider adapters and embedding execution;
- Qdrant client, collection lifecycle, vector upsert, and vector deletion;
- Retriever, RAG Prompt, RAG query/chat runtime, and Agent Tool integration;
- frontend Knowledge Base, upload, RAG Chat, and source display;
- Advanced RAG, Hybrid Search, Rerank, Evaluation, Memory, OCR, and multimodal
  capabilities.

See [Architecture](01-architecture.md) for the wider workspace boundaries.
