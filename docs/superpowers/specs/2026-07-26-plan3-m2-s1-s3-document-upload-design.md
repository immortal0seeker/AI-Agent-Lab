# Plan 3 M2 S1～S3 Document Upload Design

## Goal

Implement the first Document Ingestion boundary without starting parsing:

- `P3-M2-S1`: controlled local document storage;
- `P3-M2-S2`: one multipart Document Upload API;
- `P3-M2-S3`: filename, type, size, SHA-256, per-Knowledge-Base count, and
  duplicate validation.

The batch ends after an uploaded `.md`, `.txt`, or `.pdf` file has been stored
safely and one `Document` row has been committed with its initial lifecycle
state. It does not parse content or create chunks, embeddings, vectors, or
frontend behavior.

## Starting Baseline

- Branch: `main`.
- Starting `HEAD == origin/main`:
  `943c3370119db6299484ab6aceda7e6d47870a25`.
- Latest commit: `feat(knowledge): add knowledge base service and api`.
- The working tree and staging area were empty at intake.
- Plan 3 M1 is complete through `P3-M1-S9`.
- `KnowledgeBase`, `Document`, `DocumentChunk`, and `RagQuery` ORM/schema
  contracts and revision `20260726_0005` already exist.
- `KnowledgeBaseService`, safe service-error mapping, and request-scoped
  commit/rollback patterns already exist.
- `.gitignore` already excludes `uploads/`, `storage/`, SQLite files, caches,
  and generated runtime artifacts.
- `python-multipart` is not currently installed or declared. The installed
  FastAPI metadata requires `python-multipart>=0.0.18` for multipart support.

No command in this batch may read, migrate, delete, or rebuild
`backend/ai_agent_lab.db`.

## Acceptance Matrix

| Step | Acceptance requirement | Current evidence | Gap | Minimal addition |
|---|---|---|---|---|
| `P3-M2-S1` | Files are saved below a controlled root and filename collisions cannot overwrite another upload | Runtime directories are ignored; `knowledge/` and `rag/` ownership packages exist | No storage settings, storage abstraction, staging, atomic promotion, or storage tests | Add bounded settings and `DocumentStorage` under `app/knowledge/`, backed only by temporary directories in tests |
| `P3-M2-S2` | Multipart upload of Markdown/TXT returns a committed `Document` record and appears in OpenAPI | Nested Document API path is specified; Document ORM/read schema and thin-route patterns exist | No multipart dependency, Document service/dependency/router, or API tests | Add `python-multipart`, `DocumentService`, one nested POST route, dependency wiring, registration, and focused tests |
| `P3-M2-S3` | Oversized, unsupported, and duplicate files are rejected safely; size/hash/type are persisted | Document fields and checks already accept `md`/`txt`/`pdf`, non-negative size, and 64-character hash | No stream limit, filename/type validation, hash calculation, 50-document cap, same-KB duplicate policy, or error mapping | Add streaming validation, lowercase SHA-256, count/duplicate queries, safe errors, and RED/GREEN unit/service/API coverage |

The original Plan 3 source sets these M2 upload limits:

- maximum `20 MiB` per file (`20_971_520` bytes);
- maximum `50` Document rows per Knowledge Base;
- allowed filename suffixes: `.md`, `.txt`, and `.pdf`.

## Scope

### Included

- controlled storage root configuration;
- configurable maximum upload bytes and maximum documents per Knowledge Base,
  with the Plan defaults above;
- streamed multipart reads with bounded memory;
- basename normalization and stored UUID filenames;
- supported-suffix validation;
- empty-file rejection;
- incremental SHA-256 and size calculation;
- temporary staging and same-filesystem promotion;
- same-Knowledge-Base hash duplicate rejection;
- cross-Knowledge-Base uploads of the same bytes;
- initial `Document` creation;
- rollback cleanup for files created by an uncommitted request;
- one nested upload route;
- safe public errors;
- current documentation and acceptance evidence.

### Excluded

- Document list, detail, chunk-query, or delete routes;
- Markdown, TXT, or PDF parsing;
- file-content/MIME sniffing or PDF validity checks;
- OCR, Word, spreadsheet, presentation, HTML, image, audio, or video support;
- text cleaning, Chunking, token counting, or `DocumentChunk` writes;
- Embedding Providers, Qdrant clients, vectors, retrieval, prompts, or RAG;
- frontend Knowledge Base or upload behavior;
- Advanced RAG, Rerank, Evaluation, Memory, MCP, or later-Plan capabilities.

## Considered Approaches

### 1. Streamed staging plus UUID-owned final paths

Read the upload in bounded chunks, write a temporary file inside the controlled
root, and calculate size and SHA-256 incrementally. After service validation,
promote it to a UUID-derived final path on the same filesystem.

This is the selected approach because it bounds memory, separates storage from
FastAPI, prevents user filename collisions, supports deterministic cleanup, and
does not introduce a shared-blob lifecycle.

### 2. Read the whole file into memory

This would be smaller initially, but each request could retain about 20 MiB plus
multipart overhead, and the size boundary would be coupled to route behavior.
It was rejected in favor of a storage-owned streaming limit.

### 3. Global content-addressed blob storage

This could deduplicate bytes across Knowledge Bases, but it would require
cross-Knowledge-Base reference counting, deletion coordination, and orphan
collection. That lifecycle is not required by S1～S3 and would make this batch
larger than its acceptance surface.

## Ownership And File Layout

The backend flow is:

```text
multipart UploadFile
    -> thin Document route
    -> DocumentService
       -> KnowledgeBase existence/count checks
       -> DocumentStorage staging/hash/size/type
       -> same-KB duplicate check
       -> UUID final path + Document row
    -> request-scoped database commit
    -> DocumentRead
```

New production ownership:

- `app/knowledge/document_storage.py`
  - framework-neutral async stream protocol;
  - filename normalization;
  - extension/type validation;
  - staging, bounded reads, size, and SHA-256;
  - final-path containment and promotion;
  - staged/final cleanup helpers.
- `app/services/document_service.py`
  - Knowledge Base existence and count policy;
  - duplicate query;
  - Document identity and persistence;
  - coordination between SQLite and local storage;
  - registration of rollback cleanup.
- `app/api/v1/documents.py`
  - one multipart POST route;
  - conversion of the ORM result to `DocumentRead`.

The route does not calculate hashes, build paths, query duplicates, persist
rows, or decide error semantics.

Default runtime layout:

```text
backend/uploads/
├── .staging/
│   └── <random>.part
└── <knowledge_base_uuid>/
    └── <document_uuid>.<md|txt|pdf>
```

Runtime directories are created on demand and remain ignored. No real uploaded
file or runtime directory is committed.

## Settings

Add these fields to `Settings` and tracked examples:

| Environment variable | Type | Default | Validation |
|---|---|---|---|
| `DOCUMENT_STORAGE_ROOT` | `Path` | `./uploads` | non-blank; relative values resolve against the backend root |
| `DOCUMENT_MAX_UPLOAD_BYTES` | positive integer | `20971520` | `1..1073741824` |
| `DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE` | positive integer | `50` | `1..10000` |

The upper validation bounds prevent accidental unbounded configuration without
claiming those upper values are normal operating limits. Tests override the
storage root with a newly created temporary directory.

The upload chunk size is an internal constant of `65_536` bytes, not a public
setting.

## Storage Interfaces

`document_storage.py` defines:

```python
class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
class StagedDocument:
    temporary_path: Path
    original_filename: str
    file_type: Literal["md", "txt", "pdf"]
    file_size: int
    file_hash: str


@dataclass(frozen=True)
class StoredDocument:
    filename: str
    relative_path: str


class DocumentStorage:
    def __init__(self, root: Path, *, max_upload_bytes: int) -> None: ...

    async def stage(
        self,
        stream: AsyncReadable,
        *,
        original_filename: str | None,
    ) -> StagedDocument: ...

    def promote(
        self,
        staged: StagedDocument,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> StoredDocument: ...

    def discard_staged(self, staged: StagedDocument) -> None: ...

    def discard_stored(self, relative_path: str) -> None: ...
```

`stage` owns all I/O validation. It reads one `65_536`-byte chunk at a time,
stops once the configured maximum would be exceeded, and always removes its
partial staging file on failure.

`promote` creates a final filename of `<document_uuid>.<normalized_type>`,
creates only the UUID Knowledge Base directory, verifies the final candidate is
contained below the configured root, and performs a same-filesystem atomic
move. User-supplied path components never participate in the final path.

`discard_staged` and `discard_stored` are idempotent for absent files. They
never accept arbitrary absolute user input; stored cleanup receives only the
relative path produced by this `DocumentStorage`.

## Filename And Path Rules

The uploaded filename is treated only as display metadata and a source of the
supported suffix:

1. reject `None`, blank values, NUL bytes, ASCII control characters, and names
   longer than 255 characters after basename extraction;
2. normalize `\` to `/` and keep only the final basename;
3. preserve that safe basename as `original_filename`;
4. lowercase only the suffix for `file_type` and the generated stored name;
5. allow exactly `.md`, `.txt`, and `.pdf`.

Examples:

| Input | Stored original filename | Stored runtime filename |
|---|---|---|
| `Guide.MD` | `Guide.MD` | `<document_uuid>.md` |
| `C:\fakepath\notes.txt` | `notes.txt` | `<document_uuid>.txt` |
| `../manual.pdf` | `manual.pdf` | `<document_uuid>.pdf` |

Existing managed directories below the storage root must not be symbolic links
or Windows reparse points. The resolved staging and final paths must remain
below the configured root. This is a local single-user boundary; it does not
claim protection against an administrator replacing filesystem entries
concurrently with the process.

The HTTP `Content-Type` header is untrusted and is not used to infer
`file_type`. PDF header/content validation belongs to S4～S6 parsing.

## Service Flow

`DocumentService` exposes:

```python
async def upload_document(
    self,
    knowledge_base_id: UUID,
    *,
    original_filename: str | None,
    stream: AsyncReadable,
) -> Document:
    ...
```

The exact flow is:

1. load the Knowledge Base through `KnowledgeBaseService`; an unknown UUID
   fails before the upload stream is read;
2. count Documents in that Knowledge Base and reject when the count is already
   `50` or the configured limit;
3. stage and validate the file;
4. query `documents` by `(knowledge_base_id, file_hash)`;
5. when a match exists, discard the staged file and raise
   `DocumentDuplicateError`;
6. generate the Document UUID and promote the staged file to its final path;
7. register that newly created relative path for rollback cleanup;
8. add and flush a `Document` with:
   - generated `id`;
   - generated stored `filename`;
   - safe `original_filename`;
   - normalized `file_type`;
   - relative POSIX `file_path`;
   - calculated `file_size`;
   - lowercase `file_hash`;
   - existing default lifecycle states;
   - empty metadata;
9. return the ORM row without committing.

The same SHA-256 is rejected only within one Knowledge Base. The same bytes may
be uploaded into another Knowledge Base and receive an independent Document
identity and physical file.

No uniqueness migration is added. The service query is the duplicate gate for
the project's local-first single-user write model. Concurrent same-hash uploads
remain a documented limitation.

## Transaction And Cleanup Behavior

The existing request database dependency remains the only commit/rollback
owner. `DocumentService` does not call `commit`.

The service registers a per-Session pending-file collection in `Session.info`
and one pair of Session event callbacks:

- after successful commit: clear the pending-file collection;
- after rollback: idempotently remove every newly created final file, then
  clear the collection.

The callbacks catch cleanup I/O failures and log only a stable event name and
safe stack locations; they do not leak absolute paths or filenames into public
errors.

Staging cleanup remains local to `DocumentStorage.stage` and the service's
duplicate/count/error branches. A storage failure before promotion leaves no
Document row. A flush or request commit failure rolls back the row and removes
the newly promoted file.

Atomic rename prevents a normal request from exposing a partially written final
file. A hard process or machine termination can still leave a staging or
unreferenced final file. Cross-process recovery and orphan scanning are
explicitly deferred.

## HTTP API

Add exactly one route:

| Method | Path | Request | Success |
|---|---|---|---|
| `POST` | `/api/v1/knowledge-bases/{knowledge_base_id}/documents` | multipart form field `file` | `201 DocumentRead` |

The OpenAPI operation accepts one required uploaded file. The current
`DocumentRead` response is reused; no new response fields or ORM columns are
introduced.

The response exposes only the controlled relative `file_path`, never the
absolute storage root. Other Document endpoints listed in the overall Plan 3
API outline remain absent in this batch.

## Public Error Contract

All new errors inherit from `ServiceError` and use the shared response envelope.

| Condition | HTTP | Code | Safe message |
|---|---:|---|---|
| missing/invalid/empty filename or empty file | 400 | `document_file_invalid` | `The uploaded document is invalid` |
| file exceeds configured bytes | 413 | `document_too_large` | `The uploaded document exceeds the size limit` |
| suffix is not `.md`, `.txt`, or `.pdf` | 415 | `document_type_unsupported` | `The uploaded document type is not supported` |
| same hash already exists in the Knowledge Base | 409 | `document_duplicate` | `The document already exists in this knowledge base` |
| Knowledge Base is at its document limit | 409 | `knowledge_base_document_limit_reached` | `The knowledge base document limit was reached` |
| local staging/promotion/removal fails | 503 | `document_storage_error` | `The document storage operation failed` |
| Knowledge Base does not exist | 404 | `knowledge_base_not_found` | existing M1 contract |
| SQLAlchemy operation fails | 503 | `database_error` | existing shared contract |
| required multipart field is absent | 422 | `validation_error` | existing shared contract |

Public messages do not contain the original filename, SHA-256, UUID, absolute
path, SQL, exception text, or file content. The successful `DocumentRead`
response intentionally returns the user's sanitized original filename.

## Dependency And Wiring

Add `python-multipart>=0.0.18,<0.1.0` to the backend runtime dependencies. This
is the only new package. It is required by FastAPI to parse multipart forms and
does not perform network calls at runtime.

Add a `get_document_service` dependency that receives:

- the request-scoped SQLAlchemy `Session`;
- `Settings`;
- a `DocumentStorage` created from the configured root and byte limit.

Register the new router in `app.main` under the existing API v1 prefix. The
existing Knowledge Base routes remain unchanged.

## TDD Plan

### Cycle 1: Settings And DocumentStorage

RED tests establish:

- default and overridden settings;
- invalid zero/negative/excessive settings;
- supported case-insensitive suffixes;
- filename basename handling and invalid-name rejection;
- bounded multi-chunk reads;
- lowercase SHA-256 and exact byte count;
- empty and oversized failure;
- staging cleanup;
- UUID final layout and relative path;
- managed symlink/reparse rejection.

GREEN adds settings, environment examples, storage types, errors needed at the
storage boundary, and the `python-multipart` dependency.

### Cycle 2: DocumentService

RED tests establish:

- successful Document creation with default statuses and empty metadata;
- unknown Knowledge Base rejected before stream consumption;
- configured per-Knowledge-Base count limit;
- same-Knowledge-Base duplicate rejection and staging cleanup;
- the same bytes accepted across different Knowledge Bases;
- storage failure leaves no row;
- rollback removes a promoted file;
- commit retains it.

GREEN adds service errors, service exports, duplicate/count queries, transaction
cleanup registration, and dependency construction.

### Cycle 3: Multipart API

RED tests establish:

- OpenAPI exposes only the required nested POST in this batch;
- `.md`, `.txt`, and synthetic `.pdf` uploads return 201 and persist matching
  bytes plus one Document row;
- missing Knowledge Base, missing file, invalid filename, empty file,
  unsupported suffix, oversized file, count limit, and duplicate behavior;
- safe 400/404/409/413/415/503 envelopes;
- a database commit failure rolls back the row and removes the file;
- absolute storage paths, hashes, internal diagnostics, and file contents do
  not leak in error responses.

GREEN adds the thin route, error mapping, router registration, and no other
Document operations.

Tests use real temporary filesystem I/O and new temporary SQLite databases.
They use small overridden byte/count limits so no large fixture or user-local
path is required.

## Documentation

Update:

- `backend/.env.example`;
- `README.md` and `README_CN.md`;
- `CHANGELOG.md`;
- `docs/00-project-overview.md`;
- `docs/01-architecture.md`;
- `docs/20-knowledge-base-design.md`;
- `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`.

Documentation records:

- the current completion boundary through `P3-M2-S3`;
- storage layout and configuration;
- 20 MiB, 50-document, type, empty-file, hash, and duplicate rules;
- the one implemented upload route;
- SQLite metadata versus local file responsibilities;
- initial lifecycle states;
- missing parser/Chunking/Embedding/Qdrant/frontend capabilities;
- hard-crash orphan and concurrent duplicate limitations;
- fresh verification and Codex self-review evidence.

No upload screenshot or frontend claim is added.

## Verification And Review

Before handoff, run:

- focused config/storage/service/API/model tests;
- complete backend pytest;
- `pip check`;
- frontend test, typecheck, and production build;
- fresh temporary-SQLite Alembic upgrade/current/check;
- Markdown link/image validation;
- high-confidence secret and real-host scans;
- generated database/upload/staging/cache artifact checks;
- `web_fetch`, later-Plan, parser, Chunking, Embedding, Qdrant-client,
  Retriever, and frontend boundary scans;
- `git diff --check`, staged paths, branch, HEAD/origin, and existing tag
  targets.

Codex self-review classifies every finding as:

- must fix;
- later Step;
- accepted limitation;
- not applicable.

No Claude Code, Fable, subagent, real Provider, real Qdrant client, or external
review is used.

## Completion Boundary

`P3-M2-S1～S3` is complete only when:

- the one upload route accepts all three allowed suffixes;
- files are written only below a temporary-test or configured controlled root;
- Document rows and files agree after success;
- validation, duplicate, limit, storage, and database failure paths are safe;
- tests demonstrate cleanup after normal rollback;
- docs state that parsing and all later pipeline stages are absent;
- all matching and repository gates pass;
- the diff is ready for the user's manual commit.

Completion permits consideration of `P3-M2-S4～S6`. It does not start those
steps.
