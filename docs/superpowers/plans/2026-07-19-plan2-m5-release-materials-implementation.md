# Plan 2 M5 Frontend Checks And Release Materials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P2-M5-S4～S6` with fresh frontend evidence, sanitized Agent ToolCall screenshots, and documentation that accurately describes the pre-tag Plan 2 release boundary.

**Architecture:** Keep the existing React and backend runtime unchanged unless a verified UI regression requires a TDD fix. Use Playwright against a local Vite server with intercepted synthetic API responses, then synchronize only current-stage documentation and release-candidate assets. Preserve `[Unreleased]` and `v0.1.0` as the current tagged release until S7～S8.

**Tech Stack:** React 19, TypeScript 5.9, Vite 7, Vitest 4, Playwright CLI, Markdown, FastAPI/pytest regression suite, Alembic, temporary SQLite.

## Global Constraints

- Work only on `P2-M5-S4～S6`; do not perform S7 final review, create/tag `v0.2.0`, or begin Plan 3.
- Do not call a real/paid Provider, read a real `.env`/secret/user SQLite database, or invoke a real network Tool.
- `web_fetch` remains deferred with no file, schema, Registry export, dependency, network implementation, API, or UI.
- Use fixed synthetic browser data and a local Vite server; do not persist the mock run to any database.
- Preserve Plan 1 Chat/Streaming/Provider behavior and the current Agent API/runtime contract.
- Do not add Agent streaming, run list, polling, cancel/resume/retry, strict persisted ToolCall sequence, Trace, RAG, Memory, MCP, shell, or file-writing Tools.
- Do not use Claude Code, Fable 5, subagents, or external review.
- Do not stage, commit, push, tag, or create/switch branches; the user performs Git integration manually.

---

### Task 1: Freeze The S4～S6 Evidence Matrix

**Files:**

- Review: `docs-plan/00-ALL PLAN/02-PLAN-2 (V1.0).md`
- Review: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Review: `frontend/src/components/agent/`
- Review: `frontend/src/pages/AgentPage.tsx`
- Review: `README.md`
- Review: `README_CN.md`
- Review: `CHANGELOG.md`
- Review: `docs/10-tool-calling-design.md`
- Review: `docs/11-simple-agent-loop.md`
- Review: `docs/12-agent-api.md`

**Interfaces:**

- Consumes: the approved Plan 2 S4～S6 acceptance criteria and current M4/M5 evidence.
- Produces: the requirements-to-evidence matrix in the design document and a no-runtime-change default.

- [x] **Step 1: Confirm the Git batch boundary**

Run from the repository root:

```powershell
git status --short --branch
git diff --check
git diff --cached --check
git diff --cached --name-only
git rev-parse HEAD
git rev-parse origin/main
```

Expected: clean `main`, no staged paths, and `HEAD` equals `origin/main` at the committed S1～S3 baseline.

- [x] **Step 2: Confirm no deeper collaboration rules override the root**

Run:

```powershell
Get-ChildItem -Path . -Recurse -Filter AGENTS.md -File
```

Expected: only the root `AGENTS.md` is present.

- [x] **Step 3: Review the matrix for scope and placeholders**

Run:

```powershell
$placeholderPattern = @('T' + 'BD', 'T' + 'ODO', 'implement' + ' later', 'fill in' + ' details') -join '|'
Select-String -LiteralPath docs/superpowers/specs/2026-07-19-plan2-m5-release-materials-design.md -Pattern $placeholderPattern
```

Expected: no matches; every S4～S6 acceptance row has an existing-evidence, gap, and minimal-addition entry.

---

### Task 2: Refresh Frontend Automated Evidence

**Files:**

- Verify: `frontend/src/`
- Modify only after a reproduced defect: the smallest relevant existing frontend source and test file

**Interfaces:**

- Consumes: the existing AgentPage, AgentRunPanel, ToolCallTimeline, ToolCallCard, URL helpers, and typed API client.
- Produces: fresh typecheck, Vitest, and production-build evidence without intentionally changing runtime behavior.

- [x] **Step 1: Run TypeScript validation**

Run from `frontend/`:

```powershell
npm run typecheck
```

Expected: exit 0 with no TypeScript errors.

- [x] **Step 2: Run the complete frontend test suite**

Run:

```powershell
npm run test
```

Expected: all 16 test files and 79 tests pass. If counts changed because a real defect is found later, record the new exact count.

- [x] **Step 3: Run the production build**

Run:

```powershell
npm run build
```

Expected: exit 0 and Vite transforms the production modules. `frontend/dist/` remains ignored and untracked.

- [x] **Step 4: Apply TDD only if a real defect appears**

If an automated or browser check exposes a behavior defect, add one focused test that reproduces it, run that test to observe the expected failure, implement the smallest source fix, rerun the focused test to green, and then repeat Steps 1～3. If no defect appears, leave `frontend/src/` unchanged and record TDD as not applicable to this verification/documentation batch.

---

### Task 3: Run Local Mock Browser Acceptance And Capture Assets

**Files:**

- Create: `docs/assets/plan2/agent-tool-call-desktop.png`
- Create: `docs/assets/plan2/agent-tool-call-mobile.png`
- Temporary only: `output/playwright/` and its standard-library Mock API script

**Interfaces:**

- Consumes: the existing Vite application, a temporary local Mock API, and a Playwright CLI session.
- Produces: sanitized desktop/mobile images and browser evidence for state, ToolCall details, IDs, and responsive overflow.

- [x] **Step 1: Confirm Playwright prerequisites**

Run:

```powershell
Get-Command npx
Get-Item C:\Users\liuyi\AppData\Local\npm-cache\_npx\31e32ef8478fbf80\node_modules\@playwright\cli\playwright-cli.js
```

Expected: `npx` and the already cached CLI entry resolve. The WindowsApps Bash stub cannot run the bundled shell wrapper in this managed session, so invoke the cached entry with `node.exe` and do not download or install a package.

- [x] **Step 2: Start scoped local Vite and Mock API processes**

Confirm ports 5173 and 8000 have no listener. Create `output/playwright/`, add a temporary Python standard-library HTTP server with fixed `/health`, `/models`, Agent POST, AgentRun GET, and ToolCall GET responses, then run Vite on `127.0.0.1:5173` and the Mock API on `127.0.0.1:8000` in separate tool-managed long-running cells.

Expected: both local endpoints become reachable; the project backend, Provider configuration, network Tools, and SQLite are never started or opened.

- [x] **Step 3: Submit the synthetic task in a named browser session**

Open `http://127.0.0.1:5173/?workspace=agent` in a named session. The Mock API returns:

- `/health`: `{ "status": "ok", "service": "ai-agent-lab-backend" }`;
- `/models`: one `supports_tools=true` Mock model plus one filtered `supports_tools=false` model;
- `POST /agents/runs`: a completed synthetic run with one ToolCall;
- `/agents/runs/<run-id>`: the same completed synthetic run;
- `/agents/runs/<run-id>/tool-calls`: one successful `read_file` call with `README.md`, 25 ms, bounded summary, and synthetic Provider/database IDs.

Fill `Read README.md and summarize the workspace structure.`, submit through the visible form, and confirm the frontend writes `run=00000000-0000-0000-0000-000000000101`. Reload that URL to verify the two GET resources restore the result.

Expected: browser network records contain only the local Vite and Mock API origins.

- [x] **Step 4: Verify the 1280×900 desktop state**

Resize to `1280 900`, snapshot, and verify visible text for `Agent`, `Completed`, `Final answer`, `read_file`, `README.md`, `Success`, `25 ms`, `Run ID`, `Conversation ID`, `Provider call ID`, and `Database ID`. Evaluate `document.documentElement.scrollWidth <= window.innerWidth`.

Expected: all required text is present and the overflow expression is `true`.

- [x] **Step 5: Capture and inspect the desktop image**

Save `output/playwright/agent-tool-call-desktop.png` at the same 1280px desktop breakpoint with a 1200px documentation canvas, visually inspect it, and confirm that it contains only synthetic IDs/content and no credential, local absolute path, browser profile, or user data.

- [x] **Step 6: Verify and capture the 390×844 mobile state**

Resize to `390 844`, re-snapshot, verify the same core ToolCall fields remain reachable, and evaluate the same overflow expression. Capture the documentation asset at the same 390px mobile breakpoint with a 1600px canvas so the complete result is visible, then visually inspect it.

Expected: no horizontal overflow and no clipped secret/path content.

- [x] **Step 7: Promote only reviewed assets and clean temporary state**

Copy the two inspected PNG files into `docs/assets/plan2/`, close the named browser session, terminate only the two recorded tool-managed process cells, and remove `output/playwright/` plus `.playwright-cli/` after confirming both resolved paths are inside the repository.

Expected: only the two `docs/assets/plan2/*.png` files remain; no temporary process/profile/log/output artifact remains.

---

### Task 4: Synchronize README And Plan 2 Documentation

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs/11-simple-agent-loop.md`
- Create: `docs/13-plan-2-basic-agent.md`

**Interfaces:**

- Consumes: implemented M1～M4 behavior, S1～S3 hardening facts, and Task 3 screenshots.
- Produces: accurate bilingual startup/current-stage documentation and a consolidated pre-tag Plan 2 release-candidate boundary.

- [x] **Step 1: Correct current stage and next-batch text**

Set the completed Plan 2 range to `P2-M1-S1` through `P2-M5-S6`, retain `v0.1.0` as the current release, and name `P2-M5-S7～S8` as the next batch. Do not state that Plan 2 or `v0.2.0` is finally released.

- [x] **Step 2: Correct stale Tool Calling and Agent Loop statements**

In `docs/10-tool-calling-design.md`, replace the claims that Agent API/frontend visualization are absent or future with the implemented plural API and read-only UI boundary. In `docs/11-simple-agent-loop.md`, replace the stale M4-next-batch paragraph with the current UI, URL restore, synchronous execution, and remaining limitations.

- [x] **Step 3: Keep startup and security instructions explicit**

Document that the tracked model remains `supports_tools=false`; using the Agent workspace requires an explicitly tools-capable local Registry entry and configured Provider. Real credentials stay only in untracked `.env`/environment variables. The two implemented Tools remain `read_file` and `list_dir`; `web_fetch` remains deferred and absent.

- [x] **Step 4: Add the Plan 2 release-candidate document**

Create `docs/13-plan-2-basic-agent.md` with release boundary, implemented Tool/Agent/API/UI surface, security model, verification model, sanitized desktop/mobile screenshots, and current limitations. Label it a release candidate/pre-tag document and link to `docs/10`, `docs/11`, and `docs/12`.

- [x] **Step 5: Add the new document to both README indexes**

Link the release-candidate document from the English and Chinese release-documentation lists and embed or link the Plan 2 screenshot section without removing the Plan 1 assets.

---

### Task 5: Update CHANGELOG And Execution Evidence

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify: `docs/superpowers/plans/2026-07-19-plan2-m5-release-materials-implementation.md`

**Interfaces:**

- Consumes: verified Tasks 2～4 evidence.
- Produces: `[Unreleased]` release-candidate notes, completed S4～S6 rows, and an auditable batch record.

- [x] **Step 1: Extend `[Unreleased]` without creating a release heading**

Add the sanitized Plan 2 screenshots/release-candidate documentation and S1～S3 security/test hardening. Add an `[Unreleased]` `### Known Limitations` section covering Mock-only Provider acceptance, synchronous/non-streaming Agent execution, no run list/polling/cancel/resume/retry, no strict persisted ToolCall sequence or Agent-linked LLM usage, tracked model Tool support disabled, and deferred `web_fetch`.

- [x] **Step 2: Mark only Batch 13 and S4～S6 complete**

Update the execution table rows for Batch 13 and `P2-M5-S4～S6` to completed. Leave Batch 14 and S7～S8 pending, including the `v0.2.0` tag row.

- [x] **Step 3: Record exact acceptance evidence**

Append a dated S4～S6 record containing automated frontend results, browser viewport/overflow checks, screenshot paths, documentation/link/security scans, full verification, and Codex self-review classifications. State explicitly that no real Provider/network Tool/user database, Claude/Fable, subagent, final tag, or Plan 3 capability was used.

- [x] **Step 4: Check every implementation-plan checkbox only after its evidence exists**

Replace each executed `- [ ]` in this file with `- [x]`. Do not check a step on intent alone.

---

### Task 6: Fresh Full Verification And Codex Self-Review

**Files:**

- Verify: all current batch changes
- Modify only for must-fix findings: the smallest in-scope path plus its relevant test/documentation

**Interfaces:**

- Consumes: Tasks 1～5 outputs.
- Produces: completion evidence and a clean unstaged handoff for the user's manual commit.

- [x] **Step 1: Run the complete backend suite and dependency check**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: all tests pass; only the already known Starlette TestClient/httpx deprecation warning may remain; pip reports no broken requirements.

- [x] **Step 2: Re-run the complete frontend gate**

Run from `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: all commands exit 0.

- [x] **Step 3: Verify Alembic with a newly created temporary SQLite database**

Create a new system temporary directory, set `DATABASE_URL` only for the command process, and run `alembic upgrade head`, `alembic current --check-heads`, and `alembic check`. Confirm head `20260718_0003`, then remove only that verified temporary directory. Never open or migrate `backend/ai_agent_lab.db` or another user database.

- [x] **Step 4: Run documentation and boundary scans**

Verify all Markdown local links/images resolve; changed paths contain no real secret-like values, `.env`, database, build output, Playwright temporary artifact, or unexpected binary; `web_fetch` still has no runtime/file/dependency surface; no later-Plan runtime appears; screenshots contain only synthetic values; and no plan placeholder/unchecked executed step remains.

- [x] **Step 5: Run final Git checks**

Run:

```powershell
git diff --check
git diff --cached --check
git diff --cached --name-only
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Expected: no whitespace error, no staged path, only S4～S6 files are modified/untracked, and `HEAD`/`origin/main` remain unchanged from the batch baseline.

- [x] **Step 6: Complete Codex self-review**

Classify findings as must fix, later Step, accepted limitation, or not applicable. Fix every must-fix item in scope and repeat the affected verification. Leave S7 full Plan review and S8 tag/bridge finalization pending. Do not stage or commit; suggest `docs(plan2): prepare basic agent release materials` for the user's manual commit.
