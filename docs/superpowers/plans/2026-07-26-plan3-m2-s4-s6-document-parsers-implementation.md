# Plan 3 M2 S4～S6 Document Parsers Implementation Plan

> **For Codex:** Execute this plan in the current task with
> `test-driven-development`. Do not use subagents, create a branch, stage,
> commit, push, tag, or read `backend/ai_agent_lab.db`.

**Goal:** Add independently testable Markdown, TXT, and text-layer PDF parsers
that return one safe shared result contract without starting cleaning,
Chunking, or ingestion orchestration.

**Architecture:** `app.rag.parsers` owns immutable parse results, safe parser
errors, and three format-specific pure parsers. Parsers accept an authorized
path plus Document UUID and return extracted text and source metadata. They do
not import database, service, API, Provider, or Qdrant modules.

**Tech Stack:** Python 3.11, dataclasses, pathlib, pytest, pypdf.

**Design:** See
`docs/superpowers/specs/2026-07-26-plan3-m2-s4-s6-document-parsers-design.md`.

---

## Guardrails

- Work only on `P3-M2-S4～S6`.
- Do not add parser dispatch, lifecycle transitions, `error_message`
  persistence, cleaner, Chunker, pipeline, API, ORM, migration, frontend, OCR,
  Embedding, Qdrant client, Retriever, or Plan 4+ runtime.
- Use only temporary files and synthetic content in tests.
- Never read, migrate, delete, or rebuild `backend/ai_agent_lab.db`.
- Add production code only after the matching test has been watched failing.
- Use `apply_patch` for edits.
- Do not stage or commit.

## Task 1: Shared Contract and Markdown Parser

**Files:**

- Create: `backend/tests/test_markdown_parser.py`
- Create: `backend/app/rag/parsers/__init__.py`
- Create: `backend/app/rag/parsers/base.py`
- Create: `backend/app/rag/parsers/markdown_parser.py`

### Step 1: Write the failing Markdown tests

Add focused tests that:

- import `DocumentParseError`, `ParsedDocument`, and `parse_markdown`;
- verify strict UTF-8 and UTF-8 BOM decoding;
- verify the original Markdown text remains intact;
- verify ATX and Setext heading metadata;
- verify backtick and tilde fenced blocks, language, content, and line numbers;
- verify heading-like code content is not a heading;
- verify invalid UTF-8 raises a safe error without exposing the temporary path.

### Step 2: Run RED

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_markdown_parser.py -q
```

Expected: collection fails because `app.rag.parsers` does not exist.

### Step 3: Implement the minimum shared contract

In `base.py`:

- define immutable `ParsedPage`;
- define immutable `ParsedDocument`;
- define `DocumentParseError`;
- define `DocumentParseLimitationError`;
- keep public messages stable and safe.

In `parsers/__init__.py`, expose only the public contract and parser entry
points that exist at this checkpoint.

### Step 4: Implement Markdown parsing

In `markdown_parser.py`:

- read bytes from the supplied `Path`;
- decode `utf-8-sig` strictly;
- wrap I/O and decode failures in `DocumentParseError`;
- scan lines with a fence-aware state machine;
- extract ATX/Setext headings and fenced blocks;
- return JSON-compatible metadata and `pages=None`;
- preserve original decoded text.

### Step 5: Run GREEN

Run the same focused command.

Expected: all Markdown tests pass.

### Step 6: Refactor without behavior changes

Keep parsing helpers private, remove duplication, and rerun the same tests.

## Task 2: TXT Parser

**Files:**

- Create: `backend/tests/test_txt_parser.py`
- Create: `backend/app/rag/parsers/txt_parser.py`
- Modify: `backend/app/rag/parsers/__init__.py`

### Step 1: Write failing TXT tests

Cover:

- strict UTF-8;
- UTF-8 BOM;
- BOM-marked UTF-16 little endian;
- BOM-marked UTF-16 big endian;
- whitespace-only content preservation;
- invalid undecodable bytes;
- safe errors that omit paths and decoder diagnostics.

### Step 2: Run RED

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_txt_parser.py -q
```

Expected: import fails because `txt_parser` is absent.

### Step 3: Implement deterministic decoding

- detect UTF-8 and UTF-16 BOMs;
- otherwise decode strict UTF-8;
- return unchanged text and the selected encoding metadata;
- wrap I/O/decode failures in the safe shared error;
- export `parse_txt`.

Do not add probabilistic encoding detection or legacy-codepage fallbacks.

### Step 4: Run GREEN and adjacent regression

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_txt_parser.py tests/test_markdown_parser.py -q
```

Expected: all parser tests so far pass.

## Task 3: PDF Dependency and Parser

**Files:**

- Create: `backend/tests/test_pdf_parser.py`
- Create: `backend/app/rag/parsers/pdf_parser.py`
- Modify: `backend/app/rag/parsers/__init__.py`
- Modify: `backend/pyproject.toml`

### Step 1: Write failing PDF tests

Create valid PDFs locally in the test module using a small deterministic
synthetic PDF builder. Do not add binary fixtures or a PDF-generation runtime
dependency.

Cover:

- one-page text extraction;
- multiple pages with order and one-based page numbers;
- a mixed text/blank document;
- a valid text-empty PDF returning `DocumentParseLimitationError`;
- malformed PDF bytes returning `DocumentParseError`;
- safe messages that omit temporary paths and low-level diagnostics.

### Step 2: Run RED before adding the dependency

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_pdf_parser.py -q
```

Expected: collection fails because the PDF parser is absent.

### Step 3: Add the bounded dependency

Add one bounded `pypdf` dependency to `backend/pyproject.toml` in the existing
sorted style.

Install the editable backend with the approved project command if the local
environment does not yet provide the package:

```powershell
..\.venv\Scripts\python.exe -m pip install -e ".[dev]" --no-build-isolation
```

If dependency installation requires network or elevated access, request the
required approval and do not fabricate successful installation evidence.

### Step 4: Implement PDF extraction

- open the path in binary mode;
- construct `PdfReader`;
- reject encrypted PDFs that cannot be read without a password;
- call `extract_text()` for every page;
- preserve ordered `ParsedPage` results;
- join document text with a double newline;
- return `page_count` metadata;
- raise the readable OCR limitation when every page is text-empty;
- wrap malformed/unreadable PDF failures in `DocumentParseError`;
- do not expose paths or third-party exception text;
- export `parse_pdf`.

### Step 5: Run GREEN and complete focused parser tests

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_pdf_parser.py tests/test_txt_parser.py tests/test_markdown_parser.py -q
```

Expected: all focused parser tests pass.

### Step 6: Verify dependency integrity

```powershell
..\.venv\Scripts\python.exe -m pip check
```

Expected: `No broken requirements found.`

## Task 4: Adjacent Regression and Documentation

**Files:**

- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify if required by current behavior: `README.md`
- Modify if required by current behavior: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: this implementation plan with observed evidence

### Step 1: Run parser plus upload/model/schema regression

```powershell
..\.venv\Scripts\python.exe -m pytest `
  tests/test_markdown_parser.py `
  tests/test_txt_parser.py `
  tests/test_pdf_parser.py `
  tests/test_document_storage.py `
  tests/test_document_service.py `
  tests/test_document_api.py `
  tests/test_knowledge_models.py `
  tests/test_knowledge_schemas.py -q
```

Expected: all pass apart from the known TestClient warning.

### Step 2: Update formal documentation

Document:

- the shared parser contract;
- exact Markdown and TXT rules;
- PDF page provenance and OCR limitation;
- the new dependency;
- that upload does not invoke parsing through S6;
- that S7～S9 still own cleaning, Chunking, pipeline, statuses, and stored
  errors.

Mark only S4～S6 and Batch 5 complete in the active Plan table after fresh
verification exists.

### Step 3: Run documentation checks

Use the repository's existing documentation/link verification method. Confirm
all tracked Markdown and local links/images are readable and no new claim
crosses the active Step boundary.

## Task 5: Full Verification and Codex Self-Review

### Step 1: Full backend regression

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

Record exact passed/warning totals.

### Step 2: Frontend regression

From `frontend/`:

```powershell
npm test -- --run
npm run typecheck
npm run build
```

Record exact file/test/module totals.

### Step 3: Temporary SQLite migration checks

Create a new system-temporary SQLite URL and run:

```powershell
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic upgrade head
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic current --check-heads
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic check
```

Delete only the verified temporary directory afterward. Never point Alembic at
`backend/ai_agent_lab.db`.

### Step 4: Repository gates

Verify:

- `git diff --check`;
- staged paths remain zero;
- changed paths belong to the S4～S6 allowlist;
- no high-confidence secrets or real Provider hosts were added;
- no generated PDF/database/upload/cache artifact was added;
- no `web_fetch`, OCR, cleaner, Chunker, ingestion, Embedding, Qdrant client,
  Retriever, frontend RAG, or Plan 4+ runtime was added;
- HEAD, `origin/main`, and peeled `v0.2.0`/`v0.2.1` targets remain unchanged
  from the batch baseline;
- the working tree contains only intentional unstaged changes.

### Step 5: Codex self-review

Review architecture, correctness, error safety, dependency scope, test value,
documentation truthfulness, and Plan boundaries. Classify every finding:

- must fix;
- later Step;
- accepted limitation;
- not applicable.

Fix all must-fix findings and rerun affected focused plus full gates.

### Step 6: Prepare manual handoff

State:

- whether S4～S6 are complete;
- exact verification evidence;
- remaining limitations;
- whether the repository may enter `P3-M2-S7～S9`;
- a suggested commit message.

Do not stage or commit.

Suggested commit message:

```text
feat(rag): add markdown txt and pdf parsers
```

## Observed Execution Evidence

- Baseline remained clean on `main` with
  `HEAD == origin/main == 66955fc9607fd4757e279eab01fae8fdea87b00d`;
  the peeled `v0.2.0` and `v0.2.1` tag targets remained unchanged.
- Markdown RED was the missing parser package; GREEN reached `4 passed`.
- TXT RED was the missing `parse_txt` export; Markdown/TXT GREEN reached
  `10 passed`.
- PDF RED was the missing `parse_pdf` export. The bounded dependency installed
  as `pypdf 6.14.2`, and the initial three-parser GREEN reached `14 passed`.
- Codex self-review identified that the UTF-32 LE BOM begins with the UTF-16 LE
  BOM. The focused regression reproduced `1 failed, 1 passed`; checking UTF-32
  BOMs first and rejecting them brought the final parser collection to
  `16 passed`.
- Parser plus upload/model/schema adjacent regression reached
  `117 passed, 1 warning`.
- Full backend regression reached `651 passed, 1 warning`; dependency integrity
  reported `No broken requirements found`.
- Frontend regression reached `18` files and `90` tests, typecheck passed, and
  the production build transformed `1813` modules.
- A new system-temporary SQLite database reached Alembic
  `20260726_0005 (head)`; `current --check-heads` and `alembic check` passed,
  and the verified temporary directory was removed.
- Documentation verification found `90` Markdown files and `69` local
  links/images with no read error or missing target.
- Parser invocation, cleaning, Chunking, lifecycle transitions, and persisted
  errors remain assigned to `P3-M2-S7～S9`.
