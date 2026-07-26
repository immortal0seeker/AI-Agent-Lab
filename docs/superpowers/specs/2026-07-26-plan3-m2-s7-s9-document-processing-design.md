# Plan 3 M2 S7～S9 Document Processing Design

## Status

- Scope: `P3-M2-S7～S9`
- Date: 2026-07-26
- Design approval: confirmed by the user
- Implementation status: not started

## Goal

Complete Plan 3 Milestone 2 by adding independently testable text cleaning and
naive Chunking, then synchronously composing the existing upload and parsers
into a transaction-safe processing flow that persists `DocumentChunk` rows and
visible Document lifecycle results.

The selected API behavior is:

- a successfully processed upload returns HTTP 201 with a
  `parsed` / `chunked` Document;
- an expected content failure, such as unreadable text bytes or a scanned PDF,
  returns HTTP 201 with a persisted failed Document and safe `error_message`;
- controlled-storage or database failures keep their existing error response
  and roll the request back.

## Acceptance Matrix

| Step | Acceptance requirement | Current evidence | Gap | Minimum new evidence |
|---|---|---|---|---|
| S7 | Normalize newlines, remove excessive blank lines and meaningless invisible characters, preserve Markdown headings and PDF pages | Markdown/TXT/PDF parsers return `ParsedDocument`; PDF pages and Markdown heading line numbers exist | No cleaner or line-number adjustment after blank-line collapse | Pure cleaner tests for newline/control cleanup, Markdown/code preservation, heading mapping, and independent PDF-page cleanup |
| S8 | Character Chunking with overlap, paragraph preference, ordered index, token estimate, heading/page provenance, and database-ready drafts | `DocumentChunk` ORM/schema and ownership constraints exist | No Chunker, configuration, draft contract, or token heuristic | Pure Chunker tests for configured bounds, paragraph/hard fallback, overlap/progress, Markdown headings, PDF pages, and empty-text rejection |
| S9 | Upload invokes parse → clean → chunk, writes chunks, and records visible states/errors without crashing on expected content failures | Upload stores a controlled file and initial Document; parsers fail safely; request Session owns commit/rollback | No parser dispatch, stored-path resolution for ingestion, status transitions, chunk persistence, or expected-failure behavior | Service/API tests for all formats, failed content, safe errors, persisted chunks/statuses, ownership, and database rollback |

## Scope

### Included

- pure text cleaning that returns a new `ParsedDocument`;
- pure naive character Chunking that returns immutable drafts;
- configurable chunk size and overlap;
- deterministic token-count estimation;
- Markdown heading and PDF page provenance;
- controlled resolution of a stored Document path;
- synchronous parser dispatch during the existing upload request;
- `DocumentChunk` persistence through the existing ORM;
- Document parse/chunk lifecycle transitions and safe content errors;
- current API response behavior, documentation, and acceptance evidence.

### Excluded

- new Document list, detail, chunk-query, retry, reprocess, or delete APIs;
- background workers, queues, polling, cancel, or progress streaming;
- real tokenizers or model-specific token limits;
- Embedding Provider abstractions or calls;
- Qdrant clients, collections, points, or vectors;
- Retriever, RAG Prompt, RAG query/chat, or Agent Tool integration;
- frontend Knowledge Base or upload behavior;
- OCR, layout analysis, table reconstruction, image extraction, or multimodal
  parsing;
- Advanced RAG, Hybrid Search, Rerank, Evaluation, Memory, or later Plans;
- ORM/schema/migration changes unless fresh implementation evidence proves the
  existing persistence contract insufficient.

## Considered Approaches

### 1. Pure processing units plus an ingestion service

`text_cleaner.py` and `chunker.py` remain deterministic and
database-independent. `DocumentIngestionService` owns parser dispatch,
lifecycle transitions, and ORM writes. `DocumentService` continues to own
upload policy and invokes ingestion after the stored file and initial Document
exist.

This is the selected approach. Each unit has one responsibility, the current
route remains thin, and later Embedding work can extend orchestration without
moving text algorithms into the upload service.

### 2. Put processing directly in `DocumentService`

This reduces the number of modules but combines upload limits, deduplication,
filesystem promotion, parser dispatch, cleaning, Chunking, lifecycle policy,
and ORM writes in one class. It is rejected because the service would become
difficult to test and extend.

### 3. Separate processing API or background task

An explicit process endpoint or queue would separate upload latency from
processing. It is rejected for this batch because Plan 3 specifies a
synchronous MVP, the user selected synchronous upload behavior, and no worker
lifecycle has been designed.

## Module Boundary

The implementation will add:

```text
backend/app/rag/
├── text_cleaner.py
└── chunker.py

backend/app/services/
└── document_ingestion_service.py
```

It will update:

```text
backend/app/core/config.py
backend/app/knowledge/document_storage.py
backend/app/services/document_service.py
backend/app/api/dependencies.py
```

No new API route is needed. Existing `Document`, `DocumentChunk`, and response
schemas already contain the required lifecycle, content, count, heading, page,
metadata, and error fields.

## Text Cleaner

`clean_parsed_document(document: ParsedDocument) -> ParsedDocument` is a pure
function.

### Newline and control policy

For every cleaned text unit:

1. convert CRLF and bare CR to LF;
2. remove C0/C1 control characters except LF and TAB;
3. remove stray BOM (`U+FEFF`), zero-width space (`U+200B`), and word joiner
   (`U+2060`);
4. preserve ordinary Unicode, including emoji variation selectors and
   zero-width joiners that can carry semantic content;
5. treat whitespace-only lines as blank;
6. collapse every run of blank lines to one blank paragraph;
7. remove leading and trailing blank lines.

The cleaner does not normalize ordinary spaces, indentation, tabs, Markdown
markers, code-block contents, punctuation, case, or Unicode composition.

### Markdown metadata

Markdown text is cleaned as one unit. The cleaner tracks the mapping from each
retained original line number to its cleaned line number. It copies the parser
metadata and updates each heading's `line_number` through that mapping.

Heading text, level, code-block metadata, and original encoding metadata remain
unchanged. Code contents are subject only to the same control/newline policy;
indentation and fence syntax remain intact.

### PDF pages

Each `ParsedPage` is cleaned independently. Its positive page number is
unchanged, including for a page that becomes empty. Document-level text is
rebuilt by joining cleaned page text with two LF characters. This prevents
cleaning from losing the page boundary needed by the Chunker.

Markdown and TXT continue to return `pages=None`.

## Chunker

### Public contract

`DocumentChunkDraft` is an immutable dataclass:

```python
chunk_index: int
content: str
token_count: int
char_count: int
heading: str | None
page_number: int | None
metadata: dict[str, object]
```

The public function is:

```python
chunk_document(
    document: ParsedDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[DocumentChunkDraft, ...]
```

The function rejects:

- `chunk_size <= 0`;
- `chunk_overlap < 0`;
- `chunk_overlap >= chunk_size`;
- a Document with no non-whitespace cleaned text.

Invalid runtime configuration is prevented by Settings validation before
service construction. Empty usable content raises the dedicated safe
`DocumentContentEmptyError`.

### Configuration

Settings add:

| Environment variable | Default | Validation |
|---|---:|---|
| `RAG_CHUNK_SIZE` | `1000` | integer from 100 through 10,000 |
| `RAG_CHUNK_OVERLAP` | `150` | integer from 0 through 2,000 and strictly less than chunk size |

The defaults sit inside the Plan 3 recommendation of 800～1200 characters and
100～200 overlap. Values count Python Unicode characters, not bytes or model
tokens.

### Boundary selection

For each chunk window:

1. set a hard end at `start + chunk_size`;
2. in the latter half of the window, prefer the last double-LF paragraph
   boundary;
3. otherwise prefer the last LF boundary in the latter half;
4. otherwise use the hard character boundary;
5. if more text remains, begin the next chunk at `end - chunk_overlap`;
6. enforce monotonic progress even for extreme valid inputs.

This is intentionally naive character Chunking. It does not perform semantic,
sentence-aware, recursive, parent-child, or tokenizer-based splitting.

### Provenance

Markdown and TXT are chunked as one text sequence. For Markdown, cleaned heading
line numbers are converted to character offsets. Each chunk receives the latest
heading at or before its start; a chunk before the first heading has no heading.
If a chunk crosses a new heading, its `heading` remains the heading active at
the chunk start.

PDF pages are chunked independently and chunks never cross a page boundary.
Every PDF chunk records its one-based `page_number`. Overlap restarts within
each page.

Draft metadata is small and JSON-compatible:

- `source_format`;
- `start_char`;
- `end_char`;
- optional Markdown `heading_level`.

PDF offsets are page-relative. Markdown/TXT offsets are document-relative.
Parser metadata is not copied wholesale into every chunk.

### Token estimate

The deterministic heuristic is:

```python
max(1, ceil(len(content.encode("utf-8")) / 4))
```

It gives an approximate audit value without introducing a model-specific
tokenizer. It is not used to enforce Provider limits in this batch.

## Controlled Stored-Path Resolution

`DocumentStorage` adds a read-only resolver for an existing stored relative
path and the expected Knowledge Base ID, Document ID, and file type. It accepts
only the existing two-component layout:

```text
<knowledge_base_uuid>/<document_uuid>.<md|txt|pdf>
```

The resolver requires both path UUIDs and the suffix to equal the supplied
Document ownership values. It resolves below the configured root and rejects a
missing file, a non-file, a root/Knowledge-Base-directory/file symlink or
reparse point, or a path that escapes the controlled root. This prevents a
tampered database row from reading another valid stored Document and prevents
parent-directory indirection. It returns an internal absolute `Path` only to
backend services and never places it in a schema, log, error message, or
frontend response.

Storage resolution failure remains `DocumentStorageError`; the existing API
maps it to safe HTTP 503 and request rollback.

## Ingestion Service

`DocumentIngestionService` consumes:

- the request `Session`;
- `DocumentStorage`;
- validated chunk size and overlap.

Its operation accepts the just-created `Document`.

### Success flow

```text
Document uploaded and promoted
    ↓
Document row flushed as uploaded/pending
    ↓
parse_status = parsing
    ↓
resolve controlled stored path
    ↓
dispatch md/txt/pdf parser
    ↓
parse_status = parsed
    ↓
copy cleaned parser metadata to Document.metadata_json
    ↓
chunk_status = chunking
    ↓
clean ParsedDocument
    ↓
create DocumentChunkDraft values
    ↓
add ordered DocumentChunk rows
    ↓
flush
    ↓
chunk_status = chunked
embedding_status remains pending
error_message = null
```

The service flushes but never commits. The request database dependency remains
the only commit/rollback owner.

### Expected content failures

The ingestion service catches only safe, expected processing errors:

- `DocumentParseError`, including the scanned/image-only PDF limitation;
- `DocumentContentEmptyError`.

Parser failure produces:

```text
parse_status = failed
chunk_status = failed
embedding_status = pending
error_message = safe parser message
no DocumentChunk rows
```

Cleaned-empty failure produces:

```text
parse_status = parsed
chunk_status = failed
embedding_status = pending
error_message = "Document contains no usable text."
no DocumentChunk rows
```

Both outcomes are flushed, returned as HTTP 201 `DocumentRead`, and committed by
the existing request dependency. This preserves a visible Document identity and
diagnostic without pretending it is ready.

Storage and SQLAlchemy failures are not converted to content failures. They
propagate through existing safe API handling, roll the request back, and remove
the promoted file through the existing Session callback.

Unexpected programming errors are also not silently stored as content errors.
They retain the existing safe HTTP 500 behavior and rollback, so defects cannot
be mislabeled as bad user documents.

## Upload Service and API

`DocumentService.upload_document()` keeps its current validation, staging,
hash, promotion, rollback cleanup, and initial Document construction. After
the initial flush it calls `DocumentIngestionService.process_document()`.

The existing route remains:

```text
POST /api/v1/knowledge-bases/{knowledge_base_id}/documents
```

It still returns `DocumentRead` with HTTP 201. No request field or response
schema is added. Existing clients now observe final synchronous parse/chunk
state rather than the former initial state.

The request remains atomic for infrastructure failures. Expected content
failures are deliberate committed business outcomes, not request exceptions.

## Transaction and Retry Semantics

One upload request creates at most one Document and its ordered Chunk rows in
one database transaction. Chunk indices begin at zero and are unique within the
Document.

There is no retry or reprocess endpoint in this batch. Duplicate upload policy
still rejects the same hash in one Knowledge Base, including when the existing
Document has a failed processing status. Changing this policy requires a later
explicit retry/replacement design.

## Test Strategy

Tests use newly created temporary SQLite databases, temporary controlled
storage, synthetic Markdown/TXT/PDF content, and no Provider or network calls.

### Cleaner

- CRLF and CR normalization;
- excessive/whitespace-only blank-line collapse;
- selected control and invisible-character removal;
- preservation of tabs, Markdown markers, code indentation, and meaningful
  joiners;
- corrected Markdown heading line numbers;
- independent PDF page cleanup and page-number preservation;
- input result remains unmodified.

### Chunker

- invalid configuration;
- one short chunk;
- hard-boundary splitting;
- paragraph and newline preference;
- exact overlap with monotonic progress;
- zero overlap;
- ordered indices and character counts;
- deterministic ASCII and Unicode token estimates;
- latest Markdown heading selection;
- PDF chunks never cross pages and retain page numbers;
- empty cleaned content raises a safe error.

### Ingestion service

- parser dispatch for Markdown, TXT, and PDF;
- successful final lifecycle and metadata;
- ordered `DocumentChunk` persistence with ownership fields;
- Markdown heading and PDF page persistence;
- parser failure state and safe message;
- cleaned-empty state and safe message;
- no partial chunks on an expected processing failure;
- storage failure propagation;
- SQLAlchemy flush failure rollback behavior.

### API

- successful Markdown/TXT/text-PDF uploads return parsed/chunked state;
- response and database contain matching states and chunk rows;
- scanned PDF and invalid text return HTTP 201 failed Documents with safe
  messages and no chunks;
- content, hashes, absolute paths, and low-level diagnostics remain absent from
  errors;
- pre-existing upload validation, duplicate, limit, rollback, and OpenAPI
  contracts remain valid.

Tests never read or modify `backend/ai_agent_lab.db`.

## TDD Sequence

1. Add Cleaner tests and watch them fail because the module does not exist.
2. Implement the minimum pure Cleaner and rerun to green.
3. Add Settings and Chunker tests and watch them fail because configuration and
   Chunker contracts do not exist.
4. Implement validated configuration, draft contract, boundary logic,
   provenance, and token estimate; rerun to green.
5. Add storage-resolution tests and watch the missing resolver fail.
6. Implement the read-only controlled resolver and rerun storage regression.
7. Add ingestion service tests and watch the missing service fail.
8. Implement dispatch, lifecycle handling, chunk persistence, and expected
   content failures; rerun to green.
9. Add service/API acceptance tests for the approved synchronous upload
   behavior and watch them fail because upload dependency wiring does not yet
   invoke ingestion.
10. Wire `DocumentService` and its FastAPI dependency to the ingestion service,
    then rerun all M2 tests to green.
11. Update documentation and active Plan evidence.
12. Run focused verification, full backend/frontend regression, dependency,
    temporary migration, documentation/link, secret, artifact, Plan-boundary,
    diff, and Git-status gates.
13. Perform Codex self-review, fix every must-fix finding, and rerun affected
    gates.

## Documentation Changes

Implementation completion will update:

- `.env.example` and `backend/.env.example` if both currently document backend
  runtime settings;
- `README.md` and `README_CN.md`;
- `CHANGELOG.md`;
- `docs/01-architecture.md`;
- `docs/20-knowledge-base-design.md`;
- the active Plan 3 execution table;
- the implementation plan with observed TDD and verification evidence.

Documentation will state that M2 now ends at persisted chunks, while Embedding,
Qdrant client work, retrieval, RAG APIs, Document query/delete APIs, retries,
and frontend Knowledge Base behavior remain unimplemented.

## Completion Criteria

`P3-M2-S7～S9` is complete only when:

- Cleaner and Chunker are independently testable;
- configured Chunking preserves required overlap, order, heading, and page
  provenance;
- successful uploads persist final parsed/chunked Document state and ordered
  chunks;
- expected content failures persist safe visible failed state without chunks;
- storage/database/unexpected failures retain safe rollback behavior;
- no Embedding, Qdrant client, Retriever, frontend, OCR, Advanced RAG, or
  later-Plan runtime was added;
- focused and full verification passes;
- dependency, temporary migration, docs/link, secret, artifact, Plan-boundary,
  diff, and Git-status gates pass;
- Codex self-review has no unresolved must-fix finding;
- the working tree is ready for the user's manual commit.

Completion closes Plan 3 Milestone 2 and permits consideration of
`P3-M3-S1～S3`. It does not start those steps.
