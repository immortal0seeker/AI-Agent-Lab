# Plan 2 M5 Final Review And Release Handoff Implementation Plan

> **Completion update (2026-07-20):** The user published commit `0e3f3a6`,
> created annotated tag `v0.2.0`, and pushed `main`. Codex verified
> `HEAD == origin/main == v0.2.0^{}`. S8, Batch 14, and Plan 2 are complete.
> References below to a pending tag describe the historical pre-release gate.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the executable review and documentation work for `P2-M5-S7～S8`, leaving only the user-owned release commit and `v0.2.0` tag mutation pending.

**Architecture:** Review the complete Plan 2 delta against the final acceptance checklist, verify it with mocks and temporary SQLite, fix only reproduced release blockers, then publish a formal Codex review and Plan 3 bridge handoff. Preserve truthful Git state until the user creates the release commit and annotated tag.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, SQLite, pytest, React 19, TypeScript 5.9, Vitest 4, Vite 7, Markdown, Git read-only inspection.

## Global Constraints

- Work only on `P2-M5-S7～S8`; do not implement Plan 3 or any deferred Plan 2 capability.
- Do not use subagents, Claude Code, Fable 5, or external review.
- Do not call a real/paid Provider, read a real `.env`/secret/user SQLite database, or invoke a real network Tool.
- Keep `web_fetch` deferred with no executable surface or dependency.
- Keep SQLite as the default and long-term supported primary database.
- Do not stage, commit, push, create/switch branches, or create a tag; the user owns all Git mutations.
- Do not mark `v0.2.0`, S8, or Plan 2 complete until the tag exists on the verified release commit.

---

### Task 1: Freeze The Final Acceptance And Review Matrix

**Files:**

- Review: `docs-plan/00-ALL PLAN/02-PLAN-2 (V1.0).md`
- Review: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Review: all Plan 2 runtime and test paths changed since `v0.1.0`
- Create: `docs/superpowers/specs/2026-07-19-plan2-m5-final-review-release-handoff-design.md`
- Create: `docs/superpowers/plans/2026-07-19-plan2-m5-final-review-release-handoff-implementation.md`

**Interfaces:**

- Consumes: the committed S1～S6 candidate and the Plan 2 final acceptance/bridge checklists.
- Produces: a requirement-to-evidence matrix and a fixed no-tag-mutation boundary.

- [x] **Step 1: Confirm Git and tag baseline**

Run `git status --short --branch`, `git diff --check`, `git diff --cached --name-only`, `git rev-parse HEAD`, `git rev-parse origin/main`, and `git tag --list --sort=version:refname`.

Expected: clean `main`, no staged paths, `HEAD` equals `origin/main` at the S4～S6 commit, and only `v0.1.0` exists.

- [x] **Step 2: Inventory the complete Plan 2 delta**

Run `git log --oneline v0.1.0..HEAD`, `git diff --name-status v0.1.0..HEAD`, and `git diff --stat v0.1.0..HEAD`. Group production ownership into Tool/security, Provider adapter, Agent/persistence/API, frontend, migrations, tests, and docs.

- [x] **Step 3: Self-review this plan**

Confirm every S7/S8 requirement has a task, scan this plan/spec for placeholders or contradictions, and verify no step authorizes a Git mutation or Plan 3 implementation.

---

### Task 2: Review The Complete Plan 2 Candidate

**Files:**

- Review: `backend/app/tools/`
- Review: `backend/app/providers/llm/`
- Review: `backend/app/agents/`
- Review: `backend/app/services/agent_service.py`
- Review: `backend/app/api/v1/agents.py`
- Review: `backend/app/models/agent_run.py`
- Review: `backend/app/models/tool_call.py`
- Review: `backend/alembic/versions/20260717_0002_agent_runs_tool_calls.py`
- Review: `backend/alembic/versions/20260718_0003_agent_run_message_consistency.py`
- Review: relevant backend tests
- Review: `frontend/src/api/agent.ts`
- Review: `frontend/src/pages/AgentPage.tsx`
- Review: `frontend/src/components/agent/`
- Review: relevant frontend tests

**Interfaces:**

- Consumes: the complete committed Plan 2 candidate.
- Produces: evidence for every final acceptance and bridge row plus a classified finding list.

- [x] **Step 1: Review backend boundaries**

Trace Tool metadata/validation/Registry, path enforcement, builtin failures, Provider wire conversion, bounded Agent decisions/timeouts/observations, transaction ownership, ORM constraints, API error redaction, and migration upgrade behavior. Compare each contract with its focused tests and formal docs.

- [x] **Step 2: Review frontend boundaries**

Trace model capability filtering, create/query flows, URL restoration, stale-request gates, loading/empty/error/success states, ToolCall redaction/display, and responsive evidence. Compare each contract with Vitest and the sanitized S4～S6 screenshots.

- [x] **Step 3: Review cross-plan and secret boundaries**

Confirm Plan 1 Chat/Streaming behavior remains covered, `web_fetch` has no runtime surface, no RAG/Embedding/Memory/MCP/Shell/write/delete Tool was added, no real credential or user database is read, and SQLite remains the documented primary database.

- [x] **Step 4: Handle findings**

Classify each item as must fix, later Plan/Step, accepted limitation, or not applicable. For each runtime must-fix, load the TDD skill, add a focused failing regression, observe RED, apply the smallest fix, observe GREEN, and rerun affected suites. Correct documentation truth errors directly and verify their references.

---

### Task 3: Run Fresh Full Verification

**Files:**

- Verify: complete repository candidate
- Temporary only: a newly created system temporary directory and SQLite database

**Interfaces:**

- Consumes: the reviewed candidate and any must-fix repairs.
- Produces: fresh release evidence without a real Provider, network Tool, secret, or user database.

- [x] **Step 1: Run backend and dependency gates**

From `backend/`, run `..\.venv\Scripts\python.exe -m pytest -q` and `..\.venv\Scripts\python.exe -m pip check`.

Expected: all tests pass; only the known Starlette TestClient/httpx deprecation warning may remain; pip reports no broken requirements.

- [x] **Step 2: Run frontend gates**

From `frontend/`, run `npm run typecheck`, `npm run test`, and `npm run build`.

Expected: every command exits 0; `frontend/dist/` remains ignored and untracked.

- [x] **Step 3: Run temporary SQLite migration gates**

Create a new system temporary directory, point `DATABASE_URL` at a SQLite file inside it for each Alembic process, and run `upgrade head`, `current --check-heads`, and `check`. Confirm head `20260718_0003`, then remove only that verified temporary directory.

- [x] **Step 4: Run docs, security, artifact, and boundary gates**

Check every Markdown local link/image, changed/tracked secret patterns, prohibited `.env`/database/build/browser artifacts, screenshot PNG signatures, dependency changes, `web_fetch` runtime absence, later-Plan runtime absence, plan placeholders, staging, and whitespace.

---

### Task 4: Publish Final Review And Bridge Handoff

**Files:**

- Create: `docs/reviews/2026-07-19-plan2-v0.2.0-final-review.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs/11-simple-agent-loop.md`
- Modify: `docs/12-agent-api.md`
- Modify: `docs/13-plan-2-basic-agent.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify: this implementation plan

**Interfaces:**

- Consumes: fresh review findings and verification evidence.
- Produces: truthful final-review, Plan 3 bridge, and user-owned release/tag handoff documentation.

- [x] **Step 1: Write the formal final-review record**

Record reviewed surfaces, finding classification, any RED/GREEN repairs, fresh backend/frontend/SQLite/docs evidence, accepted limitations, and the exact release commit/tag gate. Do not claim external review.

- [x] **Step 2: Synchronize current-stage documents**

Replace pre-S7 wording with “Plan 2 final review passed; release commit/tag pending user action.” Keep `v0.1.0` as the latest existing tag, retain the accepted limitations, and do not claim Plan 3 has started.

- [x] **Step 3: Update the execution table truthfully**

Mark S7 complete only after review/verification. Record all five bridge checks as freshly passed. Mark S8 as tag-ready/pending user tag and keep Batch 14 and Plan 2 incomplete until the tag exists.

- [x] **Step 4: Check executed plan items**

Mark only evidenced checkboxes in this file. The final tag-verification item remains unchecked until the user creates `v0.2.0`.

---

### Task 5: Final Reverification And Manual Git Handoff

**Files:**

- Verify: the final unstaged S7～S8 candidate

**Interfaces:**

- Consumes: Task 4 documentation updates.
- Produces: a clean, auditable handoff for the user's manual release commit and annotated tag.

- [x] **Step 1: Re-run affected and full gates**

Repeat all verification affected by review/document edits, including full backend/frontend, temporary SQLite, docs/link/security/Plan-boundary scans, and `git diff --check`.

- [x] **Step 2: Verify Git scope**

Confirm no staged path, no `v0.2.0` tag, no unexpected generated artifact, and only S7～S8 review/release documentation plus any evidence-backed must-fix paths differ from the baseline.

- [x] **Step 3: Deliver the manual sequence**

Suggest `chore: release v0.2.0 basic agent` for the user's commit, then instruct the user to create annotated tag `v0.2.0` on that commit. Do not run either command. State that `P3-M1-S1` can begin only after a later clean-worktree/tag-target verification.

- [x] **Step 4: Verify the user-created tag in a later turn**

After the user commits and tags, verify `git status`, `HEAD == origin/main` as applicable, `git tag --list v0.2.0`, annotated tag metadata, and the peeled tag target. Only then mark S8, Batch 14, and Plan 2 complete and enter `P3-M1-S1`.

Verified on 2026-07-20: `HEAD` and `origin/main` both resolve to
`0e3f3a66e1322c565f2056696f7e482cedbb5f6c`; `v0.2.0` is an annotated tag and
its peeled target resolves to the same release commit.
