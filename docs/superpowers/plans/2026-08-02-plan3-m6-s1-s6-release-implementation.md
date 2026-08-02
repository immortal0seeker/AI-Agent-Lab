# Plan 3 M6 S1～S6 Test And Release Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. This
> repository and user require inline Codex execution only: do not dispatch
> subagents, create branches/worktrees, stage, commit, push, or tag. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Plan 3 test, Demo, documentation, and `v0.3.0` release-candidate
evidence without adding later-Plan behavior or performing the user's Git
release actions.

**Architecture:** Reuse the existing focused tests as an explicit S1～S4
acceptance matrix, adding tests only for discovered behavior gaps. Update the
single missing release-version invariant through TDD, capture sanitized
synthetic browser evidence, then synchronize formal documentation and run full
backend/frontend/Docker/migration/security/Git gates. Execute S1～S3 as the
first repository-sized checkpoint and S4～S6 as the second.

**Tech Stack:** Python 3.11, pytest, FastAPI, SQLAlchemy/Alembic, Mock
LLM/Embedding boundaries, Qdrant 1.15.x, React 19, TypeScript, Vitest/jsdom,
Vite, Playwright CLI, Docker Compose, Markdown.

## Global Constraints

- Implement only `P3-M6-S1～S6`; do not start Plan 4 runtime.
- Use Codex self-review only; do not request or run Claude Code/Fable review.
- Do not read `.env`, real secrets, paid Providers, network Tools, or
  `backend/ai_agent_lab.db`.
- Tests and Demo use synthetic credentials/data, system-temporary SQLite and
  workspace paths, Mock Providers, and disposable Qdrant collections.
- Do not add low-value duplicate tests; every new test must close a named gap.
- Use TDD for production behavior/version changes and record the observed RED.
- Preserve SQLite as the primary business/audit database and Qdrant only as the
  vector store.
- Do not stage, commit, push, create/move tags, switch branches, or create a
  worktree.

---

### Task 1: S1～S3 Backend Test Audit

**Files:**
- Read/test: `backend/tests/test_knowledge_*.py`
- Read/test: `backend/tests/test_document_*.py`
- Read/test: `backend/tests/test_markdown_parser.py`
- Read/test: `backend/tests/test_txt_parser.py`
- Read/test: `backend/tests/test_pdf_parser.py`
- Read/test: `backend/tests/test_text_cleaner.py`
- Read/test: `backend/tests/test_chunker.py`
- Read/test: Embedding/VectorStore/ingestion/Retriever test modules
- Modify only if a concrete missing behavior is found: the smallest affected
  test and implementation module

**Interfaces:**
- Consumes: existing ORM/schema/service/API/parser/pipeline contracts.
- Produces: attributable fresh S1～S3 evidence and a documented gap decision.

- [x] **Step 1: Inventory named tests against S1～S3 acceptance**

Map every required layer to concrete test names, including failure/rollback,
text-layer PDF, Mock Embedding, Qdrant payload/store, ingestion compensation,
and Knowledge Base isolation.

- [x] **Step 2: Run the complete S1～S3 focused command**

Run all mapped modules together from `backend/`. Expected: zero failures and
only the known Starlette TestClient/httpx deprecation warning.

- [x] **Step 3: Decide gaps from behavior, not test count**

If the command and inventory demonstrate every S1～S3 acceptance item, record
the suite unchanged. If a real gap appears, add one failing test, observe the
expected RED, implement the minimum fix, and rerun the group.

- [x] **Step 4: Record the S1～S3 checkpoint in the active execution table**

Record exact module scope, pass count, known warning, Mock/live boundaries,
and Codex classification without marking S4～S6 complete early.

---

### Task 2: S4 RAG Query, Chat, Audit, And Tool Test Audit

**Files:**
- Read/test: `backend/tests/test_rag_prompt.py`
- Read/test: `backend/tests/test_rag_schemas.py`
- Read/test: `backend/tests/test_rag_service.py`
- Read/test: `backend/tests/test_rag_api.py`
- Read/test: `backend/tests/test_search_knowledge_base_tool.py`
- Read/test: `backend/tests/test_agent_api.py`
- Modify only if a concrete missing behavior is found: the smallest affected
  test and implementation module

**Interfaces:**
- Consumes: shared Retriever, `RagQueryService`, `RagService`, route error
  mapping, Tool Registry, and Agent integration.
- Produces: fresh evidence for retrieval, answer, sources, audit persistence,
  rollback, and lazy Tool use.

- [x] **Step 1: Inventory S4 behavior and error paths**

Confirm that tests assert requested Top-K, ordered sources, retrieval metadata,
`rag_query_id`, Conversation/answer linkage, zero-hit behavior, full rollback,
Tool bounds/safe failure, and ordinary Agent lazy initialization.

- [x] **Step 2: Run the complete S4 focused command**

Expected: zero failures and only the known Starlette TestClient/httpx warning.

- [x] **Step 3: Apply TDD only for an actual uncovered behavior**

Do not add duplicate Query/Chat/Tool tests when the existing assertions already
prove the acceptance contract.

---

### Task 3: v0.3.0 Release Metadata TDD

**Files:**
- Modify: `backend/tests/test_release_version.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/main.py`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Consumes: existing release metadata consistency test.
- Produces: a single `0.3.0` version across backend package, FastAPI OpenAPI,
  frontend package, and lockfile root package.

- [x] **Step 1: Change the release test expectation to `0.3.0`**

Rename the test functions from Plan 2 wording to release-neutral wording and
set `EXPECTED_RELEASE_VERSION = "0.3.0"` without changing production metadata.

- [x] **Step 2: Run the focused release test and observe RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_release_version.py -q
```

Expected: assertions report current production `0.2.1` values instead of
`0.3.0`.

- [x] **Step 3: Synchronize minimal production metadata**

Change only the project/root-package version values to `0.3.0`; do not alter
dependency versions such as transitive `0.2.x` packages.

- [x] **Step 4: Run release metadata GREEN**

Expected: both release consistency tests pass.

---

### Task 4: S5 Frontend And Sanitized Demo Evidence

**Files:**
- Create: `docs/assets/plan3/knowledge-base-workspace.png`
- Create: `docs/assets/plan3/rag-chat-sources.png`
- Temporary only: ignored Playwright/browser artifacts under
  `output/playwright/`, removed after inspection

**Interfaces:**
- Consumes: current Knowledge workspace and typed RAG UI.
- Produces: build/test evidence, complete synthetic create/upload/ask/source
  Demo assertions, and two sanitized release screenshots.

- [x] **Step 1: Run frontend typecheck, full Vitest, and production build**

Run `npm run typecheck`, `npm test -- --run`, and `npm run build` from
`frontend/`. Record exact file/test/module counts.

- [x] **Step 2: Verify the browser prerequisite and start the local UI**

Confirm `npx` is available. Start the local Vite server without real backend
credentials. Browser calls are intercepted with complete synthetic resources.

- [x] **Step 3: Exercise the complete synthetic flow**

At desktop width: load/select a Knowledge Base, create another, upload a
synthetic `.md`, verify `parsed/chunked/ready`, switch to RAG Chat, create a
Conversation, ask one question, and verify answer/source/score/provenance/audit
IDs. At `390×844`, verify no horizontal overflow and usable controls. Require
zero console errors/warnings.

- [x] **Step 4: Capture and inspect both committed screenshots**

Capture the completed Document view and grounded RAG result. Visually inspect
the actual PNG files and ensure all IDs/content are synthetic and no secret,
local path, response body, or real user data appears.

- [x] **Step 5: Remove temporary browser artifacts**

Keep only the two intentional `docs/assets/plan3/*.png` release assets.

---

### Task 5: S6 Release Documentation, Review, And Bridge Record

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs/21-embedding-provider.md` only if release evidence needs it
- Modify: `docs/22-document-ingestion-pipeline.md` only if release evidence needs it
- Modify: `docs/23-naive-rag.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Create: `docs/reviews/2026-08-02-plan3-v0.3.0-final-review.md`
- Modify: this plan's checkboxes

**Interfaces:**
- Consumes: fresh S1～S5 evidence and current product boundaries.
- Produces: complete release instructions, screenshot links, current
  limitations, final Codex-only review, and Plan 4 bridge readiness.

- [x] **Step 1: Promote the changelog and refresh version/stage wording**

Move current Plan 3 entries under `## [0.3.0] - 2026-08-02`. README files must
say the release candidate is prepared while the tag remains a user action;
they must not falsely report an absent tag.

- [x] **Step 2: Document the runnable Plan 3 workflow and screenshots**

Document Qdrant startup, backend/frontend startup, create/upload/ingest/ask/
source flow, `.md`/`.txt`/text-layer `.pdf` support, and current Mock-only,
non-streaming, no-OCR, no-Advanced-RAG limitations. Link both screenshots.

- [x] **Step 3: Write the formal Codex final review and bridge matrix**

Classify must-fix, fix-later, recorded limitations, and not-applicable items.
Prove the five Plan 4 bridge contracts from code/tests without adding Plan 4
behavior. Record that external review is intentionally not used.

- [x] **Step 4: Update the active execution table honestly**

Mark S1～S5 complete only after evidence exists. Mark S6 release artifacts as
prepared and explicitly leave Plan 3/tag completion pending the user's manual
commit and annotated `v0.3.0` tag. Include the exact tag gate command.

---

### Task 6: Full Verification And Release Handoff

**Files:**
- Modify: documentation evidence/checklists only when actual final output differs

**Interfaces:**
- Consumes: the complete M6 diff.
- Produces: fresh final evidence and a manual commit/tag handoff.

- [x] **Step 1: Run complete backend regression and dependency check**

Use safe temporary state and never discover/read the protected user database.
Run all backend tests plus `pip check` and record exact results.

- [x] **Step 2: Run temporary SQLite migration lifecycle**

Run upgrade head, current/check-heads, `alembic check`, downgrade one revision,
and re-upgrade on a system-temporary SQLite database. Remove the directory.

- [x] **Step 3: Run Docker/Qdrant gates and disposable live smoke**

Run Compose config, verify Qdrant running/restart count zero/loopback-only port/
HTTP health, then run the existing deterministic Mock Provider + temporary
SQLite + random Qdrant collection acceptance. Delete and recheck the collection.

- [x] **Step 4: Run documentation, security, artifact, and Git gates**

Read every Markdown file; validate local links/images; scan changed text for
high-confidence tokens and private-key headers; confirm no executable Plan 4+
or network Tool runtime; confirm no unexpected tracked/untracked artifacts;
run `git diff --check`; review exact changed paths, staged count, branch,
HEAD/origin, old peeled tag targets, and `v0.3.0` absence.

- [x] **Step 5: Run Codex final self-review and affected re-verification**

Fix every must-fix finding via the appropriate RED/GREEN cycle, rerun affected
checks, and report residual limitations. Do not create the commit or tag.

- [x] **Step 6: Hand off exact manual release commands**

Suggest `chore(release): publish v0.3.0 naive rag`, ask the user to commit the
verified diff, then create an annotated `v0.3.0` tag at that commit and verify
its peeled target. Plan 3 is complete only after that separate tag gate passes.
