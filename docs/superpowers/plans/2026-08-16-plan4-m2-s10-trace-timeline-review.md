# Plan 4 M2 S10 Trace Timeline Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. This repository does not use subagents
> for this batch. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the Trace Timeline usage guide, complete a Codex-only M2
review, repair documentation drift, and prove that P4-M3-S1～S3 may begin.

**Architecture:** This is a documentation and verification closeout. Existing
M2 runtime is audited read-only first; production code changes are allowed only
for a reproduced Critical or Important M2 defect and must follow strict TDD.
The canonical foundation remains `docs/30-trace-observability.md`, while the
new `docs/31-trace-timeline.md` becomes the operator/developer usage guide.

**Tech Stack:** Markdown, PowerShell, Git, Python 3.11, pytest, Alembic,
TypeScript, Vitest, Vite, Playwright CLI, SQLite.

## Global Constraints

- Work only on `P4-M2-S10`; do not start P4-M3 runtime.
- Codex self-review is the only review gate. Do not request, run, wait for,
  cite, or depend on Claude Code or another external reviewer.
- Do not read or modify `backend/ai_agent_lab.db`, real `.env`, credentials,
  browser profiles, or system credential stores.
- Do not call real paid Providers, real network Tools, or a real Qdrant
  collection for this SQLite/documentation closeout.
- Tests use system-temporary SQLite, document storage, synthetic records, and
  Mock Providers only.
- Do not create/switch branches or worktrees and do not stage, commit, push,
  pull, merge, rebase, or mutate tags. The user owns Git operations.
- If a Critical or Important M2 defect is reproduced, add a failing focused
  test before the minimal implementation fix and rerun matching/full gates.
- Do not implement Metadata Filtering, BM25, Hybrid Search, RRF, Parent-Child,
  Query Rewrite, Rerank, Evaluation, Agent/Tool Trace, Memory, Agent Runtime v2,
  Human Approval, MCP, OCR, or multimodal behavior.

---

### Task 1: Independent M2 Contract Audit And Documentation RED

**Files:**
- Read: `backend/app/observability/*.py`
- Read: `backend/app/rag/retrieval_recorder.py`
- Read: `backend/app/services/trace_query_service.py`
- Read: `backend/app/api/v1/traces.py`
- Read: `backend/app/schemas/trace_query.py`
- Read: `frontend/src/api/traces.ts`
- Read: `frontend/src/types/trace.ts`
- Read: `frontend/src/pages/TraceTimelinePage.tsx`
- Read: `frontend/src/components/trace/*.tsx`
- Read: `backend/tests/test_llm_trace.py`
- Read: `backend/tests/test_rag_trace.py`
- Read: `backend/tests/test_trace_api.py`
- Read: `backend/tests/test_trace_query_service.py`
- Read: `frontend/src/pages/TraceTimelinePage.dom.test.tsx`
- Read: `docs/reviews/2026-08-08-plan4-m2-s1-s3-review.md`
- Read: `docs/reviews/2026-08-08-plan4-m2-s4-s6-review.md`
- Read: `docs/reviews/2026-08-09-plan4-m2-s7-s9-review.md`

**Interfaces:**
- Consumes: M1 baseline commit `c68d059`, M2 release HEAD
  `be7ee17105ebd8421874e45eba565e1545b086e3`.
- Produces: an evidence matrix covering Trace write/read/UI contracts and a
  classified finding list used by Tasks 2 and 4.

- [ ] **Step 1: Confirm the immutable starting gate**

Run:

```powershell
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
git diff --cached --name-only
git log -4 --oneline --decorate
```

Expected: `main`; HEAD and `origin/main` are both
`be7ee17105ebd8421874e45eba565e1545b086e3`; status and staged output are
empty. Stop before writes if any value differs.

- [ ] **Step 2: Review the complete M2 Git range and implementation seams**

Run:

```powershell
git diff --stat c68d059..HEAD
git diff --name-status c68d059..HEAD
git diff c68d059..HEAD -- backend/app/observability backend/app/rag backend/app/services/trace_query_service.py backend/app/api/v1/traces.py backend/app/schemas/trace_query.py frontend/src/api/traces.ts frontend/src/types/trace.ts frontend/src/pages/TraceTimelinePage.tsx frontend/src/components/trace
```

Inspect against this matrix:

```text
LLM success/failure -> safe Trace Run/Step + caller transaction
RAG Query/Chat -> ordered retrieval/Prompt/LLM/final evidence
Retrieval candidates -> stable IDs/ranks/scores + bounded preview/metadata
Trace reads -> limit 1..100 + deterministic order + <=4 detail queries
Trace errors -> safe 404/422/503 without Provider/vector initialization
Timeline -> deep link + independent states + stale/unmount guards
Security -> no prompt/context/vector payload/secret/error-body replay
Boundary -> no Agent/Tool Trace, Advanced RAG, Evaluation, or Plan 5 runtime
```

Classify every finding as must fix, fix later, recorded limitation, or not
applicable. Reproduce suspected runtime issues before editing.

- [ ] **Step 3: Run the documentation RED gate**

Run this read-only assertion before creating S10 deliverables:

```powershell
$failures = @()
if (-not (Test-Path -LiteralPath 'docs/31-trace-timeline.md')) {
  $failures += 'missing docs/31-trace-timeline.md'
}
if (-not (Test-Path -LiteralPath 'docs/reviews/2026-08-16-plan4-m2-final-review.md')) {
  $failures += 'missing M2 final review'
}
$failures += @(
  Select-String -LiteralPath 'docs/01-architecture.md' `
    -Pattern 'Trace API, and Timeline UI remain later|no\s+Trace API/Timeline' `
    -Encoding UTF8 | ForEach-Object { "stale architecture:$($_.LineNumber)" }
)
$failures += @(
  Select-String -LiteralPath 'docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md' `
    -Pattern 'Claude' -Encoding UTF8 |
    ForEach-Object { "stale review policy:$($_.LineNumber)" }
)
$failures
if ($failures.Count -eq 0) { throw 'RED gate unexpectedly passed' }
exit 1
```

Expected: FAIL for the two missing S10 artifacts, the verified stale
architecture claims, and legacy external-review instructions.

- [ ] **Step 4: Run focused M2 tests before documentation changes**

Run from the repository root with no real credentials:

```powershell
& '.venv/Scripts/python.exe' -m pytest `
  backend/tests/test_trace_models.py `
  backend/tests/test_trace_schemas.py `
  backend/tests/test_trace_types.py `
  backend/tests/test_trace_service.py `
  backend/tests/test_trace_context.py `
  backend/tests/test_llm_trace.py `
  backend/tests/test_rag_trace.py `
  backend/tests/test_retrieval_models.py `
  backend/tests/test_retrieval_schemas.py `
  backend/tests/test_trace_query_schemas.py `
  backend/tests/test_trace_query_service.py `
  backend/tests/test_trace_api.py
```

Expected: all selected tests pass with only the known Starlette/httpx
TestClient deprecation warning. If a product failure appears, invoke
systematic-debugging and apply the TDD repair policy before continuing.

---

### Task 2: Publish The Usage Guide And Reconcile Current Status

**Files:**
- Create: `docs/31-trace-timeline.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/30-trace-observability.md`
- Modify: `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: the verified API/UI behavior and findings from Task 1.
- Produces: one canonical usage guide and consistent project-facing M2 status
  for the final review in Task 4.

- [ ] **Step 1: Create the Trace Timeline usage guide**

Use `apply_patch` to create `docs/31-trace-timeline.md` with these exact
sections and facts:

```markdown
# Trace Timeline

## Current Scope
## Open And Navigate The Workspace
## Trace Read API
## Read A Run
## Read The Step Timeline
## Read Retrieval Evidence
## Common Replay Patterns
## Loading, Empty, Error, And Failure States
## Security And Data Boundaries
## Troubleshooting
## Acceptance Evidence
## Current Limitations
## Verification References
```

Required contract statements:

```text
GET /api/v1/traces?limit=50; accepted range 1..100
Run ordering created_at DESC,id DESC; input preview <=160 Unicode chars
Detail Step ordering step_index,id; retrieval ordering created_at,id
Candidate ordering rank,id; persisted preview <=500 chars
unknown valid UUID -> safe trace_run_not_found 404
malformed UUID/limit -> shared 422 validation envelope
deep link -> ?workspace=trace&run=<uuid>
retrieval association -> output_json.retrieval_run_id
read surface -> SQLite only, no Provider/Qdrant/external request
no reconstructed full Prompt/context/vector payload/deleted source
```

Link the desktop/mobile images in `docs/assets/plan4/`, the canonical
foundation, the three prior batch reviews, backend/frontend tests, and the M2
final review.

- [ ] **Step 2: Repair architecture and status drift**

Use `apply_patch` to make these statements consistent:

```text
README / README_CN: M2 complete through S10; link docs/31 and M2 final review
CHANGELOG: add Trace Timeline guide and Codex-only M2 closeout under Unreleased
docs/01: Trace API/Timeline are implemented; only Agent/Tool hooks and later
         Advanced RAG/Evaluation remain deferred
docs/30: replace the S10-owned future statement with links to docs/31 and the
         completed M2 final review
```

Do not change version metadata or create a release entry.

- [ ] **Step 3: Normalize the active Plan 4 review policy**

Use `apply_patch` on the Plan 4 execution table so that:

```text
all milestone and Step review cells use Codex / Codex self-review
Batch 7 and P4-M2-S10 are marked complete
the external-review section becomes a Codex review-node section
the remediation workflow starts from Codex findings
the file contains zero occurrences of the token Claude
future Step status remains incomplete
```

Do not alter Step deliverables, order, or Plan boundaries.

- [ ] **Step 4: Run the documentation GREEN gate**

Run:

```powershell
if (-not (Test-Path -LiteralPath 'docs/31-trace-timeline.md')) { throw 'missing guide' }
$staleArchitecture = @(Select-String -LiteralPath 'docs/01-architecture.md' `
  -Pattern 'Trace API, and Timeline UI remain later|no\s+Trace API/Timeline' `
  -Encoding UTF8)
$staleReview = @(Select-String `
  -LiteralPath 'docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md' `
  -Pattern 'Claude' -Encoding UTF8)
if ($staleArchitecture.Count -ne 0) { $staleArchitecture; throw 'stale architecture' }
if ($staleReview.Count -ne 0) { $staleReview; throw 'stale review policy' }
Select-String -LiteralPath 'README.md','README_CN.md','CHANGELOG.md',` 
  'docs/30-trace-observability.md' -Pattern '31-trace-timeline|M2.*S10' `
  -Encoding UTF8
```

Expected: no stale matches; all current-facing documents expose the S10 guide
or completed status.

---

### Task 3: Fresh Full Verification And Headed Timeline Acceptance

**Files:**
- Verify: `backend/tests/`
- Verify: `frontend/src/`
- Verify: `backend/alembic/`
- Verify: `docs/assets/plan4/trace-timeline-desktop.png`
- Verify: `docs/assets/plan4/trace-timeline-mobile.png`

**Interfaces:**
- Consumes: unchanged or TDD-repaired M2 runtime plus Task 2 documentation.
- Produces: exact fresh evidence for the M2 final review.

- [ ] **Step 1: Run the complete backend suite in an isolated directory**

Create a unique system-temporary directory, remove credential environment
variables without reading them, set `APP_ENV=test`, a temporary SQLite
`DATABASE_URL`, temporary `DOCUMENT_STORAGE_ROOT`, and `PYTHONPATH` to the
backend. From the temporary working directory run:

```powershell
& 'F:/MyProjects/AI-Agent-Lab/.venv/Scripts/python.exe' -m pytest `
  -c 'F:/MyProjects/AI-Agent-Lab/backend/pyproject.toml' `
  'F:/MyProjects/AI-Agent-Lab/backend/tests'
& 'F:/MyProjects/AI-Agent-Lab/.venv/Scripts/python.exe' -m pip check
```

Validate the exact temporary path is below the system temp root before
recursive removal. Expected: all backend tests pass; `pip check` reports no
broken requirements; only the known TestClient warning may remain.

- [ ] **Step 2: Run the temporary SQLite migration lifecycle**

With a second validated system-temporary SQLite URL and no `.env` loading, run:

```powershell
& '.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini upgrade head
& '.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini current --check-heads
& '.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini check
& '.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini downgrade -1
& '.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini upgrade head
& '.venv/Scripts/python.exe' -m alembic -c backend/alembic.ini current --check-heads
```

Expected final head: `20260808_0009`. Validate and remove only the exact
temporary directory.

- [ ] **Step 3: Run complete frontend verification**

Run:

```powershell
npm run typecheck
npm test -- --run
npm run build
```

Run from `frontend/`. If sandboxed Vite output recreation raises the already
known Windows `EPERM`, rerun the identical approved build outside the sandbox;
do not change source to work around an environment restriction.

Expected: typecheck, all Vitest files/tests, and production build pass.

- [ ] **Step 4: Run fresh headed browser acceptance**

Before browser work, load the `playwright` skill. Start the built frontend on
`127.0.0.1:4173` and use a temporary Playwright route-mock script with only
synthetic health/list/detail JSON. Validate:

```text
1440x900: recent Run auto-selects and writes run=<uuid>
deep link: failed Run outside recent list restores with failed Run/Step UI
timeline: rag_retrieve -> build_prompt -> llm_call -> final_answer
candidates: rank 1 before rank 2; IDs and exact non-null score names visible
metadata: Run and Step JSON details expand
390x844: list/detail stack without horizontal overflow
requests: health/list/detail succeed; failed requests = 0
console: errors = 0; warnings = 0
```

Inspect the existing desktop/mobile assets visually. Replace them only if the
fresh current UI materially differs. Stop the server, close the browser, remove
only the exact temporary mock/session files, and verify port 4173 has no
listener.

---

### Task 4: Publish The M2 Final Review And Close The Gate

**Files:**
- Create: `docs/reviews/2026-08-16-plan4-m2-final-review.md`
- Modify: `docs/31-trace-timeline.md`
- Modify: `docs/30-trace-observability.md`
- Modify: `README.md`
- Modify: `README_CN.md`

**Interfaces:**
- Consumes: Task 1 findings and exact Task 3 verification output.
- Produces: the authoritative M2 completion decision and M3 entry gate.

- [ ] **Step 1: Write the consolidated M2 review**

Use `apply_patch` to create the review with these sections:

```markdown
# Plan 4 M2 Trace Integration And Timeline Final Review

## Decision
## Scope And Git Baseline
## S1-S10 Acceptance Matrix
## Delivered M2 Contracts
## Fresh Verification Evidence
## Findings And Disposition
### Must Fix - Fixed
### Fix Later
### Recorded Limitations
### Not Applicable
## Security And Plan Boundary Review
## Codex Self-Review
## M3 Entry Gate
## Git Handoff
```

Record exact test counts, migration head, browser viewports, link counts,
changed-path count, and Git refs from the actual commands. State explicitly
that no external review was requested or used. Do not invent evidence or copy
stale counts.

- [ ] **Step 2: Link the final review from current documentation**

Use `apply_patch` so README, README_CN, docs/30, and docs/31 link the new review.
Keep earlier batch reviews as detailed supporting evidence.

- [ ] **Step 3: Run Codex final self-review**

Review the complete diff and classify findings. Confirm:

```text
only S10 documentation/review artifacts changed unless a TDD repair was needed
M2 S1-S10 acceptance is supported by implementation and fresh evidence
routes remain thin and read queries remain bounded/no-N+1
Trace transaction/error/security contracts are unchanged or correctly repaired
Timeline deep-link/state/order/source-ID behavior is covered
no Advanced RAG/Evaluation/Agent-Tool/later-Plan runtime was added
no real Provider/Qdrant/network Tool/user database/credential was accessed
all active Plan 4 review instructions are Codex-only
```

Fix every must-fix, rerun matching verification, and update the review before
continuing.

- [ ] **Step 4: Run final links, security, artifacts, and Git gates**

Run a Markdown link checker over root README/AGENTS plus all `docs/` and
`docs-plan/` Markdown, excluding fenced and inline code from link parsing.
Then run:

```powershell
git diff --check
git diff --cached --check
git diff --cached --name-only
git ls-files '*.pyc' '*.pyo' '.playwright-cli/**' 'output/playwright/**'
git status --short --untracked-files=all -- '*.pyc' '*.pyo' '*.db' '.playwright-cli/**' 'output/playwright/**'
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.3.1^{}'
git -c core.quotepath=false status --short --untracked-files=all
```

Scan changed/new text files for high-confidence API keys, bearer tokens, and
private-key headers; scan changed paths for later-Plan runtime directories and
unexpected generated artifacts. Expected: zero missing links, secret/private
key matches, staged paths, temporary artifacts, generated databases, and later
Plan runtime paths. Branch/refs remain unchanged.

- [ ] **Step 5: Prepare the manual handoff**

Do not stage or commit. Report the M2 decision, exact verification evidence,
findings/limitations, M3 entry decision, changed paths, staged count, and the
suggested manual commit:

```text
fix(observability): expose trace run metrics
```
