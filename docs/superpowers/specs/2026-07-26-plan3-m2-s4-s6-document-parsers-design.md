# Plan 3 M2 S4～S6 Document Parsers Design

## Status

- Scope: `P3-M2-S4～S6`
- Date: 2026-07-26
- Design approval: confirmed by the user
- Implementation status: not started

## Goal

Add independently testable parsers for Markdown, TXT, and text-layer PDF
documents. Each parser returns the same `ParsedDocument` contract so the later
`P3-M2-S9` ingestion pipeline can compose parsing, cleaning, Chunking, and
Document lifecycle updates without format-specific branching outside the
parser boundary.

This batch proves extraction only. It does not connect parsing to upload,
change database state, write `DocumentChunk` rows, or start later pipeline
stages.

## Acceptance Matrix

| Step | Acceptance requirement | Current evidence | Gap | Minimum new evidence |
|---|---|---|---|---|
| S4 | Markdown headings, body, and fenced code blocks are extracted | Upload accepts and stores `.md`; no parser exists | No shared result contract or Markdown parser | Parser tests for preserved source text, ATX/Setext headings, fenced code blocks, and headings inside fences |
| S5 | TXT text and supported encodings are handled deterministically | Upload accepts and stores `.txt`; no parser exists | No decoding policy or readable parse error | Parser tests for UTF-8, UTF-8 BOM, BOM-marked UTF-16, and invalid bytes |
| S6 | Text-layer PDF content and page metadata are extracted; scanned PDF returns a readable limitation | Upload accepts and stores `.pdf`; `pypdf` is not installed | No PDF reader, page result, corrupt-file handling, or scanned-PDF boundary | Real synthetic PDF extraction tests, multi-page metadata test, scanned/image-only limitation test, and corrupt-file test |

## Scope

### Included

- a shared immutable `ParsedDocument` result contract;
- shared safe parser errors;
- Markdown parsing with original markup preserved;
- Markdown heading and fenced-code-block metadata;
- deterministic TXT decoding;
- text-layer PDF extraction with page-number metadata;
- explicit scanned/image-only PDF limitation behavior;
- focused unit and integration-level parser tests using temporary or synthetic
  files;
- the minimum runtime dependency needed for PDF extraction;
- documentation and current Plan 3 acceptance evidence.

### Excluded

- file upload changes or content/MIME sniffing at upload time;
- automatic parser dispatch from `Document.file_type`;
- Document `parse_status` transitions or `error_message` persistence;
- text cleaning, whitespace normalization, or invisible-character removal;
- Chunking, token estimation, or `DocumentChunk` writes;
- Embedding Providers, Qdrant clients, retrieval, prompts, or RAG APIs;
- OCR, layout analysis, table reconstruction, image extraction, or
  multimodal parsing;
- Word, spreadsheet, presentation, HTML, CSV, or repository ingestion;
- frontend changes;
- Plan 4+ capabilities.

## Considered Approaches

### 1. Independent parsers with a shared result contract

Each format owns one small parser module and all return `ParsedDocument`.
Format-specific metadata remains local while later orchestration can consume a
stable result.

This is the selected approach because it keeps the three Steps independently
testable and avoids coupling extraction to the later ingestion state machine.

### 2. One suffix-dispatching parser service

A single service could accept a path and file type, then dispatch internally.
This gives callers one entry point but introduces the S9 orchestration boundary
before S9 begins. It is deferred until the ingestion pipeline needs it.

### 3. A general document framework

Libraries such as full ingestion frameworks could cover more formats and
layout features, but they add a large dependency and behavior surface. They
also encourage OCR, complex layout recovery, and other capabilities explicitly
outside Plan 3. This approach is rejected.

## Module Boundary

The implementation will add:

```text
backend/app/rag/parsers/
├── __init__.py
├── base.py
├── markdown_parser.py
├── txt_parser.py
└── pdf_parser.py
```

`base.py` owns the shared result and safe error vocabulary. The three parser
modules own only their respective extraction rules. `parsers/__init__.py`
exposes the intended public API.

No parser imports SQLAlchemy models, services, FastAPI, Qdrant, or Provider
code. Callers supply a `document_id` and a path to a file they have already
authorized. Controlled-storage path resolution remains the responsibility of
the later ingestion service rather than being duplicated inside pure parsers.

## Shared Contract

`ParsedDocument` is an immutable dataclass with:

```python
document_id: UUID
text: str
metadata: dict[str, object]
pages: tuple[ParsedPage, ...] | None
```

`ParsedPage` is an immutable page result with:

```python
page_number: int
text: str
```

The contract keeps complete extracted text convenient for cleaning and
Chunking while preserving page-level PDF provenance. Markdown and TXT return
`pages=None`.

Metadata is intentionally small and JSON-compatible:

- every parser records `format`;
- Markdown records `encoding`, `headings`, and `code_blocks`;
- TXT records `encoding`;
- PDF records `page_count`.

Metadata does not contain absolute paths, file contents duplicated from
`text`, credentials, internal exception messages, or future retrieval fields.

## Markdown Parser

The Markdown parser reads bytes and decodes strict UTF-8, accepting an optional
UTF-8 BOM. `ParsedDocument.text` preserves the decoded source exactly except
that the BOM is removed by decoding. Cleaning and newline normalization remain
S7 responsibilities.

A line-oriented state machine extracts:

- ATX headings (`#` through `######`);
- Setext headings using `=` or `-` underline syntax;
- fenced code blocks opened by at least three backticks or tildes;
- an optional fence info string as the code-block language;
- one-based source line positions.

Headings inside an open code fence are not treated as headings. A closing fence
must use the same marker character and at least the opening length. Unclosed
fences remain represented as code blocks through end-of-file rather than
causing text loss.

Heading metadata contains `level`, `text`, and `line_number`. Code-block
metadata contains `language`, `content`, `start_line`, and `end_line`.
Markdown-to-HTML rendering, inline syntax interpretation, and AST construction
are unnecessary for this batch.

## TXT Parser

TXT decoding is deterministic:

1. UTF-8 BOM uses `utf-8-sig`;
2. UTF-16 little- or big-endian BOM uses Python's BOM-aware `utf-16`;
3. all other input uses strict UTF-8.

Invalid byte sequences raise a readable parser error. The parser does not use
replacement characters, locale-dependent defaults, probabilistic encoding
detection, or a broad legacy-codepage fallback. This prevents silent content
corruption and keeps behavior reproducible across machines.

The decoded text is returned unchanged. A non-empty uploaded file containing
only whitespace is still parser-valid; content suitability belongs to cleaning
and Chunking.

## PDF Parser

The backend adds a bounded `pypdf` runtime dependency and uses `PdfReader` to
extract the PDF text layer page by page.

For each page:

- `extract_text()` output is retained, with `None` represented as an empty
  string;
- page numbers are one-based;
- page order is preserved.

The document-level text joins page texts with a stable double-newline
separator. This separator is an extraction boundary, not final cleaning.

If every page is blank after a whitespace check, parsing raises a dedicated
readable limitation error explaining that scanned or image-only PDFs require
OCR and are unsupported in Plan 3. A PDF with at least one text-bearing page
is valid even when other pages are blank.

Malformed, encrypted-without-password, or otherwise unreadable PDFs raise a
generic safe parse error. The public error does not include the absolute path,
document content, PDF metadata, or the third-party exception text.

PDF metadata does not attempt table reconstruction, image interpretation,
layout analysis, reading-order correction, or OCR.

## Error Model

The shared parser boundary defines:

- `DocumentParseError`: safe general parse or decoding failure;
- `DocumentParseLimitationError`: a readable, intentional unsupported-content
  limitation, currently used for scanned/image-only PDF.

The exception messages are stable and suitable for later mapping to
`Document.error_message`. Low-level exceptions remain chained for local
debugging but are not copied into the public message.

This batch does not persist either error. `P3-M2-S9` will own lifecycle
transitions and safe error persistence.

## Dependency Policy

Only `pypdf` is added because Python's standard library is sufficient for
Markdown structure extraction and deterministic TXT decoding. No Markdown
renderer, encoding detector, OCR library, PDF rendering engine, or general
ingestion framework is introduced.

The dependency must be version-bounded consistently with the existing
`pyproject.toml` style. Installation integrity is verified with `pip check`.

## Test Strategy

Tests use newly created temporary files and synthetic contents only.

### Shared contract

- immutable result/page values;
- page numbers remain positive and ordered by the PDF parser.

### Markdown

- original source text remains intact;
- ATX and Setext headings are captured with levels and line numbers;
- backtick and tilde fences capture language and content;
- heading-like text inside a fence is not reported as a heading;
- UTF-8 BOM succeeds;
- invalid UTF-8 raises a safe parse error.

### TXT

- strict UTF-8 succeeds;
- UTF-8 BOM is removed and reported correctly;
- BOM-marked UTF-16 LE/BE succeeds;
- invalid undecodable bytes raise a safe parse error;
- whitespace-only text is preserved.

### PDF

- a real synthetic text-layer PDF yields expected text;
- a multi-page PDF preserves order and page numbers;
- a mixed text/blank PDF remains valid;
- an image-only or otherwise text-empty valid PDF raises the OCR limitation;
- malformed PDF bytes raise a safe general error;
- neither error message exposes the temporary path or low-level diagnostic.

The PDF tests generate their fixtures locally and make no network or Provider
calls. No test reads `backend/ai_agent_lab.db`.

## TDD Sequence

1. Add shared-contract and Markdown tests and watch them fail because parser
   modules do not exist.
2. Implement only enough shared/Markdown code to pass.
3. Add TXT encoding tests and watch the missing parser behavior fail.
4. Implement deterministic TXT decoding.
5. Add PDF tests and watch them fail because the parser/dependency is absent.
6. Add the bounded dependency and implement text-layer extraction and errors.
7. Run the complete focused parser collection.
8. Update current documentation and acceptance evidence.
9. Run matching verification, full regression, dependency, migration,
   documentation, secret, artifact, Plan-boundary, diff, and Git-status gates.
10. Perform Codex self-review and classify findings as must fix, later Step,
    accepted limitation, or not applicable.

## Documentation Changes

Implementation completion will update:

- `docs/20-knowledge-base-design.md`;
- README/CHANGELOG only where current behavior or dependency instructions
  require it;
- the active Plan 3 execution table with fresh evidence;
- the implementation plan and observed TDD checkpoints.

Documentation will explicitly state that parser invocation, status persistence,
cleaning, Chunking, and the ingestion pipeline remain unimplemented through
S6.

## Completion Criteria

`P3-M2-S4～S6` is complete only when:

- all three parsers return the shared result contract;
- Markdown structure tests pass while original markup remains preserved;
- deterministic TXT encoding tests pass;
- text-layer PDF extraction and page provenance tests pass;
- scanned/image-only PDF produces the documented readable OCR limitation;
- malformed inputs fail safely without leaking paths or diagnostics;
- no database/API/status/pipeline behavior was added;
- focused and full regression verification passes;
- dependency, migration, docs/link, secret, artifact, Plan-boundary, diff, and
  Git-status gates pass;
- Codex self-review has no unresolved must-fix finding;
- the working tree is ready for the user's manual commit.

Completion permits consideration of `P3-M2-S7～S9`. It does not start those
steps.
