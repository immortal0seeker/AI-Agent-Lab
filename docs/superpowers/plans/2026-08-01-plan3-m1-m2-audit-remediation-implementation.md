# Plan 3 M1/M2 Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Repository policy forbids subagents for this batch. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 修复 Plan 3 M1/M2 整体审核确认的配置暴露、路径边界、Markdown 元数据、资源放大、删除语义和数据库完整性问题，使 M1/M2 可重新封板。

**Architecture:** 保持现有同步上传与薄 API route，新增不可变 processing-limit 契约并注入 parser/chunker；由 storage、service 和数据库约束分别承担路径、业务与最终一致性边界。使用新增 Alembic 补丁 revision 演进已提交 schema，不改写 `20260726_0005`。

**Tech Stack:** Python 3.11、FastAPI、Pydantic Settings、SQLAlchemy 2、Alembic、SQLite、pypdf、pytest、Docker Compose、React/TypeScript/Vitest/Vite。

## Global Constraints

- 只审核和修复 `P3-M1`、`P3-M2`；不得开始 M3、Embedding、Qdrant 数据写入、Retriever 或 RAG API。
- Qdrant 只承担 Plan 3 向量存储职责；SQLite 继续作为默认且长期支持的主数据库。
- 不读取、迁移、删除或重建 `backend/ai_agent_lab.db`；数据库测试只用新建临时 SQLite。
- 不读取真实 `.env`、secret、API key 或工作区外敏感路径；不调用真实 Provider、付费服务或网络 Tool。
- 文件测试只使用 pytest 临时目录和合成 `.md`、`.txt`、`.pdf` 内容。
- 默认限制必须是：PDF `500` 页、提取文本 `10000000` 字符、Markdown 结构 `20000` 项、单文档 `10000` chunks。
- 配置上界必须是：PDF `10000` 页、提取文本 `100000000` 字符、Markdown 结构 `100000` 项、chunks `100000`。
- 非空 Knowledge Base 删除必须返回 409，并保持 Knowledge Base、Document、DocumentChunk 和受控文件不变。
- API route 保持薄；业务判断进入 service；必要注释使用中文且只解释非显然边界。
- 不创建或切换分支，不 stage、commit、push 或 tag；每个任务只做只读 Git checkpoint，最终由用户手动提交。
- 不使用子代理、Claude Code、Fable 5 或外部 review；Codex self-review 是唯一 gate。

---

## File Map

### Create

- `backend/app/rag/processing_limits.py` — 不可变限制值与安全超限错误。
- `backend/alembic/versions/20260801_0006_plan3_m1_m2_audit_remediation.py` — Document 删除/哈希唯一性与 RagQuery answer 外键补丁。
- `docs/reviews/2026-08-01-plan3-m1-m2-audit-remediation-review.md` — 已确认问题、修复证据、限制和 review 分类。

### Modify: configuration and storage

- `docker-compose.yml`
- `backend/app/core/config.py`
- `backend/.env.example`
- `backend/app/api/dependencies.py`
- `backend/app/knowledge/document_storage.py`
- `backend/tests/test_plan3_foundation.py`
- `backend/tests/test_config.py`
- `backend/tests/test_document_storage.py`

### Modify: parsing and processing

- `backend/app/rag/__init__.py`
- `backend/app/rag/parsers/markdown_parser.py`
- `backend/app/rag/parsers/txt_parser.py`
- `backend/app/rag/parsers/pdf_parser.py`
- `backend/app/rag/text_cleaner.py`
- `backend/app/rag/chunker.py`
- `backend/app/services/document_ingestion_service.py`
- `backend/app/services/document_service.py`
- `backend/tests/test_markdown_parser.py`
- `backend/tests/test_txt_parser.py`
- `backend/tests/test_pdf_parser.py`
- `backend/tests/test_text_cleaner.py`
- `backend/tests/test_chunker.py`
- `backend/tests/test_document_ingestion_service.py`
- `backend/tests/test_document_service.py`

### Modify: database and API behavior

- `backend/app/models/knowledge_base.py`
- `backend/app/models/document.py`
- `backend/app/models/rag_query.py`
- `backend/app/models/message.py`
- `backend/app/services/errors.py`
- `backend/app/services/__init__.py`
- `backend/app/services/knowledge_base_service.py`
- `backend/app/api/errors.py`
- `backend/tests/test_knowledge_models.py`
- `backend/tests/test_knowledge_migration.py`
- `backend/tests/test_knowledge_base_service.py`
- `backend/tests/test_knowledge_base_api.py`
- `backend/tests/test_error_handling.py`

### Modify: formal documentation

- `README.md`
- `README_CN.md`
- `CHANGELOG.md`
- `docs/01-architecture.md`
- `docs/20-knowledge-base-design.md`
- `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- `docs/superpowers/plans/2026-08-01-plan3-m1-m2-audit-remediation-implementation.md`

---

### Task 1: Lock Qdrant and configuration limits

**Files:**

- Create: `backend/app/rag/processing_limits.py`
- Modify: `docker-compose.yml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/rag/__init__.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_plan3_foundation.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**

- Produces: `DocumentProcessingLimits(max_pdf_pages, max_extracted_characters, max_markdown_structures, max_chunks)`.
- Produces: `DocumentProcessingLimitError` with fixed message `Document exceeds the processing limit.`.
- Produces: `Settings.document_processing_limits -> DocumentProcessingLimits`.
- Consumed later by all parsers, `chunk_document()` and `DocumentIngestionService`.

- [x] **Step 1: Change the Compose assertion and add failing Settings/limit tests**

Replace the old port assertion and add these contracts:

```python
def test_qdrant_compose_contract() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(
        encoding="utf-8"
    )

    assert "qdrant/qdrant:v1.15.4" in compose
    assert '"127.0.0.1:6333:6333"' in compose
    assert '"6333:6333"' not in compose
    assert "qdrant_data:/qdrant/storage" in compose
    assert "\n  qdrant_data:\n" in compose
    assert 'QDRANT__TELEMETRY_DISABLED: "true"' in compose


def test_settings_default_document_processing_limits() -> None:
    settings = Settings(_env_file=None)

    assert settings.document_max_pdf_pages == 500
    assert settings.document_max_extracted_characters == 10_000_000
    assert settings.document_max_markdown_structures == 20_000
    assert settings.document_max_chunks == 10_000
    assert settings.document_processing_limits.max_pdf_pages == 500


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("DOCUMENT_MAX_PDF_PAGES", 0),
        ("DOCUMENT_MAX_PDF_PAGES", 10_001),
        ("DOCUMENT_MAX_EXTRACTED_CHARACTERS", 0),
        ("DOCUMENT_MAX_EXTRACTED_CHARACTERS", 100_000_001),
        ("DOCUMENT_MAX_MARKDOWN_STRUCTURES", 0),
        ("DOCUMENT_MAX_MARKDOWN_STRUCTURES", 100_001),
        ("DOCUMENT_MAX_CHUNKS", 0),
        ("DOCUMENT_MAX_CHUNKS", 100_001),
    ],
)
def test_settings_rejects_invalid_document_processing_limits(
    field_name: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})
```

- [x] **Step 2: Run RED tests**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_plan3_foundation.py tests/test_config.py -q
```

Expected: failures for the old Compose bind and missing processing-limit Settings fields/property.

- [x] **Step 3: Add the immutable limit contract**

Create `backend/app/rag/processing_limits.py`:

```python
from dataclasses import dataclass


class DocumentProcessingLimitError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Document exceeds the processing limit.")


@dataclass(frozen=True)
class DocumentProcessingLimits:
    max_pdf_pages: int = 500
    max_extracted_characters: int = 10_000_000
    max_markdown_structures: int = 20_000
    max_chunks: int = 10_000

    def __post_init__(self) -> None:
        for value in (
            self.max_pdf_pages,
            self.max_extracted_characters,
            self.max_markdown_structures,
            self.max_chunks,
        ):
            if value <= 0:
                raise ValueError("document processing limits must be positive")


DEFAULT_DOCUMENT_PROCESSING_LIMITS = DocumentProcessingLimits()
```

Export all three names from `backend/app/rag/__init__.py`.

- [x] **Step 4: Add exact Settings limit fields**

Add the four `Field` declarations to `Settings`:

```python
document_max_pdf_pages: int = Field(
    default=500, gt=0, le=10_000, alias="DOCUMENT_MAX_PDF_PAGES"
)
document_max_extracted_characters: int = Field(
    default=10_000_000,
    gt=0,
    le=100_000_000,
    alias="DOCUMENT_MAX_EXTRACTED_CHARACTERS",
)
document_max_markdown_structures: int = Field(
    default=20_000,
    gt=0,
    le=100_000,
    alias="DOCUMENT_MAX_MARKDOWN_STRUCTURES",
)
document_max_chunks: int = Field(
    default=10_000, gt=0, le=100_000, alias="DOCUMENT_MAX_CHUNKS"
)
```

Add:

```python
@property
def document_processing_limits(self) -> DocumentProcessingLimits:
    return DocumentProcessingLimits(
        max_pdf_pages=self.document_max_pdf_pages,
        max_extracted_characters=self.document_max_extracted_characters,
        max_markdown_structures=self.document_max_markdown_structures,
        max_chunks=self.document_max_chunks,
    )
```

- [x] **Step 5: Wire configuration and examples**

Change Compose to:

```yaml
ports:
  - "127.0.0.1:6333:6333"
```

Append to `backend/.env.example`:

```text
DOCUMENT_MAX_PDF_PAGES=500
DOCUMENT_MAX_EXTRACTED_CHARACTERS=10000000
DOCUMENT_MAX_MARKDOWN_STRUCTURES=20000
DOCUMENT_MAX_CHUNKS=10000
```

- [x] **Step 6: Run GREEN tests and a Compose syntax check**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_plan3_foundation.py tests/test_config.py -q
Set-Location ..
docker compose config --quiet
Set-Location backend
```

Expected: tests pass and Compose exits 0. If the Docker CLI/daemon is unavailable, record the exact failure; do not replace it with claimed health evidence.

- [x] **Step 7: Checkpoint without Git mutation**

```powershell
Set-Location ..
git diff --check
git status --short
Set-Location backend
```

Expected: only Task 1 plus the approved spec/plan files are changed; staged paths remain zero.

---

### Task 2: Enforce canonical stored paths and visible root links

**Files:**

- Modify: `backend/app/core/config.py`
- Modify: `backend/app/knowledge/document_storage.py`
- Test: `backend/tests/test_config.py`
- Test: `backend/tests/test_document_storage.py`

**Interfaces:**

- Consumes: Settings now returns an absolute lexical root without resolving symlinks.
- Preserves: `DocumentStorage.resolve_stored(relative_path, *, knowledge_base_id, document_id, file_type) -> Path` and fixed `DocumentStorageError`.
- Produces: exact canonical round-trip for `<kb_uuid>/<document_uuid>.<type>`.

- [x] **Step 1: Add RED tests for root symlink preservation and mixed separators**

Add to `test_config.py`:

```python
def test_settings_preserves_document_storage_root_symlink(
    tmp_path: Path,
) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    link = tmp_path / "uploads-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    settings = Settings(
        _env_file=None,
        DOCUMENT_STORAGE_ROOT=str(link),
    )

    assert settings.document_storage_root == link.absolute()
    assert settings.document_storage_root.is_symlink()
```

Extend `test_storage_rejects_invalid_stored_path` with:

```python
f"{KNOWLEDGE_BASE_ID}\\nested\\{DOCUMENT_ID}.txt",
f"{KNOWLEDGE_BASE_ID}\\{DOCUMENT_ID}.txt",
f"{str(KNOWLEDGE_BASE_ID).upper()}/{DOCUMENT_ID}.txt",
f"{KNOWLEDGE_BASE_ID}/{str(DOCUMENT_ID).upper()}.txt",
f"{KNOWLEDGE_BASE_ID}/{DOCUMENT_ID}.TXT",
f"{KNOWLEDGE_BASE_ID}/./{DOCUMENT_ID}.txt",
```

- [x] **Step 2: Run RED tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_config.py::test_settings_preserves_document_storage_root_symlink tests/test_document_storage.py::test_storage_rejects_invalid_stored_path -q
```

Expected: the symlink test and at least the Windows mixed-separator path cases fail on the old behavior.

- [x] **Step 3: Preserve the lexical root and implement strict canonical stored-path parsing**

Import `os` in `config.py` and replace `return path.resolve()` with:

```python
return Path(os.path.abspath(path))
```

This normalizes `.`/`..` without dereferencing a symlink/reparse target before `DocumentStorage` validates it.

At the start of `_stored_path()` reject backslashes and require an exact canonical reconstruction:

```python
if not isinstance(relative_path, str) or "\\" in relative_path:
    raise ValueError("invalid stored document path")
normalized = PurePosixPath(relative_path)
if normalized.is_absolute() or len(normalized.parts) != 2:
    raise ValueError("invalid stored document path")
raw_knowledge_base_id, filename = normalized.parts
knowledge_base_id = UUID(raw_knowledge_base_id)
file_path = PurePosixPath(filename)
if len(file_path.parts) != 1:
    raise ValueError("invalid stored document path")
document_id = UUID(file_path.stem)
file_type = _SUPPORTED_SUFFIXES.get(file_path.suffix)
if file_type is None:
    raise ValueError("invalid stored document suffix")
canonical = f"{knowledge_base_id}/{document_id}.{file_type}"
if relative_path != canonical:
    raise ValueError("non-canonical stored document path")
path = self._contained_path(self._root / raw_knowledge_base_id / filename)
return path, knowledge_base_id, document_id, file_type
```

Do not lowercase the suffix before the canonical comparison. Keep existing root/parent/file symlink and reparse checks.

- [x] **Step 4: Run GREEN storage regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_document_storage.py -q
```

Expected: all Settings/storage tests pass; platform-unavailable symlink cases may skip with their existing explicit reason.

- [x] **Step 5: Checkpoint without Git mutation**

Run `git diff --check` and `git status --short` from the repository root. Do not stage or commit.

---

### Task 3: Bound parsers and repair Markdown structure metadata

**Files:**

- Modify: `backend/app/rag/parsers/markdown_parser.py`
- Modify: `backend/app/rag/parsers/txt_parser.py`
- Modify: `backend/app/rag/parsers/pdf_parser.py`
- Modify: `backend/app/rag/text_cleaner.py`
- Test: `backend/tests/test_markdown_parser.py`
- Test: `backend/tests/test_txt_parser.py`
- Test: `backend/tests/test_pdf_parser.py`
- Test: `backend/tests/test_text_cleaner.py`

**Interfaces:**

- Parser signatures add keyword-only `limits: DocumentProcessingLimits = DEFAULT_DOCUMENT_PROCESSING_LIMITS`.
- All parser-side limit failures raise `DocumentProcessingLimitError` unchanged.
- Markdown `code_blocks` entries contain only `language`, `start_line`, `end_line`.
- `clean_parsed_document()` returns heading and code-block line numbers relative to cleaned text.

- [x] **Step 1: Write RED parser-limit and metadata tests**

Add tests using small injected limits:

```python
LIMITS = DocumentProcessingLimits(
    max_pdf_pages=1,
    max_extracted_characters=20,
    max_markdown_structures=1,
    max_chunks=10,
)


def test_markdown_parser_omits_code_content_metadata(tmp_path: Path) -> None:
    path = tmp_path / "code.md"
    path.write_text("```py\nsecret = 1\n```", encoding="utf-8")

    parsed = parse_markdown(path, document_id=DOCUMENT_ID)

    assert parsed.metadata["code_blocks"] == [
        {"language": "py", "start_line": 1, "end_line": 3}
    ]


def test_markdown_parser_rejects_structure_limit(tmp_path: Path) -> None:
    path = tmp_path / "many.md"
    path.write_text("# One\n# Two", encoding="utf-8")

    with pytest.raises(DocumentProcessingLimitError):
        parse_markdown(path, document_id=DOCUMENT_ID, limits=LIMITS)


def test_txt_parser_rejects_extracted_character_limit(tmp_path: Path) -> None:
    path = tmp_path / "large.txt"
    path.write_text("x" * 21, encoding="utf-8")

    with pytest.raises(DocumentProcessingLimitError):
        parse_txt(path, document_id=DOCUMENT_ID, limits=LIMITS)


def test_pdf_parser_rejects_page_limit(tmp_path: Path) -> None:
    path = tmp_path / "many.pdf"
    path.write_bytes(build_pdf(["one", "two"]))

    with pytest.raises(DocumentProcessingLimitError):
        parse_pdf(path, document_id=DOCUMENT_ID, limits=LIMITS)
```

Also add a one-page PDF whose extracted text exceeds 20 characters, proving the incremental character limit.

- [x] **Step 2: Write the RED cleaner test for fenced blank lines**

Replace the stale `code_blocks == original` assertion with:

```python
def test_cleaner_preserves_fenced_blank_lines_and_remaps_structure() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="Intro\n\n```py\na = 1\n\n\nb = 2\n```\n\n# Next",
        metadata={
            "format": "markdown",
            "headings": [
                {"level": 1, "text": "Next", "line_number": 10}
            ],
            "code_blocks": [
                {"language": "py", "start_line": 3, "end_line": 8}
            ],
        },
    )

    cleaned = clean_parsed_document(original)

    assert "a = 1\n\n\nb = 2" in cleaned.text
    assert cleaned.metadata["code_blocks"] == [
        {"language": "py", "start_line": 3, "end_line": 8}
    ]
    assert cleaned.metadata["headings"] == [
        {"level": 1, "text": "Next", "line_number": 10}
    ]
```

Retain a second case where blank lines outside the fence collapse and move both heading and code-block lines.

- [x] **Step 3: Run RED parser/cleaner tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_markdown_parser.py tests/test_txt_parser.py tests/test_pdf_parser.py tests/test_text_cleaner.py -q
```

Expected: failures for missing `limits`, duplicated code `content`, missing bounds and stale code-block line mapping.

- [x] **Step 4: Implement incremental parser limits**

Each parser imports the shared limits. TXT and Markdown check decoded `len(text)` before returning or extracting structure:

```python
if len(text) > limits.max_extracted_characters:
    raise DocumentProcessingLimitError()
```

Markdown `_extract_structure()` accepts `max_structures: int`; after every heading or code block append it checks:

```python
if len(headings) + len(code_blocks) > max_structures:
    raise DocumentProcessingLimitError()
```

Remove `content_lines` and the `content` metadata key; scanning still advances to the matching closing fence.

PDF replaces the tuple comprehension with an explicit loop:

```python
if len(reader.pages) > limits.max_pdf_pages:
    raise DocumentProcessingLimitError()
pages_list: list[ParsedPage] = []
extracted_characters = 0
for page_number, page in enumerate(reader.pages, start=1):
    page_text = page.extract_text() or ""
    extracted_characters += len(page_text)
    if extracted_characters > limits.max_extracted_characters:
        raise DocumentProcessingLimitError()
    pages_list.append(ParsedPage(page_number=page_number, text=page_text))
pages = tuple(pages_list)
```

Add `except DocumentProcessingLimitError: raise` before PDF's generic exception wrapper.

- [x] **Step 5: Make Markdown cleaning fence-aware**

Split the cleaner into ordinary/PDF `_clean_text()` and Markdown `_clean_markdown_text()` paths. The Markdown helper must:

1. normalize CRLF/CR before line enumeration;
2. derive protected inclusive source ranges from validated integer `start_line`/`end_line` values;
3. preserve every blank line inside protected ranges;
4. collapse only unprotected blank-line runs;
5. record the cleaned line number for every retained source line;
6. trim only unprotected leading/trailing blank lines;
7. remap `headings[].line_number`, `code_blocks[].start_line`, and `code_blocks[].end_line` through the resulting mapping.

Use a small retained-line record so trimming cannot invalidate mappings:

```python
@dataclass(frozen=True)
class _CleanedLine:
    source_line: int
    text: str
    protected: bool
```

After trimming, construct both outputs in one pass:

```python
line_mapping = {
    item.source_line: cleaned_line
    for cleaned_line, item in enumerate(output, start=1)
}
return "\n".join(item.text for item in output), line_mapping
```

Malformed metadata is copied but ignored for range protection/remapping; parser-generated valid metadata remains authoritative.

- [x] **Step 6: Run GREEN parser/cleaner regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_markdown_parser.py tests/test_txt_parser.py tests/test_pdf_parser.py tests/test_text_cleaner.py -q
```

Expected: all tests pass with no content/path leakage in exception strings.

- [x] **Step 7: Checkpoint without Git mutation**

Run `git diff --check` and `git status --short`. Do not stage or commit.

---

### Task 4: Bound Chunking and persist safe processing failures

**Files:**

- Modify: `backend/app/rag/chunker.py`
- Modify: `backend/app/services/document_ingestion_service.py`
- Modify: `backend/app/services/document_service.py`
- Modify: `backend/app/api/dependencies.py`
- Test: `backend/tests/test_chunker.py`
- Test: `backend/tests/test_document_ingestion_service.py`
- Test: `backend/tests/test_document_service.py`

**Interfaces:**

- `chunk_document(document, *, chunk_size, chunk_overlap, limits=DEFAULT_DOCUMENT_PROCESSING_LIMITS)` rejects a document before appending chunk `max_chunks + 1`.
- `DocumentChunkDraft.heading` is `None` or at most 512 Python characters.
- `DocumentIngestionService(session, *, storage, chunk_size, chunk_overlap, processing_limits)` passes one immutable contract to parser and chunker.
- Limit failures during parse mark parse/chunk failed; limit failures during Chunking mark only chunk failed after parse succeeds.

- [x] **Step 1: Add RED Chunker tests**

```python
def test_chunker_rejects_chunk_amplification_before_returning_partial_data() -> None:
    limits = DocumentProcessingLimits(
        max_pdf_pages=500,
        max_extracted_characters=10_000,
        max_markdown_structures=100,
        max_chunks=2,
    )

    with pytest.raises(
        DocumentProcessingLimitError,
        match="Document exceeds the processing limit",
    ):
        chunk_document(
            parsed_txt("x" * 250),
            chunk_size=100,
            chunk_overlap=0,
            limits=limits,
        )


def test_chunker_bounds_persisted_heading_length() -> None:
    heading = "H" * 600
    document = ParsedDocument(
        document_id=DOCUMENT_ID,
        text=f"# {heading}\nBody",
        metadata={
            "format": "markdown",
            "headings": [
                {"level": 1, "text": heading, "line_number": 1}
            ],
        },
    )

    chunks = chunk_document(document, chunk_size=1000, chunk_overlap=0)

    assert chunks[0].heading == heading[:512]
    assert len(chunks[0].heading or "") == 512
```

- [x] **Step 2: Add RED ingestion/service tests**

Construct the following small limit contract, upload synthetic text longer than five characters, and assert:

```python
limits = DocumentProcessingLimits(
    max_pdf_pages=10,
    max_extracted_characters=5,
    max_markdown_structures=10,
    max_chunks=10,
)
```

```python
assert processed.parse_status == "failed"
assert processed.chunk_status == "failed"
assert processed.error_message == "Document exceeds the processing limit."
assert stored_chunks(session, document) == []
assert str(storage.root) not in processed.error_message
assert "private" not in processed.error_message
```

Add a separate ingestion test with `max_chunks=1`, small `chunk_size`, and text requiring two chunks; assert parse is `parsed`, chunk is `failed`, and no partial rows exist.

- [x] **Step 3: Run RED processing tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chunker.py tests/test_document_ingestion_service.py tests/test_document_service.py -q
```

Expected: missing `limits` parameters, unlimited chunks and unbounded heading cause failures.

- [x] **Step 4: Convert `_chunk_ranges` to a generator and enforce the cap**

Change `_chunk_ranges` to `Iterator[tuple[int, int]]`, remove the `ranges` list, replace `ranges.append((start, end))` with `yield start, end`, and remove `return tuple(ranges)`. Before each draft append in both PDF and non-PDF branches:

```python
if len(drafts) >= limits.max_chunks:
    raise DocumentProcessingLimitError()
```

Pass `limits` as a keyword-only argument with the immutable default, and bound heading in `_build_draft()`:

```python
heading=None if heading is None else heading.text[:512]
```

- [x] **Step 5: Inject limits through services**

Extend constructors exactly as follows:

```python
class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        *,
        storage: DocumentStorage,
        chunk_size: int,
        chunk_overlap: int,
        processing_limits: DocumentProcessingLimits = (
            DEFAULT_DOCUMENT_PROCESSING_LIMITS
        ),
    ) -> None:
        self._session = session
        self._storage = storage
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._processing_limits = processing_limits
```

`DocumentService` receives the same optional immutable contract and passes it to ingestion. `get_document_service()` passes `settings.document_processing_limits`.

Parser dispatch becomes:

```python
parsed = _PARSERS[document.file_type](
    path,
    document_id=document.id,
    limits=self._processing_limits,
)
```

Chunking becomes:

```python
drafts = chunk_document(
    cleaned,
    chunk_size=self._chunk_size,
    chunk_overlap=self._chunk_overlap,
    limits=self._processing_limits,
)
```

Catch `DocumentProcessingLimitError` in both processing phases. Parser-side failures call `_mark_parse_failed`; chunk-side failures call `_mark_chunk_failed`. Do not catch storage, SQLAlchemy or unexpected exceptions.

Update the helpers to accept the exact safe unions:

```python
def _mark_parse_failed(
    self,
    document: Document,
    error: DocumentParseError | DocumentProcessingLimitError,
) -> Document:
    document.parse_status = "failed"
    document.chunk_status = "failed"
    document.error_message = str(error)
    self._session.flush()
    return document

def _mark_chunk_failed(
    self,
    document: Document,
    error: DocumentContentEmptyError | DocumentProcessingLimitError,
) -> Document:
    document.parse_status = "parsed"
    document.chunk_status = "failed"
    document.error_message = str(error)
    self._session.flush()
    return document
```

- [x] **Step 6: Run GREEN processing regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chunker.py tests/test_document_ingestion_service.py tests/test_document_service.py tests/test_document_api.py -q
```

Expected: successful uploads remain HTTP 201 parsed/chunked; content/limit failures remain safe HTTP 201 failed Documents; no partial chunks.

- [x] **Step 7: Checkpoint without Git mutation**

Run `git diff --check` and `git status --short`. Do not stage or commit.

---

### Task 5: Add database final constraints and migration

**Files:**

- Create: `backend/alembic/versions/20260801_0006_plan3_m1_m2_audit_remediation.py`
- Modify: `backend/app/models/knowledge_base.py`
- Modify: `backend/app/models/document.py`
- Modify: `backend/app/models/rag_query.py`
- Modify: `backend/app/models/message.py`
- Modify: `backend/tests/test_knowledge_models.py`
- Modify: `backend/tests/test_knowledge_migration.py`

**Interfaces:**

- Produces: `uq_documents_knowledge_base_id_file_hash`.
- Changes: `fk_documents_knowledge_base_id_knowledge_bases` to `ON DELETE RESTRICT`.
- Produces: `fk_rag_queries_answer_message_id_messages` with `ON DELETE SET NULL`.
- Changes: `fk_rag_queries_answer_message_conversation_messages` to `ON DELETE NO ACTION` while retaining cross-conversation protection.
- Migration revision: `20260801_0006`, down revision `20260726_0005`.

- [x] **Step 1: Replace cascade expectations with RED database-contract tests**

Replace `test_deleting_knowledge_base_cascades_owned_rows` with a test that commits a Knowledge Base, Document and chunk, then executes raw SQL delete:

```python
with pytest.raises(IntegrityError):
    session.execute(
        delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base.id)
    )
    session.commit()
session.rollback()
assert session.get(KnowledgeBase, knowledge_base.id) is not None
assert session.get(Document, document.id) is not None
```

Add same-KB hash uniqueness and different-KB allowance tests. Replace the ORM-only answer deletion proof with an additional raw SQL test:

```python
session.execute(delete(Message).where(Message.id == answer_id))
session.commit()
session.expire_all()
preserved = session.get(RagQuery, query_id)
assert preserved is not None
assert preserved.conversation_id == conversation_id
assert preserved.answer_message_id is None
```

- [x] **Step 2: Extend migration tests before creating the revision**

Update head assertions:

```python
assert {
    constraint["name"]
    for constraint in inspector.get_unique_constraints("documents")
} == {
    "uq_documents_id_knowledge_base_id",
    "uq_documents_knowledge_base_id_file_hash",
}
assert document_foreign_key["options"]["ondelete"] == "RESTRICT"
assert rag_foreign_keys[("answer_message_id",)]["options"]["ondelete"] == (
    "SET NULL"
)
assert answer_foreign_key["options"].get("ondelete", "NO ACTION") == (
    "NO ACTION"
)
```

Add a migration behavior test that upgrades to `20260726_0005`, inserts two complete Document rows with one KB/hash combination using `sqlalchemy.text`, and asserts upgrade to `head` raises `RuntimeError` containing only the duplicate group count and remediation direction—not filenames, paths or hashes.

- [x] **Step 3: Run RED model/migration tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_knowledge_models.py tests/test_knowledge_migration.py -q
```

Expected: current CASCADE, missing hash uniqueness, raw Message RESTRICT and missing revision fail the new assertions.

- [x] **Step 4: Update ORM metadata**

In `Document.__table_args__` add:

```python
UniqueConstraint(
    "knowledge_base_id",
    "file_hash",
    name="uq_documents_knowledge_base_id_file_hash",
),
```

Change Document FK to `ondelete="RESTRICT"`. Change `KnowledgeBase.documents` to:

```python
documents: Mapped[list[Document]] = relationship(
    back_populates="knowledge_base",
    passive_deletes="all",
)
```

In RagQuery, change the composite FK to `ondelete="NO ACTION"` and add to `answer_message_id`:

```python
ForeignKey(
    "messages.id",
    name="fk_rag_queries_answer_message_id_messages",
    ondelete="SET NULL",
)
```

Set `passive_deletes=True` on `Message.answered_rag_queries` so unloaded raw/ORM deletions use the database action while existing loaded ORM behavior remains compatible.

- [x] **Step 5: Create the additive Alembic revision**

The revision must first count duplicate groups:

```python
duplicate_groups = op.get_bind().execute(
    sa.text(
        "SELECT COUNT(*) FROM ("
        "SELECT 1 FROM documents "
        "GROUP BY knowledge_base_id, file_hash HAVING COUNT(*) > 1"
        ") AS duplicate_document_groups"
    )
).scalar_one()
if duplicate_groups:
    raise RuntimeError(
        "Plan 3 document hash uniqueness migration found "
        f"{duplicate_groups} duplicate group(s); review them manually."
    )
```

Then use named `batch_alter_table()` operations to replace the Document FK, create the hash unique constraint, replace the RagQuery composite FK with `NO ACTION`, and create the single-column `SET NULL` FK. `downgrade()` performs the exact inverse and does not touch rows.

- [x] **Step 6: Run GREEN database regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_knowledge_models.py tests/test_knowledge_migration.py tests/test_migrations.py tests/test_agent_migrations.py -q
```

Expected: model and migration contracts pass on fresh temporary SQLite, including downgrade and fail-closed duplicate evidence.

- [x] **Step 7: Checkpoint without Git mutation**

Run `git diff --check`, `git status --short`, and confirm `git diff --name-only --cached` is empty.

---

### Task 6: Normalize non-empty deletion and unique-race errors

**Files:**

- Modify: `backend/app/services/errors.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/services/knowledge_base_service.py`
- Modify: `backend/app/services/document_service.py`
- Modify: `backend/app/api/errors.py`
- Modify: `backend/tests/test_knowledge_base_service.py`
- Modify: `backend/tests/test_knowledge_base_api.py`
- Modify: `backend/tests/test_document_service.py`
- Modify: `backend/tests/test_document_api.py`
- Modify: `backend/tests/test_error_handling.py`

**Interfaces:**

- Produces: `KnowledgeBaseNotEmptyError(knowledge_base_id)` mapped to `409 / knowledge_base_not_empty`.
- Preserves: `DocumentDuplicateError` mapped to `409 / document_duplicate`.
- Internal IntegrityError details never enter response, `error_message`, log extras or file paths.

- [x] **Step 1: Add RED service/API deletion tests**

Service test:

```python
with pytest.raises(KnowledgeBaseNotEmptyError):
    service.delete_knowledge_base(knowledge_base.id)
assert session.get(KnowledgeBase, knowledge_base.id) is not None
assert session.get(Document, document.id) is not None
```

API test creates a KB and a synthetic Document in the temporary database, calls DELETE, then asserts:

```python
assert response.status_code == 409
assert response.json()["error"]["code"] == "knowledge_base_not_empty"
assert response.json()["error"]["message"] == (
    "Delete documents before deleting the knowledge base"
)
```

After the response, query the temp database and verify both rows remain. Create a synthetic file in `tmp_path` and prove it remains unchanged. Retain the existing empty-KB 204 test.

- [x] **Step 2: Add RED unique-race normalization test**

Create one committed Document, then bypass only the second Document scalar lookup in the next request so the DB unique constraint acts as the final gate:

```python
def test_service_normalizes_unique_race_and_cleans_promoted_file(
    db: tuple[Session, Engine],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Race")
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )
    content = b"same race content"
    asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="first.txt",
            stream=TrackingStream(content),
        )
    )
    session.commit()
    real_scalar = session.scalar
    document_scalar_calls = 0

    def scalar_without_duplicate_precheck(statement, *args, **kwargs):
        nonlocal document_scalar_calls
        if "FROM documents" in str(statement):
            document_scalar_calls += 1
            if document_scalar_calls == 2:
                return None
        return real_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", scalar_without_duplicate_precheck)

    with pytest.raises(DocumentDuplicateError):
        asyncio.run(
            service.upload_document(
                knowledge_base_id,
                original_filename="second.txt",
                stream=TrackingStream(content),
            )
        )
    session.rollback()

    assert _document_count(session) == 1
    assert len(_stored_files(storage.root)) == 1
```

Also assert `error_spec_for_exception(DocumentDuplicateError())` remains the existing safe 409 contract.

- [x] **Step 3: Run RED service/API tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_knowledge_base_service.py tests/test_knowledge_base_api.py tests/test_document_service.py tests/test_document_api.py -q
```

Expected: non-empty deletion currently succeeds/cascades and the IntegrityError race is not normalized.

- [x] **Step 4: Add the service error and stable API mapping**

Define and export:

```python
class KnowledgeBaseNotEmptyError(ServiceError):
    def __init__(self, knowledge_base_id: UUID) -> None:
        super().__init__(
            f"Knowledge base contains documents: {knowledge_base_id}"
        )
        self.knowledge_base_id = knowledge_base_id
```

Map it before the generic service/database branches:

```python
if isinstance(exc, KnowledgeBaseNotEmptyError):
    return ErrorSpec(
        409,
        "knowledge_base_not_empty",
        "Delete documents before deleting the knowledge base",
    )
```

- [x] **Step 5: Guard Knowledge Base deletion in the service**

Before `session.delete()`:

```python
document_id = self._session.scalar(
    select(Document.id)
    .where(Document.knowledge_base_id == knowledge_base_id)
    .limit(1)
)
if document_id is not None:
    raise KnowledgeBaseNotEmptyError(knowledge_base_id)
```

Wrap the delete flush only:

```python
try:
    self._session.delete(knowledge_base)
    self._session.flush()
except IntegrityError as exc:
    raise KnowledgeBaseNotEmptyError(knowledge_base_id) from exc
```

The request dependency owns rollback. Do not delete or enumerate storage files in this service.

- [x] **Step 6: Normalize only the Document hash unique constraint**

Add a private predicate in `document_service.py`:

```python
def _is_document_hash_duplicate(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    return (
        "uq_documents_knowledge_base_id_file_hash" in message
        or (
            "unique constraint failed" in message
            and "documents.knowledge_base_id" in message
            and "documents.file_hash" in message
        )
    )
```

Wrap only the initial Document flush:

```python
try:
    self._session.flush()
except IntegrityError as exc:
    if _is_document_hash_duplicate(exc):
        raise DocumentDuplicateError() from exc
    raise
```

Do not call `rollback()` inside the service; the request/test owner performs rollback, triggering the existing promoted-file cleanup listener.

- [x] **Step 7: Run GREEN service/API regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_knowledge_base_service.py tests/test_knowledge_base_api.py tests/test_document_service.py tests/test_document_api.py tests/test_error_handling.py -q
```

Expected: non-empty deletion is stable 409, empty deletion remains 204, unique races become duplicate 409, and storage/DB failures retain their existing classifications.

- [x] **Step 8: Checkpoint without Git mutation**

Run `git diff --check`, `git status --short`, and `git diff --name-only --cached`. Staged paths must be empty.

---

### Task 7: Synchronize documentation and close the audit

**Files:**

- Create: `docs/reviews/2026-08-01-plan3-m1-m2-audit-remediation-review.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: `docs/superpowers/plans/2026-08-01-plan3-m1-m2-audit-remediation-implementation.md`

**Interfaces:**

- Documents the exact 409, canonical path, processing-limit, migration and Qdrant loopback contracts.
- Records observed verification outputs without inventing Docker/runtime evidence.
- Leaves M3 and all later-Plan abilities explicitly unimplemented.

- [x] **Step 1: Update operational and architecture documentation**

Update both READMEs and `docs/20-knowledge-base-design.md` with:

```text
Qdrant Compose binds 6333 only to 127.0.0.1.
DOCUMENT_MAX_PDF_PAGES=500
DOCUMENT_MAX_EXTRACTED_CHARACTERS=10000000
DOCUMENT_MAX_MARKDOWN_STRUCTURES=20000
DOCUMENT_MAX_CHUNKS=10000
Deleting a Knowledge Base that still owns any Document returns 409.
Markdown code-block metadata stores language/start_line/end_line, not a second content copy.
```

Remove the old statement that Knowledge Base deletion cascades Documents or that code-block metadata contains content. Keep the synchronous-processing, no-OCR, no-Document-delete, crash-orphan and no-M3-runtime limitations explicit.

- [x] **Step 2: Update Changelog and Plan status**

Add an Unreleased `Security And Reliability`/`Fixed` group covering the verified fixes. In the active Plan 3 table:

- change stale M2 batch “未完成” text to completed;
- add the M1/M2 audit-remediation evidence without marking M3 started;
- preserve the real Git baseline and existing tags;
- record the new migration head only after migration tests pass.

- [x] **Step 3: Write the formal review record**

Create `docs/reviews/2026-08-01-plan3-m1-m2-audit-remediation-review.md` with these sections and actual observed values:

```markdown
# Plan 3 M1/M2 Audit Remediation Review

## Scope And Baseline
## Acceptance Matrix
## Confirmed Findings And Fixes
## TDD Evidence
## Full Verification Evidence
## Security And Plan-Boundary Checks
## Codex Self-Review
### Must fix
### Later Step
### Accepted limitation
### Not applicable
## Readiness Conclusion
```

Do not enter pass counts until commands have been run. Use “not run” rather than estimates while execution is incomplete.

- [x] **Step 4: Run focused backend verification**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_plan3_foundation.py tests/test_config.py tests/test_document_storage.py tests/test_markdown_parser.py tests/test_txt_parser.py tests/test_pdf_parser.py tests/test_text_cleaner.py tests/test_chunker.py tests/test_document_ingestion_service.py tests/test_document_service.py tests/test_document_api.py tests/test_knowledge_models.py tests/test_knowledge_migration.py tests/test_knowledge_base_service.py tests/test_knowledge_base_api.py tests/test_error_handling.py -q
```

Expected: all selected tests pass; only the already-known Starlette TestClient/httpx deprecation warning may remain.

- [x] **Step 5: Run full backend and dependency verification**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: full pytest passes and `pip check` prints `No broken requirements found.`.

- [x] **Step 6: Verify Alembic only against a fresh temporary SQLite**

Use a newly generated path under the OS temp directory, print and verify that it does not equal or resolve beneath `backend/ai_agent_lab.db`, then run:

```powershell
$auditTempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-agent-lab-m1-m2-audit-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $auditTempRoot | Out-Null
$auditDb = Join-Path $auditTempRoot "audit.db"
$env:DATABASE_URL = "sqlite:///" + ($auditDb -replace '\\','/')
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
..\.venv\Scripts\python.exe -m alembic downgrade 20260726_0005
..\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:DATABASE_URL
```

Before cleanup, resolve `$auditTempRoot` and verify it starts with `[System.IO.Path]::GetTempPath()` and contains the exact `ai-agent-lab-m1-m2-audit-` prefix. Only then remove that exact temporary directory with PowerShell `Remove-Item -LiteralPath $auditTempRoot -Recurse -Force`.

- [x] **Step 7: Run frontend regression**

From `frontend/`:

```powershell
npm run typecheck
npm test
npm run build
```

Expected: typecheck, all Vitest files/tests and production build pass. No screenshot is required because this audit changes no frontend behavior.

- [x] **Step 8: Run Compose, docs, secret, artifact and Plan-boundary checks**

From repository root:

```powershell
docker compose config --quiet
$runningServices = @(docker compose ps --status running --services)
if ($LASTEXITCODE -eq 0 -and $runningServices -contains "qdrant") {
    Invoke-RestMethod http://localhost:6333/healthz
}
```

Only call `http://localhost:6333/healthz` if `docker compose ps` proves the local container is running. Do not pull an image or claim runtime health when the daemon is inaccessible.

Run this local Markdown-link checker over project Markdown files:

```powershell
$markdownFiles = Get-ChildItem -File -Recurse -Filter *.md | Where-Object {
    $_.FullName -notmatch '\\(\.git|\.venv|node_modules|dist|docs-local|__pycache__|\.pytest_cache|uploads)\\'
}
$missingLinks = [System.Collections.Generic.List[string]]::new()
foreach ($markdownFile in $markdownFiles) {
    $content = Get-Content -LiteralPath $markdownFile.FullName -Raw -Encoding UTF8
    $matches = [regex]::Matches(
        $content,
        '!?' + '\[[^\]]*\]' + '\((?<target><[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)'
    )
    foreach ($match in $matches) {
        $target = $match.Groups['target'].Value.Trim('<', '>')
        if ($target -match '^(#|https?://|mailto:|data:)') { continue }
        $pathPart = ($target -split '[?#]', 2)[0]
        if (-not $pathPart) { continue }
        $decoded = [uri]::UnescapeDataString($pathPart)
        $resolved = [IO.Path]::GetFullPath(
            (Join-Path $markdownFile.DirectoryName $decoded)
        )
        if (-not (Test-Path -LiteralPath $resolved)) {
            $missingLinks.Add("$($markdownFile.FullName) -> $target")
        }
    }
}
if ($missingLinks.Count -ne 0) {
    $missingLinks
    throw "Missing local Markdown links: $($missingLinks.Count)"
}
"Markdown files: $($markdownFiles.Count); missing links: 0"
```

Run exact secret and forbidden-runtime scans:

```powershell
$trackedFiles = @(git ls-files | Where-Object { Test-Path -LiteralPath $_ })
$secretPattern = '(?i)(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,})'
$secretMatches = @(Select-String -LiteralPath $trackedFiles -Pattern $secretPattern)
if ($secretMatches.Count -ne 0) {
    $secretMatches
    throw "Potential tracked secrets found"
}

$runtimeFiles = @(
    Get-ChildItem -LiteralPath backend/app,frontend/src -File -Recurse
    Get-Item -LiteralPath backend/pyproject.toml,frontend/package.json
)
$webFetchMatches = @(
    Select-String -LiteralPath $runtimeFiles.FullName -Pattern '(?i)web_fetch'
)
if ($webFetchMatches.Count -ne 0) {
    $webFetchMatches
    throw "Deferred web_fetch runtime surface found"
}

$laterPlanMatches = @(
    Select-String -LiteralPath $runtimeFiles.FullName -Pattern '(?i)(advanced rag|rerank|evaluation|memory|ocr|multimodal|mcp|human approval)'
)
$laterPlanMatches
```

Every later-Plan match must be inspected. Existing negative limitation text such as the scanned-PDF OCR error is allowed; imports, executable adapters, routes, dependencies or feature registrations are blockers.

Check tracked artifacts:

```powershell
$trackedArtifacts = @(git ls-files | Where-Object {
    $_ -match '(^|/)(__pycache__|\.pytest_cache|dist|uploads)(/|$)|\.pyc$|\.db$'
})
if ($trackedArtifacts.Count -ne 0) {
    $trackedArtifacts
    throw "Tracked runtime artifacts found"
}
```

These scans exclude runtime directories through Git tracking state and never open `backend/ai_agent_lab.db`. They cover:

- secret/token/private-key patterns and realistic credential assignments;
- forbidden `web_fetch` runtime/schema/Registry/dependency surfaces;
- later-Plan runtime names: Advanced RAG, Rerank, Evaluation, Memory, OCR, multimodal, MCP, Human Approval;
- generated artifacts: `__pycache__`, `.pyc`, `.pytest_cache`, frontend `dist`, runtime uploads and SQLite files.

Classify documentation-only mentions separately from runtime implementation. Expected: zero secret findings, zero forbidden runtime, zero newly tracked artifacts and zero missing local links.

- [x] **Step 9: Run final Git and Codex review gates**

```powershell
git diff --check
git diff --name-only --cached
git status --short
git diff --stat
git diff -- docker-compose.yml backend frontend docs docs-plan README.md README_CN.md CHANGELOG.md
$newTextFiles = @(git ls-files --others --exclude-standard | Where-Object {
    $_ -match '\.(py|md|toml|ya?ml|json|tsx?|css)$'
})
if ($newTextFiles.Count -gt 0) {
    $trailingWhitespace = @(
        Select-String -LiteralPath $newTextFiles -Pattern '[ \t]+$'
    )
    if ($trailingWhitespace.Count -ne 0) {
        $trailingWhitespace
        throw "Trailing whitespace found in untracked files"
    }
}
```

Review every changed/untracked path and classify findings:

- `must fix`: correctness, security, migration, secret, test or Plan-boundary blocker—fix now and rerun affected gates;
- `later Step`: valid M3+ work explicitly deferred;
- `accepted limitation`: synchronous processing, privileged TOCTOU, historical orphan cleanup, Docker runtime availability;
- `not applicable`: PostgreSQL migration, frontend screenshots, live Provider/network verification.

Update the review record and this plan with exact final evidence. Staged paths must remain zero; do not commit.

---

## Execution Evidence

- Implementation mode: inline `executing-plans`; repository policy prohibited
  subagents, branches/worktrees, staging, commits, pushes, and tags.
- TDD GREEN checkpoints: Task 1 `34 passed`; Task 2 `68 passed`; Task 3
  `27 passed`; Task 4 `91 passed, 1 warning`; Task 5 `33 passed`; Task 6
  `58 passed, 1 warning`.
- Focused backend: `208 passed, 1 warning`.
- Full backend: `735 passed, 1 warning`; `pip check` reported
  `No broken requirements found.`.
- Fresh temporary SQLite: head `20260801_0006`; upgrade, check-heads,
  autogenerate check, downgrade to `20260726_0005`, and re-upgrade passed; the
  verified temporary directory was removed without touching the protected user
  database.
- Frontend: typecheck passed; `18 files / 90 tests`; production build
  transformed `1813 modules`.
- Compose config passed. Current runtime health was not checked because
  `docker compose ps` could not connect to the local daemon; no image pull or
  fabricated health claim was made.
- Documentation: `95` Markdown files, `69` local links/images, zero missing.
- Security/boundary: high-confidence token 0, unexpected private-key marker 0,
  `web_fetch` runtime 0, later-Plan runtime 0, tracked artifacts 0.
- Git: `git diff --check` passed, staged paths remained zero, and untracked
  text files had zero trailing-whitespace findings.
- Codex self-review: no remaining must-fix. Later Step, accepted limitation,
  and not-applicable classifications are recorded in the formal review.

---

## Final Handoff

This repository explicitly forbids subagents and user-owned Git mutations for this batch, so the only permitted execution mode is inline execution with `superpowers:executing-plans`. Execute Tasks 1–7 in order, preserve RED evidence before implementation, pause at material scope changes, and finish with the full verification and Codex self-review gates above.

Suggested commit message after all gates pass:

```text
fix(rag): harden plan 3 m1 m2 boundaries
```
