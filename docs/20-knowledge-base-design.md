# Knowledge Base Design

## Scope

Plan 3 Milestone 1 establishes the persistence and management boundary for
Knowledge Bases. Through `P3-M1-S9`, the backend can create, list, read, update,
and delete Knowledge Base metadata through a service-owned HTTP API.

This milestone does not upload or parse documents, create chunks or embeddings,
connect to Qdrant, retrieve sources, generate RAG answers, or expose a frontend
Knowledge Base workspace. Those capabilities remain assigned to later Plan 3
steps.

## Storage Responsibilities

SQLite remains the default and long-term supported primary database. It owns:

- Knowledge Base configuration metadata;
- Document identity, file metadata, and ingestion lifecycle state;
- Document Chunk text, source metadata, and future vector identifiers;
- RAG query audit metadata and retrieved-chunk snapshots.

Qdrant is configured as Plan 3's vector-storage service, but M1 contains no
Qdrant client or Vector Store runtime. The `vector_store`,
`vector_collection_name`, and `vector_id` fields are persistence bridges, not
evidence that a collection or vector has been created.

Deleting a Knowledge Base in M1 deletes its SQLite-owned metadata through
database cascades. It does not contact Qdrant or delete a Qdrant collection.

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

The current milestone defines and validates these states but does not execute
their transitions. Upload, parsing, cleaning, Chunking, and Embedding services
remain deferred.

Deleting a Knowledge Base cascades to its Documents. The unique
`(id, knowledge_base_id)` pair supports a composite ownership check for chunks.

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

`PATCH` is a partial update. At least one field must be supplied. The mutable
fields are `name`, `description`, `embedding_provider`, `embedding_model`,
`vector_store`, and `vector_collection_name`. Explicit `null` clears nullable
fields; `name` and `vector_store` cannot be `null`. Unknown fields and blank
bounded names fail schema validation.

The route layer validates input, calls the service, and shapes the response. It
does not own persistence logic.

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

The active Plan 3 execution table contains the security, scope, artifact, and
Git gates. No verification command read or modified `backend/ai_agent_lab.db`.

## Deferred Capabilities

The following remain outside `P3-M1-S7～S9`:

- Document upload, controlled file storage, duplicate detection, and Document
  APIs;
- Markdown, TXT, or text-PDF parsing, cleaning, and Chunking;
- Embedding Provider adapters and embedding execution;
- Qdrant client, collection lifecycle, vector upsert, and vector deletion;
- Retriever, RAG Prompt, RAG query/chat runtime, and Agent Tool integration;
- frontend Knowledge Base, upload, RAG Chat, and source display;
- Advanced RAG, Hybrid Search, Rerank, Evaluation, Memory, OCR, and multimodal
  capabilities.

See [Architecture](01-architecture.md) for the wider workspace boundaries.
