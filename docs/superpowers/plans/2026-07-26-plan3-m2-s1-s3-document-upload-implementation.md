# Plan 3 M2 S1～S3 Document Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Repository
> policy forbids subagents for this work.

**Goal:** Add controlled, validated multipart Document upload while preserving
the existing SQLite transaction boundary and stopping before parsing.

**Architecture:** A framework-neutral `DocumentStorage` streams uploads into a
controlled staging directory, calculates size and SHA-256, and promotes them to
UUID-owned relative paths. `DocumentService` owns Knowledge Base/count/duplicate
policy and Document persistence, while one thin FastAPI route passes
`UploadFile` into the service and returns `DocumentRead`.

**Tech Stack:** Python 3.11, FastAPI 0.138, `python-multipart`, Pydantic Settings,
SQLAlchemy 2.0, SQLite, pytest, temporary filesystem fixtures.

## Global Constraints

- Work only on `P3-M2-S1～S3`.
- Maximum file size defaults to exactly `20_971_520` bytes.
- Maximum Documents per Knowledge Base defaults to exactly `50`.
- Allowed suffixes are exactly `.md`, `.txt`, and `.pdf`.
- Same SHA-256 is rejected within one Knowledge Base and allowed across
  different Knowledge Bases.
- Store files as
  `<knowledge_base_uuid>/<document_uuid>.<normalized_suffix>`.
- Persist only a relative POSIX `file_path`; never return the absolute root.
- Routes remain thin and the request database dependency remains the only
  commit/rollback owner.
- Do not add or change ORM columns, constraints, or Alembic revisions.
- Do not implement parser, cleaner, Chunker, Embedding, Qdrant client,
  Retriever, Document query/delete routes, frontend behavior, or Plan 4+
  runtime.
- Tests use new temporary SQLite databases, temporary upload roots, synthetic
  bytes, and no real network/Provider/Qdrant/user database.
- Do not read, migrate, delete, or rebuild `backend/ai_agent_lab.db`.
- Do not stage, commit, push, tag, switch branches, or use external review.
- Necessary non-obvious code comments are Chinese.

---

## File Responsibility Map

### New files

| File | Responsibility |
|---|---|
| `backend/app/knowledge/errors.py` | Document upload/storage domain errors |
| `backend/app/knowledge/document_storage.py` | filename/type validation, bounded streaming, staging, hash, promotion, cleanup |
| `backend/app/services/document_service.py` | Knowledge Base/count/duplicate policy, Document persistence, rollback file cleanup |
| `backend/app/api/v1/documents.py` | one nested multipart POST route |
| `backend/tests/test_document_storage.py` | pure storage/path/stream tests |
| `backend/tests/test_document_service.py` | temporary-SQLite plus real-temp-files service state tests |
| `backend/tests/test_document_api.py` | OpenAPI, multipart, errors, transaction API tests |

### Modified files

| File | Change |
|---|---|
| `backend/app/core/config.py` | storage root, byte limit, per-KB count limit |
| `backend/.env.example` | tracked non-secret upload settings |
| `backend/pyproject.toml` | `python-multipart>=0.0.18,<0.1.0` |
| `backend/app/knowledge/__init__.py` | storage/error exports |
| `backend/app/services/__init__.py` | `DocumentService` export |
| `backend/app/api/dependencies.py` | `get_document_service` |
| `backend/app/api/errors.py` | safe Document error mapping and handler |
| `backend/app/main.py` | router registration |
| `backend/tests/test_config.py` | new Settings contracts |
| `README.md`, `README_CN.md`, `CHANGELOG.md` | current user/operations truth |
| `docs/00-project-overview.md`, `docs/01-architecture.md`, `docs/20-knowledge-base-design.md` | storage/API design and boundary |
| `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md` | Batch 4 evidence and acceptance state |
| this implementation plan | checkbox and exact observed evidence updates |

No other source path belongs in this batch.

---

### Task 1: Settings, Upload Errors, And Controlled DocumentStorage

**Files:**

- Create: `backend/app/knowledge/errors.py`
- Create: `backend/app/knowledge/document_storage.py`
- Create: `backend/tests/test_document_storage.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/knowledge/__init__.py`
- Modify: `backend/tests/test_config.py`
- Modify: `backend/.env.example`
- Modify: `backend/pyproject.toml`

**Interfaces:**

- Consumes: `Settings`, `is_reparse_point`, `Path`, async `.read(size)`.
- Produces:
  - `DocumentError`;
  - `DocumentFileInvalidError`;
  - `DocumentTooLargeError`;
  - `DocumentTypeUnsupportedError`;
  - `DocumentStorageError`;
  - `DocumentDuplicateError`;
  - `KnowledgeBaseDocumentLimitReachedError`;
  - `AsyncReadable`;
  - `StagedDocument`;
  - `StoredDocument`;
  - `DocumentStorage`.

- [x] **Step 1: Add failing Settings tests**

Append tests with these exact contracts to `test_config.py`:

```python
from pathlib import Path


def test_settings_default_document_upload_limits() -> None:
    settings = Settings(_env_file=None)

    assert settings.document_storage_root.is_absolute()
    assert settings.document_storage_root.name == "uploads"
    assert settings.document_max_upload_bytes == 20_971_520
    assert settings.document_max_files_per_knowledge_base == 50


def test_settings_resolves_relative_document_storage_from_backend() -> None:
    settings = Settings(
        _env_file=None,
        DOCUMENT_STORAGE_ROOT="runtime_uploads",
    )

    assert settings.document_storage_root.is_absolute()
    assert settings.document_storage_root.name == "runtime_uploads"
    assert settings.document_storage_root.parent.name == "backend"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("DOCUMENT_MAX_UPLOAD_BYTES", 0),
        ("DOCUMENT_MAX_UPLOAD_BYTES", 1_073_741_825),
        ("DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE", 0),
        ("DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE", 10_001),
    ],
)
def test_settings_rejects_invalid_document_upload_limits(
    field_name: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})
```

- [x] **Step 2: Add failing storage tests**

Create a `ChunkedStream` test double that returns at most the requested bytes
and records `read_calls`. Add focused tests:

```python
class ChunkedStream:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._offset = 0
        self.read_calls = 0

    async def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if self._offset >= len(self._content):
            return b""
        end = len(self._content) if size < 0 else self._offset + size
        chunk = self._content[self._offset:end]
        self._offset += len(chunk)
        return chunk
```

Test names and assertions:

- `test_storage_stages_stream_and_calculates_sha256`
  - use `b"synthetic document"` and filename `Guide.MD`;
  - assert normalized type `md`;
  - assert original filename remains `Guide.MD`;
  - assert exact size and lowercase `hashlib.sha256(...).hexdigest()`;
  - assert staging file contains the exact bytes;
  - assert at least two reads, including EOF.
- `test_storage_promotes_to_uuid_owned_relative_path`
  - promote with fixed UUIDs;
  - assert filename `<document_uuid>.txt`;
  - assert relative path
    `<knowledge_base_uuid>/<document_uuid>.txt`;
  - assert only the final file exists and contains the bytes.
- `test_storage_keeps_only_basename`
  - parametrize `C:\fakepath\notes.txt` and `../notes.txt`;
  - assert `original_filename == "notes.txt"`;
  - assert no path outside the configured root exists.
- `test_storage_rejects_invalid_filename`
  - parametrize `None`, `""`, whitespace, NUL, ASCII control, and a basename
    longer than 255;
  - expect `DocumentFileInvalidError`;
  - assert staging contains no files.
- `test_storage_rejects_unsupported_type`
  - parametrize `.csv`, `.docx`, missing suffix, and `.pdf.exe`;
  - expect `DocumentTypeUnsupportedError`;
  - assert staging contains no files.
- `test_storage_rejects_empty_file_and_removes_partial`
  - expect `DocumentFileInvalidError`;
  - assert staging is empty.
- `test_storage_rejects_oversized_file_and_removes_partial`
  - configure maximum `8`, upload `9` bytes;
  - expect `DocumentTooLargeError`;
  - assert no staged/final file remains.
- `test_storage_discard_helpers_are_idempotent`
  - discard the same staged and stored path twice;
  - assert neither call leaks an absolute path or raises for absence.
- `test_storage_rejects_managed_symlink_or_reparse_directory`
  - create a real symlink where supported, otherwise skip with the captured
    `OSError`;
  - expect `DocumentStorageError`.

- [x] **Step 3: Run RED for Settings and storage**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_config.py `
  tests/test_document_storage.py
```

Expected: collection/import or assertion failures because the new Settings
fields, errors, and storage module do not exist. Record the exact output.

- [x] **Step 4: Implement upload errors**

Create `app/knowledge/errors.py` with a `DocumentError(RuntimeError)` base and
the six named subclasses. Constructors use stable internal messages only; no
constructor includes file bytes, hash, absolute path, or original filename.

Export all error classes through `app.knowledge`.

- [x] **Step 5: Implement Settings**

In `config.py`:

```python
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    document_storage_root: Path = Field(
        default=BACKEND_ROOT / "uploads",
        alias="DOCUMENT_STORAGE_ROOT",
    )
    document_max_upload_bytes: int = Field(
        default=20_971_520,
        gt=0,
        le=1_073_741_824,
        alias="DOCUMENT_MAX_UPLOAD_BYTES",
    )
    document_max_files_per_knowledge_base: int = Field(
        default=50,
        gt=0,
        le=10_000,
        alias="DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE",
    )
```

Add a before-validator for `document_storage_root` that rejects blank strings,
converts values to `Path`, resolves relative values below `BACKEND_ROOT`, and
returns an absolute resolved path.

Add these exact tracked examples:

```dotenv
DOCUMENT_STORAGE_ROOT=./uploads
DOCUMENT_MAX_UPLOAD_BYTES=20971520
DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE=50
```

- [x] **Step 6: Declare and install multipart support**

Add:

```toml
"python-multipart>=0.0.18,<0.1.0",
```

to runtime dependencies. Install the verified project dependency set:

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[dev]" --no-build-isolation
```

If dependency download is blocked by sandbox/network policy, request the
required approval and do not fake install evidence.

- [x] **Step 7: Implement DocumentStorage**

Implement exactly the interfaces in the approved design. Required details:

- `UPLOAD_CHUNK_BYTES = 65_536`;
- suffix mapping `{".md": "md", ".txt": "txt", ".pdf": "pdf"}`;
- `tempfile.mkstemp(..., suffix=".part", dir=staging_directory)`;
- bounded loop using `await stream.read(UPLOAD_CHUNK_BYTES)`;
- reject non-`bytes` stream output as `DocumentStorageError`;
- update SHA-256 and size only for accepted chunks;
- remove the temp path in every failure branch;
- lower-case hexadecimal hash;
- create only `.staging` and UUID Knowledge Base directories;
- check managed directories with `lstat`, `Path.is_symlink`, and
  `is_reparse_point`;
- verify staged/final/cleanup candidates with `relative_to(self.root)`;
- use UUID-derived final paths and a same-filesystem rename;
- return POSIX relative paths;
- make discard idempotent for missing normal files;
- wrap unexpected I/O exceptions as `DocumentStorageError`.

No upload is written outside `DocumentStorage`.

- [x] **Step 8: Run GREEN for Settings and storage**

Run the same command from Step 3.

Expected: all config and storage tests pass. Record exact pass/warning counts.

- [x] **Step 9: Refactor only after GREEN**

Remove duplication in containment and cleanup helpers only. Re-run Step 8 after
any refactor.

- [x] **Step 10: Record Task 1 checkpoint**

Update this plan's observed evidence. Do not stage or commit.

---

### Task 2: DocumentService, Duplicate Policy, And Rollback Cleanup

**Files:**

- Create: `backend/app/services/document_service.py`
- Create: `backend/tests/test_document_service.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/api/dependencies.py`

**Interfaces:**

- Consumes:
  - `KnowledgeBaseService.get_knowledge_base(UUID)`;
  - `DocumentStorage.stage/promote/discard_*`;
  - `Settings.document_*`;
  - `Document` ORM.
- Produces:

```python
class DocumentService:
    def __init__(
        self,
        session: Session,
        *,
        storage: DocumentStorage,
        max_files_per_knowledge_base: int,
    ) -> None: ...

    async def upload_document(
        self,
        knowledge_base_id: UUID,
        *,
        original_filename: str | None,
        stream: AsyncReadable,
    ) -> Document: ...
```

- [x] **Step 1: Write failing service tests**

Create temporary SQLite/session/storage fixtures. Import all models before
`Base.metadata.create_all`.

Add these tests:

- `test_service_uploads_document_with_initial_states`
  - create one Knowledge Base;
  - upload `guide.md`;
  - assert generated UUID filename and relative file path;
  - assert original filename, type, size, hash, `uploaded`, `pending`,
    `pending`, empty metadata;
  - assert final file bytes;
  - commit and assert the file remains.
- `test_service_checks_knowledge_base_before_reading_stream`
  - use an unknown UUID and a stream whose `read` records calls;
  - expect `KnowledgeBaseNotFoundError`;
  - assert zero reads and no file.
- `test_service_rejects_document_limit_before_reading_stream`
  - configure limit `1`, pre-create one Document;
  - expect `KnowledgeBaseDocumentLimitReachedError`;
  - assert zero stream reads.
- `test_service_rejects_same_knowledge_base_duplicate`
  - commit the first upload;
  - upload the same bytes under another supported filename;
  - expect `DocumentDuplicateError`;
  - assert one DB row and no staging file.
- `test_service_allows_same_hash_in_different_knowledge_bases`
  - upload identical bytes to two Knowledge Bases;
  - assert two rows, independent paths, and two final files.
- `test_service_rolls_back_promoted_file`
  - upload without commit;
  - assert final file exists;
  - call `session.rollback()`;
  - assert final file is removed and no row remains.
- `test_service_commit_retains_promoted_file`
  - upload and commit;
  - call a later rollback;
  - assert committed file remains.
- `test_service_storage_failure_leaves_no_document`
  - configure storage root as an existing file or inject a failing storage;
  - expect `DocumentStorageError`;
  - assert zero Documents.

- [x] **Step 2: Run service RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_document_storage.py `
  tests/test_document_service.py
```

Expected: collection fails because `DocumentService` is absent. Record the
exact error.

- [x] **Step 3: Implement session cleanup callbacks**

Use module-level keys:

```python
_PENDING_DOCUMENT_FILES = "pending_document_files"
_DOCUMENT_FILE_LISTENERS = "document_file_listeners_registered"
```

The pending collection stores `(DocumentStorage, relative_path)` pairs in
`Session.info`.

Register exactly once per Session instance:

- `after_commit`: pop and forget the pending collection;
- `after_rollback`: pop, call `discard_stored` for every item, catch cleanup
  exceptions, and log `document_rollback_cleanup_failed` with
  `safe_stack_locations` but without file/path/hash data.

The listener marker remains for the Session lifetime so reused Sessions do not
accumulate listeners.

- [x] **Step 4: Implement DocumentService**

Implement the approved nine-step flow:

1. Knowledge Base lookup;
2. `count(Document.id)` by Knowledge Base and limit rejection;
3. stage;
4. duplicate `select(Document.id)` by Knowledge Base plus lowercase hash;
5. duplicate branch discards staging;
6. generate `document_id = uuid4()` and promote;
7. register final relative path before ORM flush;
8. add `Document` with generated/staged fields and existing defaults;
9. flush and return.

Use `try/finally` so any still-existing staging file is discarded. Do not
commit or parse the file.

- [x] **Step 5: Export and wire the service dependency**

Export `DocumentService` from `app.services`.

Add:

```python
def get_document_service(
    session: Session = Depends(get_db_session, scope="function"),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    storage = DocumentStorage(
        settings.document_storage_root,
        max_upload_bytes=settings.document_max_upload_bytes,
    )
    return DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=(
            settings.document_max_files_per_knowledge_base
        ),
    )
```

Do not initialize Provider or Qdrant dependencies.

- [x] **Step 6: Run service GREEN**

Run the Step 2 command.

Expected: all storage/service tests pass. Record exact output.

- [x] **Step 7: Run adjacent schema/model regression**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_config.py `
  tests/test_knowledge_models.py `
  tests/test_knowledge_schemas.py `
  tests/test_document_storage.py `
  tests/test_document_service.py
```

Expected: all pass. No migration is added.

- [x] **Step 8: Record Task 2 checkpoint**

Update this plan's observed evidence. Do not stage or commit.

---

### Task 3: Multipart Document Upload API And Safe Errors

**Files:**

- Create: `backend/app/api/v1/documents.py`
- Create: `backend/tests/test_document_api.py`
- Modify: `backend/app/api/errors.py`
- Modify: `backend/app/main.py`

**Interfaces:**

- Consumes:
  - multipart field `file: UploadFile`;
  - `get_document_service`;
  - `DocumentService.upload_document`;
  - `DocumentRead`.
- Produces:
  - `POST /api/v1/knowledge-bases/{knowledge_base_id}/documents`;
  - safe Document error mappings.

- [x] **Step 1: Write failing API fixture**

The fixture must:

- create a new temporary SQLite engine and `Base.metadata.create_all`;
- override `get_db_session` with commit/rollback/close behavior matching
  production;
- override `get_settings` with:
  - temporary storage root;
  - small synthetic byte limit large enough for success fixtures;
  - document limit `50`;
- use `TestClient`;
- clear dependency overrides and dispose the engine in `finally`.

- [x] **Step 2: Write failing OpenAPI and success tests**

Add:

- `test_openapi_exposes_only_nested_document_upload`
  - nested path methods are exactly `{"post"}`;
  - `/api/v1/documents` and chunk/delete paths remain absent;
  - request body is required multipart form data with required `file`.
- `test_document_upload_accepts_supported_types`
  - parametrize:
    - `guide.md`, `b"# Synthetic"`, `text/markdown`, expected `md`;
    - `notes.txt`, `b"Synthetic text"`, `text/plain`, expected `txt`;
    - `manual.pdf`, `b"%PDF-1.7 synthetic"`, `application/pdf`, expected `pdf`;
  - assert HTTP 201;
  - assert one Document row with correct states, size, and hash;
  - assert response `file_path` is relative;
  - assert final file contains exact bytes.
- `test_document_upload_sanitizes_client_path`
  - upload `C:\fakepath\guide.md`;
  - assert `original_filename == "guide.md"`;
  - assert stored filename/path contain only UUID components.

- [x] **Step 3: Write failing validation/error tests**

Add:

- absent multipart field -> 422 `validation_error`;
- empty file -> 400 `document_file_invalid`;
- `.csv` -> 415 `document_type_unsupported`;
- configured byte limit plus one -> 413 `document_too_large`;
- unknown Knowledge Base -> safe 404 and no stored file;
- second same-hash upload in one Knowledge Base -> 409
  `document_duplicate`, one row/file;
- configured one-document limit plus a unique second file -> 409
  `knowledge_base_document_limit_reached`;
- storage root failure -> 503 `document_storage_error`, no absolute path;
- commit failure with `FailingCommitSession` -> 503 `database_error`, zero rows,
  and no final/staging file.

For every safe-error test, assert the response does not contain:

- the configured absolute temp path;
- a computed SHA-256;
- the synthetic internal exception message;
- uploaded file content.

- [x] **Step 4: Run API RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_document_api.py
```

Expected: requests return the pre-route 404 surface or imports fail because the
router/error mappings do not exist. Record exact output.

- [x] **Step 5: Implement safe error mapping**

Map errors in this exact order before generic `SQLAlchemyError` and HTTP
fallbacks:

```text
DocumentFileInvalidError -> 400 / document_file_invalid
DocumentTooLargeError -> 413 / document_too_large
DocumentTypeUnsupportedError -> 415 / document_type_unsupported
DocumentDuplicateError -> 409 / document_duplicate
KnowledgeBaseDocumentLimitReachedError
  -> 409 / knowledge_base_document_limit_reached
DocumentStorageError -> 503 / document_storage_error
```

Use exactly the safe messages in the approved design. Register the
`DocumentError` base with the unified error handler.

- [x] **Step 6: Implement the thin route**

Create:

```python
router = APIRouter(tags=["documents"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    knowledge_base_id: UUID,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    document = await service.upload_document(
        knowledge_base_id,
        original_filename=file.filename,
        stream=file,
    )
    return DocumentRead.model_validate(document)
```

Register this router under the existing v1 prefix in `app.main`. Do not add any
other Document route.

- [x] **Step 7: Run API GREEN**

Run the Step 4 command.

Expected: all API tests pass with only the existing TestClient warning.

- [x] **Step 8: Run complete focused upload verification**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_config.py `
  tests/test_knowledge_models.py `
  tests/test_knowledge_schemas.py `
  tests/test_knowledge_base_service.py `
  tests/test_knowledge_base_api.py `
  tests/test_document_storage.py `
  tests/test_document_service.py `
  tests/test_document_api.py
```

Expected: all pass. Record exact count and warning.

- [x] **Step 9: Record Task 3 checkpoint**

Update this plan's observed evidence. Do not stage or commit.

---

### Task 4: Current Documentation And Batch Acceptance

**Files:**

- Modify: `backend/.env.example`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this plan

**Interfaces:**

- Consumes: verified S1～S3 runtime behavior.
- Produces: accurate operations/API/security/current-scope documentation.

- [x] **Step 1: Update current scope**

Change current completion statements from `P3-M1-S9` to `P3-M2-S3` without
claiming M2 or Plan 3 completion.

- [x] **Step 2: Document storage and API contracts**

Record:

- all three environment variables and defaults;
- runtime directory layout;
- relative path behavior;
- 20 MiB, 50-document, empty, suffix, hash, and same-KB duplicate policy;
- cross-Knowledge-Base identical-content behavior;
- concurrent same-hash uploads remain an accepted local-first limitation;
- POST route and safe errors;
- SQLite row versus local file ownership;
- request rollback cleanup and hard-crash orphan limitation;
- initial lifecycle states;
- absence of parsing, Chunking, Embedding, Qdrant client, retrieval, and
  frontend upload.

- [x] **Step 3: Update the active Plan**

Mark only Batch 4 and the Markdown/TXT/PDF upload acceptance rows implemented
after verification. Add dated RED/GREEN, regression, dependency, migration,
docs, secret, artifact, boundary, Git, and Codex self-review evidence. Keep
parser/cleaner/Chunker rows pending.

- [x] **Step 4: Run documentation pre-gates**

Require:

- every tracked/untracked Markdown link and image resolves;
- current completion statements end at `P3-M2-S3`;
- no document claims parsing or ingestion completion;
- upload settings and API paths match source;
- no real file, filename, path, content, hash, secret, or screenshot is
  committed.

- [x] **Step 5: Record Task 4 checkpoint**

Record exact Markdown/link counts after the command succeeds.

---

### Task 5: Full Verification And Codex Self-Review

**Files:**

- Modify: active Plan acceptance evidence
- Modify: this plan's observed evidence and checkboxes

- [x] **Step 1: Run complete backend regression**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

- [x] **Step 2: Run complete frontend regression**

From `frontend/`:

```powershell
npm run test
npm run typecheck
npm run build
```

- [x] **Step 3: Run a fresh temporary SQLite Alembic gate**

Create a unique system-temp directory, prove it is below the system temp root
and outside the workspace, set `DATABASE_URL` to its new SQLite path, then run:

```powershell
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c alembic.ini current --check-heads
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c alembic.ini check
```

Require `20260726_0005 (head)`, no new operations, and verified removal of the
temp root. Never target the user database.

- [x] **Step 4: Run repository/security/boundary gates**

Require:

- all Markdown links/images resolve;
- high-confidence added-line secret hits: `0`;
- real Provider host additions: `0`;
- tracked/untracked `.db`, `.sqlite`, uploaded document, `.part`, staging,
  cache, and frontend build artifacts: `0`;
- `web_fetch` production additions: `0`;
- parser/cleaner/Chunker/Embedding/Qdrant client/Retriever/frontend upload and
  Plan 4+ runtime additions: `0`;
- changed paths match an explicit S1～S3 allowlist;
- `git diff --check`: no findings;
- staged paths: `0`;
- branch remains `main`;
- `HEAD == origin/main ==
  943c3370119db6299484ab6aceda7e6d47870a25`;
- `v0.2.0^{}` remains
  `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`;
- `v0.2.1^{}` remains
  `872310b4dc1b78e2a2487303699d68ec8b22f88b`.

- [x] **Step 5: Perform Codex self-review**

Review:

- no absolute path or content leakage;
- storage containment and symlink/reparse handling;
- size loop cannot overrun configured bytes;
- temp files are removed on every normal error;
- UUID paths cannot use user components;
- duplicate scope is exactly one Knowledge Base;
- count limit occurs before stream consumption;
- route is thin;
- service flushes but never commits;
- successful commit retains files;
- rollback and commit failure remove new files;
- safe 400/404/409/413/415/503 mapping;
- only the upload POST exists;
- no ORM/migration or later-step expansion;
- docs match runtime.

Classify findings as must fix, later Step, accepted limitation, or not
applicable. Fix all must-fix items and rerun affected gates.

- [x] **Step 6: Prepare manual handoff**

State whether S1～S3 are complete and whether the repository may enter
`P3-M2-S4～S6`. Preserve the verified main working tree for manual commit.

Suggested commit message:

```text
feat(knowledge): add controlled document upload
```

## Observed Execution Evidence

- Planning baseline: clean `main` with
  `HEAD == origin/main == 943c3370119db6299484ab6aceda7e6d47870a25`;
  annotated Plan 2 tag targets remained unchanged.
- Task 1 RED: collection failed because Document upload errors/storage exports
  did not exist. Editable dependency installation initially failed because
  setuptools flat-layout discovery found both `app` and `alembic`; explicit
  `app*` package discovery fixed the root cause. `python-multipart 0.0.32` then
  installed successfully. Task 1 GREEN: `34 passed in 1.16s`.
- Task 2 RED: collection failed because `DocumentService` did not exist.
  Storage/service GREEN: `26 passed in 1.62s`; adjacent config/model/schema
  regression: `97 passed in 4.47s`.
- Task 3 RED: `20 failed, 1 warning` with the expected missing route/error
  mappings. Current FastAPI OpenAPI 3.1 represents the file with
  `contentMediaType`; after aligning the test with that framework contract,
  API GREEN reached `20 passed, 1 warning in 2.61s`. Focused upload regression:
  `136 passed, 1 warning in 8.49s`.
- Documentation gate: `88` Markdown files, `60` locally parsed links/images,
  `0` read/parse errors, and `0` missing targets.
- Complete backend after the Codex must-fix:
  `635 passed, 1 warning in 26.83s`; `pip check` reported
  `No broken requirements found`.
- Frontend: `18` files / `90` tests passed, typecheck succeeded, and the
  production build transformed `1813` modules.
- Temporary migration: `20260726_0005 (head)`,
  `No new upgrade operations detected`, and `temporary_root_removed=True`.
  The user database was not read or modified.
- Repository gates: `25` changed paths, `0` unexpected paths, `0` staged
  paths, `0` high-confidence secret hits, `0` real Provider hosts, `0`
  generated/upload/database artifacts, `0` production `web_fetch` hits, and
  `0` later-runtime paths. `git diff --check` had no findings and all Git refs
  matched the planning baseline.
- Codex self-review must-fix: restored the pre-existing `app.knowledge`
  ownership docstring; the affected collection reached `49 passed, 1 warning`
  before the full backend rerun. Later Steps, accepted limitations, and
  not-applicable findings are recorded in the active Plan 3 table.
