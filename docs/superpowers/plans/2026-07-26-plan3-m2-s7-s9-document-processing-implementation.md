# Plan 3 M2 S7～S9 Document Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Repository
> rules prohibit subagents for this batch. Do not stage, commit, push, tag, or
> create/switch branches; the user owns all Git mutations.

**Goal:** Add pure text cleaning and naive Chunking, then synchronously process
uploaded Markdown, TXT, and text-layer PDF files into persisted
`DocumentChunk` rows with visible final Document states.

**Architecture:** `app.rag.text_cleaner` and `app.rag.chunker` are pure,
database-independent processing units. `DocumentIngestionService` resolves the
controlled stored path, dispatches the existing parser, composes cleaning and
Chunking, applies lifecycle policy, and writes chunks. `DocumentService`
retains upload policy and calls ingestion after the initial Document flush;
the request Session remains the only commit/rollback owner.

**Tech Stack:** Python 3.11, dataclasses, pathlib, FastAPI, Pydantic Settings,
SQLAlchemy 2, SQLite, pytest, existing `pypdf`.

## Global Constraints

- Work only on `P3-M2-S7～S9`.
- Expected parser/content failures return HTTP 201 with a persisted failed
  Document and safe `error_message`.
- Storage, database, and unexpected programming failures propagate through
  existing safe API handling and roll back the Document, chunks, and promoted
  file.
- Default `RAG_CHUNK_SIZE=1000`; valid range is 100 through 10,000.
- Default `RAG_CHUNK_OVERLAP=150`; valid range is 0 through 2,000 and strictly
  less than chunk size.
- Do not add Document query/delete/retry APIs, workers, Embedding, Qdrant
  clients, Retriever, RAG runtime, frontend behavior, OCR, or Plan 4+ features.
- Use only temporary SQLite databases, temporary storage, and synthetic
  documents in tests.
- Never read, migrate, delete, or rebuild `backend/ai_agent_lab.db`.
- Write every behavior test first and watch the expected RED before production
  code.
- Use `apply_patch` for file edits.
- Do not stage or commit. Commit commands in generic skill guidance are
  intentionally omitted.

---

### Task 1: Pure Text Cleaner

**Files:**

- Create: `backend/tests/test_text_cleaner.py`
- Create: `backend/app/rag/text_cleaner.py`
- Modify: `backend/app/rag/__init__.py`

**Interfaces:**

- Consumes:
  `ParsedDocument(document_id, text, metadata, pages)` and `ParsedPage`.
- Produces:
  `clean_parsed_document(document: ParsedDocument) -> ParsedDocument`.
- The input object and its nested metadata must remain unchanged.

- [ ] **Step 1: Write the failing Cleaner tests**

Create `backend/tests/test_text_cleaner.py` with focused cases shaped like:

```python
from uuid import UUID

from app.rag import clean_parsed_document
from app.rag.parsers import ParsedDocument, ParsedPage


DOCUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_cleaner_normalizes_controls_and_blank_lines() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="\r\nAlpha\x00\u200b\r\n \t\r\n\r\nBeta\tvalue\ufeff\r",
        metadata={"format": "txt", "encoding": "utf-8"},
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.text == "Alpha\n\nBeta\tvalue"
    assert cleaned.metadata == original.metadata
    assert original.text.startswith("\r\n")


def test_cleaner_preserves_markdown_and_updates_heading_lines() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="\n\n# Title\n\n\n```py\n  value = 1\n```\n\n## Next",
        metadata={
            "format": "markdown",
            "headings": [
                {"level": 1, "text": "Title", "line_number": 3},
                {"level": 2, "text": "Next", "line_number": 10},
            ],
            "code_blocks": [],
        },
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.text == (
        "# Title\n\n```py\n  value = 1\n```\n\n## Next"
    )
    assert cleaned.metadata["headings"] == [
        {"level": 1, "text": "Title", "line_number": 1},
        {"level": 2, "text": "Next", "line_number": 7},
    ]


def test_cleaner_cleans_pdf_pages_independently() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text=" stale aggregate ",
        metadata={"format": "pdf", "page_count": 2},
        pages=(
            ParsedPage(page_number=1, text="\r\nPage one\r\n"),
            ParsedPage(page_number=2, text="\x00\r\n\r\nPage two"),
        ),
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.pages == (
        ParsedPage(page_number=1, text="Page one"),
        ParsedPage(page_number=2, text="Page two"),
    )
    assert cleaned.text == "Page one\n\nPage two"
```

Add separate assertions that TAB and `U+200D` remain, C0/C1 controls are
removed, and nested heading dictionaries are copied rather than mutated.

- [ ] **Step 2: Run Cleaner RED**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_text_cleaner.py -q
```

Expected: collection fails because `clean_parsed_document` does not exist.

- [ ] **Step 3: Implement the minimum Cleaner**

Create `backend/app/rag/text_cleaner.py` with these interfaces and algorithm:

```python
from copy import deepcopy

from app.rag.parsers import ParsedDocument, ParsedPage

_REMOVED_FORMAT_CHARACTERS = {"\ufeff", "\u200b", "\u2060"}


def clean_parsed_document(document: ParsedDocument) -> ParsedDocument:
    metadata = deepcopy(document.metadata)
    if document.pages is not None:
        pages = tuple(
            ParsedPage(
                page_number=page.page_number,
                text=_clean_text(page.text)[0],
            )
            for page in document.pages
        )
        return ParsedDocument(
            document_id=document.document_id,
            text="\n\n".join(page.text for page in pages),
            metadata=metadata,
            pages=pages,
        )

    text, line_mapping = _clean_text(document.text)
    headings = metadata.get("headings")
    if isinstance(headings, list):
        for heading in headings:
            if not isinstance(heading, dict):
                continue
            source_line = heading.get("line_number")
            if isinstance(source_line, int) and source_line in line_mapping:
                heading["line_number"] = line_mapping[source_line]
    return ParsedDocument(
        document_id=document.document_id,
        text=text,
        metadata=metadata,
    )


def _clean_text(text: str) -> tuple[str, dict[int, int]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    line_mapping: dict[int, int] = {}
    for source_line, raw_line in enumerate(normalized.split("\n"), start=1):
        line = "".join(
            character
            for character in raw_line
            if _keep_character(character)
        )
        if not line.strip():
            if output and output[-1] != "":
                output.append("")
            continue
        output.append(line)
        line_mapping[source_line] = len(output)
    while output and output[-1] == "":
        output.pop()
    return "\n".join(output), line_mapping


def _keep_character(character: str) -> bool:
    if character == "\t":
        return True
    codepoint = ord(character)
    if codepoint < 32 or 127 <= codepoint <= 159:
        return False
    return character not in _REMOVED_FORMAT_CHARACTERS
```

Export `clean_parsed_document` from `backend/app/rag/__init__.py`.

- [ ] **Step 4: Run Cleaner GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_text_cleaner.py -q
```

Expected: all Cleaner tests pass.

- [ ] **Step 5: Refactor only after GREEN**

Keep helpers private, keep input immutability explicit, and rerun the same
command.

### Task 2: Chunk Settings and Pure Chunker

**Files:**

- Create: `backend/tests/test_chunker.py`
- Modify: `backend/tests/test_config.py`
- Create: `backend/app/rag/chunker.py`
- Modify: `backend/app/rag/__init__.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`

**Interfaces:**

- Consumes:
  `chunk_document(ParsedDocument, chunk_size=int, chunk_overlap=int)`.
- Produces:
  `tuple[DocumentChunkDraft, ...]`.
- Raises:
  `DocumentContentEmptyError("Document contains no usable text.")`.

- [ ] **Step 1: Write failing Settings tests**

Extend `backend/tests/test_config.py`:

```python
def test_settings_default_rag_chunk_bounds() -> None:
    settings = Settings(_env_file=None)

    assert settings.rag_chunk_size == 1000
    assert settings.rag_chunk_overlap == 150


@pytest.mark.parametrize(
    ("size", "overlap"),
    [(99, 0), (10_001, 0), (1000, -1), (1000, 1000), (1000, 2001)],
)
def test_settings_rejects_invalid_rag_chunk_bounds(
    size: int,
    overlap: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            RAG_CHUNK_SIZE=size,
            RAG_CHUNK_OVERLAP=overlap,
        )
```

- [ ] **Step 2: Run Settings RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_config.py -q
```

Expected: failures show missing chunk settings.

- [ ] **Step 3: Implement validated Settings**

In `backend/app/core/config.py`, add bounded fields and an after-model
validator:

```python
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator

rag_chunk_size: int = Field(
    default=1000,
    ge=100,
    le=10_000,
    alias="RAG_CHUNK_SIZE",
)
rag_chunk_overlap: int = Field(
    default=150,
    ge=0,
    le=2_000,
    alias="RAG_CHUNK_OVERLAP",
)

@model_validator(mode="after")
def validate_rag_chunk_window(self) -> Self:
    if self.rag_chunk_overlap >= self.rag_chunk_size:
        raise ValueError("RAG chunk overlap must be smaller than chunk size")
    return self
```

Append only non-secret defaults to `backend/.env.example`:

```text
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=150
```

- [ ] **Step 4: Run Settings GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_config.py -q
```

- [ ] **Step 5: Write failing Chunker tests**

Create `backend/tests/test_chunker.py`. Cover these exact behaviors:

```python
def test_chunker_returns_one_ordered_draft_for_short_text() -> None:
    document = parsed_txt("Short content")

    chunks = chunk_document(
        document,
        chunk_size=100,
        chunk_overlap=10,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "Short content"
    assert chunks[0].char_count == len("Short content")
    assert chunks[0].token_count == 4
    assert chunks[0].metadata == {
        "source_format": "txt",
        "start_char": 0,
        "end_char": 13,
    }


def test_chunker_prefers_paragraph_boundary_and_overlaps() -> None:
    text = ("A" * 60) + "\n\n" + ("B" * 45) + ("C" * 30)
    chunks = chunk_document(
        parsed_txt(text),
        chunk_size=100,
        chunk_overlap=10,
    )

    assert chunks[0].content.endswith("\n\n")
    assert chunks[1].content.startswith(chunks[0].content[-10:])
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunker_preserves_markdown_heading() -> None:
    document = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="# First\nBody\n\n## Second\nMore",
        metadata={
            "format": "markdown",
            "headings": [
                {"level": 1, "text": "First", "line_number": 1},
                {"level": 2, "text": "Second", "line_number": 4},
            ],
        },
    )

    chunks = chunk_document(document, chunk_size=12, chunk_overlap=2)

    assert chunks[0].heading == "First"
    assert any(chunk.heading == "Second" for chunk in chunks)
    assert any(
        chunk.metadata.get("heading_level") == 2 for chunk in chunks
    )


def test_chunker_keeps_pdf_pages_separate() -> None:
    document = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="Page one\n\nPage two",
        metadata={"format": "pdf", "page_count": 2},
        pages=(
            ParsedPage(page_number=1, text="Page one"),
            ParsedPage(page_number=2, text="Page two"),
        ),
    )

    chunks = chunk_document(document, chunk_size=100, chunk_overlap=10)

    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert [chunk.content for chunk in chunks] == ["Page one", "Page two"]
```

Also cover:

- hard boundary when no newline exists;
- zero overlap;
- invalid size/overlap;
- monotonic progress;
- UTF-8 byte-based token estimate for Chinese;
- whitespace-only document raises `DocumentContentEmptyError`;
- an empty PDF page creates no chunk and does not affect the next page's
  overlap or page number.

- [ ] **Step 6: Run Chunker RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chunker.py -q
```

Expected: collection fails because `chunk_document` and its contracts do not
exist.

- [ ] **Step 7: Implement the minimum Chunker**

Create `backend/app/rag/chunker.py` with:

```python
from bisect import bisect_right
from dataclasses import dataclass
from math import ceil

from app.rag.parsers import ParsedDocument


class DocumentContentEmptyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Document contains no usable text.")


@dataclass(frozen=True)
class DocumentChunkDraft:
    chunk_index: int
    content: str
    token_count: int
    char_count: int
    heading: str | None
    page_number: int | None
    metadata: dict[str, object]


def chunk_document(
    document: ParsedDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[DocumentChunkDraft, ...]:
    _validate_window(chunk_size, chunk_overlap)
    if not document.text.strip():
        raise DocumentContentEmptyError()
    # PDF: iterate nonblank pages independently.
    # Markdown/TXT: process one document-level segment.
    # Assign global zero-based indices after all segments are split.
```

Private helpers must:

- calculate the latter-half paragraph/newline boundary;
- return `(start, end, content)` values with monotonic progress;
- convert Markdown heading line numbers to character offsets;
- use `bisect_right` to select the heading active at chunk start;
- set page-relative PDF offsets;
- calculate `max(1, ceil(len(content.encode("utf-8")) / 4))`.

Export `DocumentChunkDraft`, `DocumentContentEmptyError`, and `chunk_document`
from `backend/app/rag/__init__.py`.

- [ ] **Step 8: Run Chunker GREEN and Cleaner regression**

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_chunker.py `
  tests/test_text_cleaner.py `
  tests/test_config.py -q
```

Expected: all tests pass.

### Task 3: Controlled Stored-Path Resolver

**Files:**

- Modify: `backend/tests/test_document_storage.py`
- Modify: `backend/app/knowledge/document_storage.py`

**Interfaces:**

- Produces:
  `DocumentStorage.resolve_stored(relative_path, *, knowledge_base_id,
  document_id, file_type) -> Path`.
- Raises:
  existing `DocumentStorageError`.

- [ ] **Step 1: Write failing resolver tests**

Extend `backend/tests/test_document_storage.py`:

```python
def test_storage_resolves_existing_uuid_owned_file(tmp_path: Path) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    stored = promote_synthetic_document(storage)

    resolved = storage.resolve_stored(
        stored.relative_path,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        file_type="txt",
    )

    assert resolved == storage.root / Path(stored.relative_path)
    assert resolved.is_file()


@pytest.mark.parametrize(
    "relative_path",
    [
        "../outside.txt",
        "not-a-uuid/file.txt",
        "11111111-1111-4111-8111-111111111111/not-a-uuid.txt",
        "11111111-1111-4111-8111-111111111111/"
        "22222222-2222-4222-8222-222222222222.exe",
    ],
)
def test_storage_rejects_invalid_stored_path(
    tmp_path: Path,
    relative_path: str,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)

    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            relative_path,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            file_type="txt",
        )
```

Also test:

- a valid path whose Knowledge Base ID, Document ID, or suffix differs from the
  supplied expected ownership values;
- missing files and directories;
- a root, Knowledge Base parent directory, or final file symlink/reparse point
  when the platform permits creating one.

- [ ] **Step 2: Run resolver RED**

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_document_storage.py -q
```

Expected: failures show `resolve_stored` is missing.

- [ ] **Step 3: Implement resolver by reusing path grammar**

Refactor the existing stored-path validation into one private helper and add:

```python
def resolve_stored(
    self,
    relative_path: str,
    *,
    knowledge_base_id: UUID,
    document_id: UUID,
    file_type: Literal["md", "txt", "pdf"],
) -> Path:
    try:
        path = self._stored_path(
            relative_path,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            file_type=file_type,
        )
        self._validate_managed_directory(self._root)
        self._validate_managed_directory(path.parent)
        path_stat = path.lstat()
        if (
            path.is_symlink()
            or is_reparse_point(path_stat)
            or not path.is_file()
        ):
            raise DocumentStorageError()
        return path
    except DocumentError:
        raise
    except (OSError, ValueError) as exc:
        raise DocumentStorageError() from exc
```

The private `_stored_path()` must compare both UUID components and suffix to
the supplied values. Make `discard_stored()` use the same root/parent
symlink/reparse checks before unlinking, while deriving its expected ownership
values from the already validated relative path. Do not broaden the accepted
layout.

- [ ] **Step 4: Run storage GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_document_storage.py -q
```

### Task 4: Document Ingestion Service

**Files:**

- Create: `backend/tests/test_document_ingestion_service.py`
- Create: `backend/app/services/document_ingestion_service.py`
- Modify: `backend/app/services/__init__.py`

**Interfaces:**

- Consumes:
  `Session`, `DocumentStorage`, chunk size, overlap, and a just-created
  `Document`.
- Produces:
  `process_document(document: Document) -> Document`.
- Persists:
  ordered `DocumentChunk` rows through `Session.flush()`.

- [ ] **Step 1: Write failing success-path service tests**

Create a temporary SQLite fixture and controlled upload fixture in
`backend/tests/test_document_ingestion_service.py`. The first test must assert:

```python
service = DocumentIngestionService(
    session,
    storage=storage,
    chunk_size=100,
    chunk_overlap=10,
)

processed = service.process_document(document)

assert processed.parse_status == "parsed"
assert processed.chunk_status == "chunked"
assert processed.embedding_status == "pending"
assert processed.error_message is None
assert processed.metadata_json["format"] == "markdown"
chunks = session.scalars(
    select(DocumentChunk)
    .where(DocumentChunk.document_id == document.id)
    .order_by(DocumentChunk.chunk_index)
).all()
assert chunks
assert chunks[0].knowledge_base_id == document.knowledge_base_id
assert chunks[0].heading == "Title"
```

Add TXT and PDF cases. PDF assertions must prove chunks do not cross pages and
persist positive page numbers.

- [ ] **Step 2: Run ingestion service RED**

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_document_ingestion_service.py -q
```

Expected: collection fails because `DocumentIngestionService` does not exist.

- [ ] **Step 3: Implement success flow**

Create `backend/app/services/document_ingestion_service.py`:

```python
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.knowledge import DocumentStorage
from app.models import Document, DocumentChunk
from app.rag import clean_parsed_document, chunk_document
from app.rag.parsers import (
    ParsedDocument,
    parse_markdown,
    parse_pdf,
    parse_txt,
)

Parser = Callable[..., ParsedDocument]

_PARSERS: dict[str, Parser] = {
    "md": parse_markdown,
    "txt": parse_txt,
    "pdf": parse_pdf,
}


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        *,
        storage: DocumentStorage,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self._session = session
        self._storage = storage
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def process_document(self, document: Document) -> Document:
        document.parse_status = "parsing"
        document.chunk_status = "pending"
        document.error_message = None
        path = self._storage.resolve_stored(
            document.file_path,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            file_type=document.file_type,
        )
        parsed = _PARSERS[document.file_type](
            path,
            document_id=document.id,
        )
        document.parse_status = "parsed"
        cleaned = clean_parsed_document(parsed)
        document.metadata_json = dict(cleaned.metadata)
        document.chunk_status = "chunking"
        drafts = chunk_document(
            cleaned,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        for draft in drafts:
            self._session.add(
                DocumentChunk(
                    document_id=document.id,
                    knowledge_base_id=document.knowledge_base_id,
                    chunk_index=draft.chunk_index,
                    content=draft.content,
                    token_count=draft.token_count,
                    char_count=draft.char_count,
                    heading=draft.heading,
                    page_number=draft.page_number,
                    metadata_json=dict(draft.metadata),
                )
            )
        document.chunk_status = "chunked"
        self._session.flush()
        return document
```

Export the service from `backend/app/services/__init__.py`.

- [ ] **Step 4: Run success-path GREEN**

Run only the new success tests. Expected: they pass.

- [ ] **Step 5: Write failing expected-content tests**

Add tests proving:

- invalid TXT bytes produce `failed/failed`, the exact safe parser message,
  and zero chunks;
- valid scanned/text-empty PDF produces the explicit OCR limitation and zero
  chunks;
- whitespace-only TXT produces `parsed/failed`,
  `"Document contains no usable text."`, metadata format `txt`, and zero
  chunks;
- low-level paths or byte contents are absent from stored messages.

- [ ] **Step 6: Run expected-content RED**

Expected: current implementation raises instead of returning a failed Document.

- [ ] **Step 7: Implement precise failure handling**

Wrap parser dispatch only with `except DocumentParseError`, and wrap cleaning/
Chunking only with `except DocumentContentEmptyError`. Add private markers:

```python
def _mark_parse_failed(
    self,
    document: Document,
    error: DocumentParseError,
) -> Document:
    document.parse_status = "failed"
    document.chunk_status = "failed"
    document.error_message = str(error)
    self._session.flush()
    return document


def _mark_chunk_failed(
    self,
    document: Document,
    error: DocumentContentEmptyError,
) -> Document:
    document.parse_status = "parsed"
    document.chunk_status = "failed"
    document.error_message = str(error)
    self._session.flush()
    return document
```

Do not catch `DocumentStorageError`, `SQLAlchemyError`, `KeyError`, or a generic
`Exception`.

- [ ] **Step 8: Run full ingestion service GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_document_ingestion_service.py `
  tests/test_chunker.py `
  tests/test_text_cleaner.py -q
```

### Task 5: Synchronous Upload Integration

**Files:**

- Modify: `backend/tests/test_document_service.py`
- Modify: `backend/tests/test_document_api.py`
- Create: `backend/tests/pdf_factory.py`
- Modify: `backend/tests/test_pdf_parser.py`
- Modify: `backend/app/services/document_service.py`
- Modify: `backend/app/api/dependencies.py`

**Interfaces:**

- `DocumentService.__init__` additionally consumes validated `chunk_size` and
  `chunk_overlap`.
- Existing upload API signature and `DocumentRead` response schema remain
  unchanged.

- [ ] **Step 1: Refactor the synthetic PDF test helper**

Move `_pdf_string()` and `_build_pdf()` unchanged from
`backend/tests/test_pdf_parser.py` into `backend/tests/pdf_factory.py`, export
`build_pdf`, and update the parser test import. Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_pdf_parser.py -q
```

Expected: existing PDF parser tests remain green. This is a test-only refactor,
not new production behavior.

- [ ] **Step 2: Write failing DocumentService integration tests**

Update the initial-state upload test to require final synchronous state:

```python
assert document.parse_status == "parsed"
assert document.chunk_status == "chunked"
assert document.embedding_status == "pending"
assert document.metadata_json["format"] == "markdown"
assert session.scalar(
    select(func.count(DocumentChunk.id)).where(
        DocumentChunk.document_id == document.id
    )
) >= 1
```

Add an invalid TXT case requiring a retained failed Document and zero chunks.

- [ ] **Step 3: Write failing API acceptance tests**

Change the supported-format parametrization to use valid Markdown, TXT, and
`build_pdf(["Synthetic PDF"])`. Assert:

```python
assert payload["parse_status"] == "parsed"
assert payload["chunk_status"] == "chunked"
assert payload["embedding_status"] == "pending"
assert payload["error_message"] is None
assert payload["metadata"]["format"] == expected_format
```

Query temporary SQLite inside the fixture and assert ordered chunks exist.

Add:

- scanned PDF returns HTTP 201, `failed/failed`, safe OCR message, and zero
  chunks;
- invalid TXT returns HTTP 201, `failed/failed`, safe generic parser message,
  and zero chunks;
- whitespace TXT returns HTTP 201, `parsed/failed`, safe empty-content message,
  and zero chunks;
- commit failure deletes the file and leaves both Document and Chunk counts
  zero.

- [ ] **Step 4: Run upload integration RED**

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_document_service.py `
  tests/test_document_api.py -q
```

Expected: state/chunk assertions fail because upload does not invoke ingestion.

- [ ] **Step 5: Wire DocumentService**

Extend the constructor:

```python
def __init__(
    self,
    session: Session,
    *,
    storage: DocumentStorage,
    max_files_per_knowledge_base: int,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> None:
    ...
    self._ingestion = DocumentIngestionService(
        session,
        storage=storage,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
```

After the initial Document flush:

```python
self._session.flush()
return self._ingestion.process_document(document)
```

The defaults preserve direct service-test construction while FastAPI passes
validated Settings explicitly.

- [ ] **Step 6: Wire FastAPI dependency**

In `get_document_service()` pass:

```python
chunk_size=settings.rag_chunk_size,
chunk_overlap=settings.rag_chunk_overlap,
```

Do not modify the route.

- [ ] **Step 7: Run upload integration GREEN**

Run the command from Step 4. Expected: all pass apart from the existing
Starlette TestClient warning.

- [ ] **Step 8: Run complete M2 focused regression**

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_config.py `
  tests/test_document_storage.py `
  tests/test_markdown_parser.py `
  tests/test_txt_parser.py `
  tests/test_pdf_parser.py `
  tests/test_text_cleaner.py `
  tests/test_chunker.py `
  tests/test_document_ingestion_service.py `
  tests/test_document_service.py `
  tests/test_document_api.py `
  tests/test_knowledge_models.py `
  tests/test_knowledge_schemas.py -q
```

### Task 6: Documentation, Verification, and Codex Self-Review

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify:
  `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this implementation plan with observed evidence

**Interfaces:**

- Documentation must describe actual runtime behavior only.
- Batch completion permits `P3-M3-S1～S3` but does not start M3.

- [ ] **Step 1: Update formal documentation**

Record:

- exact Cleaner policy;
- chunk defaults, bounds, boundary preference, provenance, and token heuristic;
- synchronous upload final states;
- expected content failures returning HTTP 201 failed Documents;
- infrastructure rollback behavior;
- M2 completion and all remaining M3+ limitations.

- [ ] **Step 2: Run dependency integrity**

```powershell
..\.venv\Scripts\python.exe -m pip check
```

Expected: `No broken requirements found.`

- [ ] **Step 3: Run full backend regression**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

Record exact pass and warning totals.

- [ ] **Step 4: Run frontend regression**

From `frontend/`:

```powershell
npm test -- --run
npm run typecheck
npm run build
```

Record exact file/test/module totals.

- [ ] **Step 5: Run fresh temporary SQLite migration checks**

Create and validate a new directory under the system temporary root. Point
`DATABASE_URL` only at its SQLite file and run:

```powershell
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic upgrade head
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic current --check-heads
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic check
```

Verify the resolved cleanup target remains below the system temporary root,
remove only that directory, and prove it no longer exists. Never point Alembic
at `backend/ai_agent_lab.db`.

- [ ] **Step 6: Run documentation/link verification**

Count all Markdown files excluding `.git`, `.venv`, `node_modules`, `dist`, and
runtime uploads. Parse local Markdown links/images, report read errors and
missing targets, and require both counts to be zero.

- [ ] **Step 7: Run repository security and boundary gates**

Verify:

- exact changed-path allowlist;
- added-line high-confidence secret matches are zero;
- added-line real HTTP Provider hosts are zero;
- generated PDF/database/upload/cache artifacts are zero;
- production `web_fetch`, Embedding, Qdrant client, Retriever, OCR, frontend
  RAG, and Plan 4+ runtime additions are zero;
- `git diff --check` has no findings;
- staged paths remain zero;
- `HEAD == origin/main`;
- peeled `v0.2.0` and `v0.2.1` targets remain unchanged.

- [ ] **Step 8: Perform Codex self-review**

Review:

- Cleaner does not corrupt Markdown/code or mutate parser input;
- Chunker terminates, respects bounds, and preserves heading/page provenance;
- expected content errors cannot hide storage/database/programming defects;
- Document/chunk/file transaction behavior is coherent;
- API remains thin and safe;
- docs match runtime;
- no M3 or later capability exists.

Classify every finding as:

- must fix;
- later Step;
- accepted limitation;
- not applicable.

Fix all must-fix findings and rerun affected focused and full gates.

- [ ] **Step 9: Prepare manual handoff**

State:

- whether S7～S9 and M2 are complete;
- exact verification evidence;
- remaining limitations;
- whether the repository may enter `P3-M3-S1～S3`;
- suggested commit message.

Do not stage or commit.

Suggested commit message:

```text
feat(rag): add document processing pipeline
```

## Observed Completion Evidence

Implemented on the clean `main` baseline
`39c901efb91d0ccdee49bae950b12106edd21a71` without staging, committing,
branching, pushing, or moving tags.

- Cleaner RED failed at import; GREEN was `4 passed`.
- Settings RED had six expected failures; GREEN was `22 passed`.
- Chunker RED failed at import; Cleaner/config/Chunker GREEN was `40 passed`.
- stored-path resolver RED was `12 failed, 18 passed`; GREEN was `30 passed`.
- ingestion success RED failed at import; success GREEN was `3 passed`.
- expected-content RED was `3 failed, 3 passed`; precise handling then passed.
- upload integration RED had eight new failures with 24 prior tests passing;
  GREEN was `32 passed, 1 warning`.
- complete M2 focused regression was `179 passed, 1 warning`.
- final backend regression was `698 passed, 1 warning`; dependency integrity
  reported `No broken requirements found`.
- frontend verification was `18` files / `90` tests, successful typecheck, and
  a production build with `1813` transformed modules.
- a fresh temporary SQLite reached Alembic `20260726_0005 (head)`,
  `current --check-heads` and `alembic check` passed, and its verified
  temporary directory was removed.
- documentation verification found `92` Markdown files, `69` local
  links/images, zero read errors, and zero missing targets.
- all 27 changed paths matched the batch allowlist; high-confidence secret,
  real Provider host, generated artifact, later-runtime path, and prohibited
  production-capability scans returned zero.
- `git diff --check` passed; staged paths remained zero; `HEAD == origin/main`;
  peeled `v0.2.0` and `v0.2.1` targets remained unchanged.

Codex self-review must-fix items were limited to test isolation, explicit chunk
rollback coverage, infrastructure-error propagation coverage, and stale
documentation; all were corrected and reverified. M3 Embedding/Vector Store,
later Document query/delete/file-lifecycle work, M4 retrieval/RAG, frontend
work, OCR, and Plan 4+ capabilities remain outside this batch.
