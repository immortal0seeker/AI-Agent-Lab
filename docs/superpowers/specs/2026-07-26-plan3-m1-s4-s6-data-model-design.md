# Plan 3 M1 S4～S6 Data Model Design

**Date:** 2026-07-26

**Status:** Approved for planning

## Goal

Implement the structured SQLite metadata foundation for Plan 3 by adding
KnowledgeBase, Document, DocumentChunk, and RagQuery ORM models, Pydantic
create/read schemas, one Alembic migration, and focused persistence/schema/
migration tests.

This batch is limited to `P3-M1-S4～S6`. It does not add services, APIs, upload
storage, parsers, Chunking, Embedding, Qdrant clients, retrieval, or frontend
RAG behavior.

## Baseline

- `main` is clean at `dbdda4416b548ed805d1d3f1421f21a81c830f88`.
- `HEAD == origin/main`.
- Alembic head is `20260720_0004`.
- SQLite remains the primary business and audit database.
- Qdrant remains a separate vector store and is not accessed by this batch.
- Existing models use UUID v4 identities, timezone-naive UTC datetimes, named
  constraints, SQLAlchemy relationships, JSON columns, and explicit indexes.
- Existing architecture creates only create/read schemas until a real update
  behavior needs an update schema.

## Acceptance Matrix

| Step | Acceptance requirement | Current evidence | Gap | Minimal delivery |
|---|---|---|---|---|
| `P3-M1-S4` | KnowledgeBase ORM and schema are usable | Existing `Base`, UUID/timestamp helpers, model exports, and create/read schema patterns are stable | No KnowledgeBase table, model, schema, migration, or tests | Add one model, create/read schemas, migration coverage, and ORM/schema tests |
| `P3-M1-S5` | Document supports filename, type, path, hash, statuses, and metadata | Plan 3 defines the document fields and status lifecycle; existing JSON/status/check patterns are available | No Document table or database-enforced ownership/status rules | Add the Document model and schemas with knowledge-base ownership, status checks, metadata mapping, and persistence tests |
| `P3-M1-S6` | DocumentChunk and full RagQuery ORM/schema are usable | The execution table requires both models; the user approved the full RagQuery bridge record | No chunk/query tables, schemas, constraints, migration, or tests | Add both models and schemas, cross-parent integrity constraints, migration tests, and schema/ORM validation |

## Considered Approaches

### 1. Domain-separated models with strong relational integrity — selected

Use one ORM file per persisted concept, keep schemas grouped by public domain,
and enforce cross-parent consistency in SQLite with named unique, check, and
composite foreign-key constraints. This follows the existing AgentRun/ToolCall
integrity pattern and prevents invalid rows from becoming later RAG inputs.

### 2. Consolidate all Plan 3 models in one file — rejected

A single file reduces the initial file count but mixes knowledge ownership,
document lifecycle, chunk storage, and query audit responsibilities. Upload,
Chunking, and RAG work would quickly turn it into a large shared module.

### 3. Use only simple foreign keys and schema validation — rejected

Schema-only checks cannot protect direct ORM writes, migrations, or future
service bugs. In particular, they would allow a chunk to carry a
`knowledge_base_id` that differs from its parent document, or a RagQuery answer
message that belongs to another conversation.

## File And Ownership Boundaries

ORM models:

- `backend/app/models/knowledge_base.py`: KnowledgeBase fields and ownership
  relationships.
- `backend/app/models/document.py`: uploaded-document metadata and lifecycle
  status fields.
- `backend/app/models/document_chunk.py`: persisted text chunks and vector
  correlation metadata.
- `backend/app/models/rag_query.py`: Naive RAG query audit bridge.
- `backend/app/models/conversation.py`: add the owning RagQuery relationship.
- `backend/app/models/message.py`: add the optional answer-message relationship
  so deleting one answer can clear the correlation without deleting the query.
- `backend/app/models/__init__.py`: explicit exports so Alembic loads every
  model into `Base.metadata`.

Schemas:

- `backend/app/schemas/knowledge_base.py`: KnowledgeBase create/read schemas.
- `backend/app/schemas/document.py`: Document and DocumentChunk create/read
  schemas plus document status types.
- `backend/app/schemas/rag.py`: RagQuery create/read schemas.
- `backend/app/schemas/__init__.py`: explicit public exports.

Database and tests:

- `backend/alembic/versions/20260726_0005_plan3_knowledge_models.py`: all four
  tables in dependency order and reverse-order downgrade.
- `backend/tests/test_knowledge_models.py`: persistence, relationships,
  defaults, cascades, and invalid-association constraints.
- `backend/tests/test_knowledge_schemas.py`: validation and ORM-to-schema
  conversion.
- `backend/tests/test_knowledge_migration.py`: migration structure, named
  constraints/indexes, and downgrade isolation.

No service, API route, parser, upload, Embedding, Vector Store, or frontend file
is created.

## ORM Design

### KnowledgeBase

Table: `knowledge_bases`

| Column | Type | Null/default | Purpose |
|---|---|---|---|
| `id` | UUID | primary key, UUID v4 | Database identity |
| `name` | String(255) | required | User-facing knowledge-base name |
| `description` | Text | nullable | Optional description |
| `embedding_provider` | String(100) | nullable | Later Embedding configuration |
| `embedding_model` | String(255) | nullable | Later Embedding model identity |
| `vector_store` | String(100) | required, `qdrant` | Vector-store kind without creating a client |
| `vector_collection_name` | String(255) | nullable | Later Qdrant collection correlation |
| `created_at` | DateTime | `utc_now` | Creation time |
| `updated_at` | DateTime | `utc_now`, on update | Last metadata update |

The database rejects blank names. Names are not unique because the plan does
not define global uniqueness and a local user may reuse a display name.

KnowledgeBase owns Documents and RagQueries with ORM delete-orphan cascades and
database `ON DELETE CASCADE`.

### Document

Table: `documents`

| Column | Type | Null/default | Purpose |
|---|---|---|---|
| `id` | UUID | primary key, UUID v4 | Database identity |
| `knowledge_base_id` | UUID | required, indexed | Owning KnowledgeBase |
| `filename` | String(255) | required | Controlled stored filename |
| `original_filename` | String(255) | required | Original upload filename |
| `file_type` | String(32) | required | `md`, `txt`, or `pdf` in later upload flow |
| `file_path` | String(4096) | required | Controlled workspace-relative storage path |
| `file_size` | Integer | required, non-negative | Byte count |
| `file_hash` | String(64) | required | SHA-256 hexadecimal digest |
| `parse_status` | String(32) | `uploaded` | Parse lifecycle |
| `chunk_status` | String(32) | `pending` | Chunk lifecycle |
| `embedding_status` | String(32) | `pending` | Embedding lifecycle |
| `error_message` | Text | nullable | Safe processing failure text |
| `metadata_json` | JSON | isolated empty dict | Extensible document metadata |
| `created_at` | DateTime | `utc_now` | Creation time |
| `updated_at` | DateTime | `utc_now`, on update | Last lifecycle update |

Allowed status values:

- parse: `uploaded`, `parsing`, `parsed`, `failed`;
- chunk: `pending`, `chunking`, `chunked`, `failed`;
- embedding: `pending`, `embedding`, `ready`, `failed`.

The database checks the three allowed file types, non-negative size, exact
64-character hash length, and allowed statuses. A unique
`(id, knowledge_base_id)` key supports a composite DocumentChunk foreign key.

Document owns DocumentChunks through ORM delete-orphan and database cascade.

### DocumentChunk

Table: `document_chunks`

| Column | Type | Null/default | Purpose |
|---|---|---|---|
| `id` | UUID | primary key, UUID v4 | Database identity and future Qdrant payload ID |
| `document_id` | UUID | required, indexed | Parent Document |
| `knowledge_base_id` | UUID | required, indexed | Retrieval/filter correlation |
| `chunk_index` | Integer | required | Zero-based order within one document |
| `content` | Text | required | Chunk text |
| `token_count` | Integer | required | Later Chunker estimate |
| `char_count` | Integer | required | Character count |
| `heading` | String(512) | nullable | Nearest heading |
| `page_number` | Integer | nullable | One-based PDF page |
| `metadata_json` | JSON | isolated empty dict | Extensible source metadata |
| `vector_id` | String(255) | nullable | Later Qdrant point correlation |
| `created_at` | DateTime | `utc_now` | Creation time |

`chunk_index`, `token_count`, and `char_count` must be non-negative;
`page_number` is null or positive. `(document_id, chunk_index)` is unique.

A composite
`(document_id, knowledge_base_id) -> documents(id, knowledge_base_id)` foreign
key prevents cross-knowledge-base chunk rows. The model does not add a second
direct KnowledgeBase relationship; the denormalized ID exists for filtering
and is validated through its Document.

### RagQuery

Table: `rag_queries`

| Column | Type | Null/default | Purpose |
|---|---|---|---|
| `id` | UUID | primary key, UUID v4 | Query identity |
| `conversation_id` | UUID | nullable, indexed | Optional Chat/Agent conversation |
| `knowledge_base_id` | UUID | required, indexed | Queried KnowledgeBase |
| `query` | Text | required | User query |
| `retrieved_chunks_json` | JSON | isolated empty list | Selected chunk/source evidence |
| `answer_message_id` | UUID | nullable, indexed | Optional persisted answer Message |
| `latency_ms` | Integer | nullable, non-negative | End-to-end RAG latency |
| `created_at` | DateTime | `utc_now` | Creation time |

The user approved this full record despite the source Plan describing
`rag_queries` as optional, because the active execution table requires it in
S6 and the Plan 4 bridge requires equivalent query evidence.

KnowledgeBase and Conversation deletions cascade their query rows, matching the
existing ownership policy for conversation-scoped audit data. A composite
`(answer_message_id, conversation_id) -> messages(id, conversation_id)`
foreign key prevents cross-conversation answers. A check requires
`conversation_id` whenever `answer_message_id` is present. Individual answer
message deletion follows the existing AgentRun/Message relationship pattern:
the ORM clears `answer_message_id` while preserving the RagQuery.

## Schema Design

All new input schemas forbid unknown fields. Read schemas enable
`from_attributes`.

- `KnowledgeBaseCreate` validates a stripped, non-empty name and bounded
  provider/model/vector fields.
- `KnowledgeBaseRead` adds UUID and timestamps.
- `DocumentCreate` requires persisted file metadata, restricts file type to
  `md`/`txt`/`pdf`, validates a 64-character hexadecimal SHA-256 value, and
  defaults the three lifecycle statuses.
- `DocumentRead` adds UUID and timestamps.
- `DocumentChunkCreate` validates non-negative counts, zero-based index,
  positive optional page number, and non-blank content.
- `DocumentChunkRead` adds UUID and creation time.
- `RagQueryCreate` requires a non-blank query, defaults retrieved chunks to an
  isolated list, validates non-negative latency, and rejects
  `answer_message_id` without `conversation_id`.
- `RagQueryRead` adds UUID and creation time.

Public schemas expose a field named `metadata`; ORM columns use
`metadata_json` because `metadata` is reserved by SQLAlchemy. Pydantic
validation aliases accept both create-schema input and ORM attributes without
changing the database column name.

Update schemas are deferred to S7, where real update behavior and field
mutability rules will be implemented and tested.

## Migration Design

Revision `20260726_0005` follows `20260720_0004`.

Upgrade order:

1. `knowledge_bases`;
2. `documents`;
3. `document_chunks`;
4. `rag_queries`.

Downgrade drops those four tables in reverse dependency order and does not
modify Plan 1 or Plan 2 tables. The migration contains no data backfill and
does not read, migrate, delete, or rebuild `backend/ai_agent_lab.db`.

All migration verification uses a newly created system-temporary SQLite
database. Required gates are `upgrade head`, `current --check-heads`,
`alembic check`, and downgrade to `20260720_0004`.

## Error And Integrity Behavior

This batch has no API or service error mapping. Invalid direct ORM writes fail
with database `IntegrityError`; invalid schema inputs fail with Pydantic
`ValidationError`. Later services must translate those failures into safe
domain/API errors without exposing SQL, paths, document contents, metadata, or
query text.

Tests use only temporary SQLite databases, synthetic UUIDs, synthetic file
paths, and synthetic document/query content.

## Test Strategy

TDD begins with failing tests for:

1. persistence of one KnowledgeBase -> Document -> DocumentChunk graph and one
   RagQuery, including JSON/default isolation and relationships;
2. lifecycle status, count, hash, unique chunk order, cross-knowledge-base
   chunk, and cross-conversation answer constraints;
3. create-schema validation and read-schema conversion from ORM instances,
   including the public `metadata` mapping;
4. exact migration tables, columns, foreign keys, indexes, unique/check
   constraints, and downgrade isolation.

The tests are grouped by behavior instead of repeating every column assertion
in both ORM and schema suites. Migration inspection owns physical-schema
coverage; ORM tests own runtime relationships and integrity; Pydantic tests own
input/output validation.

After GREEN, run the focused model/schema/migration suite, the complete backend
suite, `pip check`, fresh temporary Alembic gates, and the existing frontend
test/typecheck/build regression. Finish with docs/link/secret/artifact/Plan
boundary/Git checks and Codex self-review.

## Documentation

Implementation updates:

- `CHANGELOG.md`;
- `README.md` and `README_CN.md` current completed scope;
- `docs/01-architecture.md` database foundation;
- `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md` acceptance evidence;
- the implementation plan under `docs/superpowers/plans/`.

`docs/20-knowledge-base-design.md` remains assigned to `P3-M1-S9` and is not
created in this batch.

## Explicit Non-Goals

- Knowledge Base service or CRUD API;
- file upload directories or multipart handling;
- Markdown, TXT, or PDF parsing;
- cleaning or Chunking implementation;
- Embedding providers;
- Qdrant client, collection, upsert, search, or payload implementation;
- Retriever, RAG prompt, RAG answer generation, or Tool registration;
- Advanced RAG, Hybrid Search, Rerank, Evaluation, Memory, OCR, or multimodal;
- frontend pages, API wrappers, or types;
- PostgreSQL introduction or migration.
