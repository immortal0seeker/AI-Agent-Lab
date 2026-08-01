# Document Ingestion Pipeline

## Scope

Plan 3 M3 S10～S12 completes the first end-to-end document vector-ingestion
path. A successful `POST /api/v1/knowledge-bases/{knowledge_base_id}/documents`
request stores the validated file, parses and cleans its text, creates ordered
Chunks, embeds all Chunk content, upserts the vectors into Qdrant, persists each
point identifier, and commits the Document as ready.

This document owns ingestion only. M4 S1～S3 now provide a separate Retriever;
RAG prompt/answer generation, Agent Tool integration, Advanced RAG, Rerank,
Evaluation, Memory, OCR, and multimodal work remain outside this boundary.

## Runtime Flow

```text
multipart upload
  -> validate Knowledge Base, suffix, size, count, and duplicate hash
  -> stage and promote controlled local file
  -> create Document(uploaded / pending / pending)
  -> parse -> clean -> split -> persist ordered DocumentChunk rows
  -> set embedding_status=embedding and flush SQLite
  -> ensure configured Qdrant COSINE collection
  -> embed all Chunk content as one bounded batch
  -> validate vector count and dimension
  -> build source-preserving payloads
  -> upsert point UUID == DocumentChunk UUID
  -> persist DocumentChunk.vector_id
  -> set embedding_status=ready
  -> request-owned SQLite commit
```

The API route remains thin. `DocumentService` owns upload coordination,
`DocumentIngestionService` owns state transitions and persistence composition,
and `app.rag.ingestion_pipeline.ingest_document_vectors()` owns the independent
Embedding-to-VectorStore boundary. None of these services commits the database;
the request session remains the transaction owner.

## Identity And Traceability

Each vector point uses the owning `DocumentChunk.id` as its UUID. On success,
the same canonical UUID string is stored in `document_chunks.vector_id`. This
gives a direct SQLite-to-Qdrant association without adding a second identity.

Every Qdrant payload preserves:

- `knowledge_base_id`, `document_id`, and `chunk_id`;
- source `filename` and zero-based `chunk_index`;
- exact Chunk `content`;
- optional `heading` and `page_number`;
- nested JSON-safe source `metadata`.

Before any Provider call, the pipeline rejects an empty Chunk list, a non-Chunk
item, mismatched Document/Knowledge Base ownership, or a non-contiguous order.
After embedding, it checks one vector per Chunk and an exact match between the
Embedding and VectorStore dimensions. After upsert, the returned point UUIDs
must exactly match the expected Chunk UUIDs in order.

## Lifecycle States

| Outcome | Parse | Chunk | Embedding | Chunk rows | Vector IDs |
|---|---|---|---|---:|---:|
| Full success | `parsed` | `chunked` | `ready` | kept | all persisted |
| Parse or parse-limit failure | `failed` | `failed` | `failed` | none | none |
| Empty-cleaned text or chunk-limit failure | `parsed` | `failed` | `failed` | none | none |
| Embedding operation failure | `parsed` | `chunked` | `failed` | kept | none |
| VectorStore operation failure | `parsed` | `chunked` | `failed` | kept | none |
| Unexpected storage/database/programming failure | rolled back | rolled back | rolled back | rolled back | compensated when possible |

Expected content and runtime failures return the created Document as HTTP 201
so its lifecycle remains inspectable. Embedding failures expose only
`Document embedding failed.`; vector failures expose only
`Document vector storage failed.`. They do not copy document text, vectors,
credentials, endpoints, or remote response bodies into the persisted error.

Provider or VectorStore dependency initialization happens before upload bytes
are streamed. A configuration/initialization failure therefore creates no file
or database row and returns a stable HTTP 503 response:

| Code | Message |
|---|---|
| `embedding_provider_unavailable` | `The embedding provider is unavailable` |
| `vector_store_unavailable` | `The vector store is unavailable` |

## Cross-Store Transaction Boundary

SQLite and Qdrant do not share a distributed transaction. After a successful
upsert, the service registers a request-scoped asynchronous rollback callback.
If the later SQLite commit fails, the session first rolls back SQLite and then
deletes points using both `knowledge_base_id` and `document_id`. A successful
commit discards the rollback callback. The Qdrant client is closed by a
request-session finalizer on both success and failure.

The vector pipeline also attempts the same ownership-scoped deletion when an
upsert reports a failure or returns unexpected point IDs, because the remote
write outcome may be uncertain. Cleanup errors are safely logged and do not
replace the original failure.

This compensation is deliberately best-effort. An abrupt process/host crash
after Qdrant accepts an upsert, or a Qdrant outage during cleanup, may leave
orphan points. Automated orphan reconciliation and a Document retry/delete API
belong to later work; operators should use a fresh collection for development
when an exact reset is required.

## Configuration

The pipeline uses the existing public settings in `backend/.env.example`:

- `DOCUMENT_STORAGE_ROOT`, upload/count/processing limits;
- `RAG_CHUNK_SIZE` and `RAG_CHUNK_OVERLAP`;
- `EMBEDDING_PROVIDER` and the independent OpenAI-compatible Embedding settings;
- `QDRANT_URL`, `QDRANT_COLLECTION_NAME`, and `QDRANT_TIMEOUT_SECONDS`.

The configured Embedding dimension must equal the existing Qdrant collection
dimension. An incompatible existing collection fails closed; ingestion never
rebuilds or deletes it automatically. Qdrant is bound to `127.0.0.1:6333` by
the repository Compose configuration, while SQLite remains the primary business
and audit database.

Tests use synthetic credentials, a deterministic Mock Embedding Provider,
temporary SQLite databases and workspaces, plus isolated in-memory VectorStore
test doubles. The runtime smoke check uses the local Qdrant container and a
random temporary collection, then verifies that collection is removed. No test
reads or modifies `backend/ai_agent_lab.db` or calls a paid Provider.

## Verification And Limits

The S10～S12 verification covers:

- pipeline ownership/order, vector-count/dimension, point-ID, upsert, and
  compensation behavior;
- success and every parse/chunk/Provider/VectorStore state transition;
- API response, SQLite rows, Qdrant payloads, safe initialization errors, file
  cleanup, and post-upsert commit failure;
- real local Qdrant ensure/upsert/search/delete with a deterministic Mock
  Embedding Provider;
- complete backend, migration, frontend, documentation, secret, artifact,
  Plan-boundary, and Git checks.

Current intentional limits are one Provider batch per bounded Document, no
automatic retry/fallback/caching, no persisted embedding usage/cost, and no
hard-crash orphan reconciler. A standalone Retriever exists through M4 S3, but
answer generation must not be inferred from successful ingestion or retrieval.

See [Knowledge Base Design](20-knowledge-base-design.md),
[Embedding Provider](21-embedding-provider.md), and
[Architecture](01-architecture.md) for the surrounding boundaries.
