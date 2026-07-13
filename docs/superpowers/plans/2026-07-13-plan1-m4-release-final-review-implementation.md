# Plan 1 v0.1.0 Release And Final Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P1-M4-S7` and `P1-M4-S8` by producing sanitized release materials, completing the expanded Codex final review, passing the complete Plan 1 acceptance suite, and tagging the user-created release commit as `v0.1.0`.

**Architecture:** Release work is documentation- and evidence-first. Browser assets are generated from deterministic intercepted API responses, the final review operates on one release candidate, and production code changes only when a verified must-fix finding has a failing regression test. The user owns Git commits; Codex creates the annotated tag only after the verified release commit exists.

**Tech Stack:** Git, Markdown, Python 3.11, FastAPI, SQLAlchemy/Alembic, pytest, React 19, TypeScript, Vite, Vitest, Playwright CLI, SQLite.

## Execution Amendment

On 2026-07-13 the user cancelled the manual Cursor/Fable 5 gate because its
quota was insufficient and assigned the remaining review, correction, and
verification work to Codex. Task 5 and later Fable-specific instructions below
are retained as the originally approved workflow but are superseded and treated
as not applicable. No Fable result is claimed. Claude Code also remains
cancelled. The active gate sequence is expanded Codex review, TDD fixes, full
verification, user manual commit, then the Codex-created annotated tag.

## Global Constraints

- Scope is exactly `P1-M4-S7` through `P1-M4-S8`.
- Do not implement Tool Calling, Agent Loop, RAG, Memory, persistent Trace, Provider retry/fallback, MCP, Voice, Vision, Desktop, or later-Plan behavior.
- Do not read a real `.env`, secret, API key, browser profile, credential store, or user-local SQLite database.
- Do not call a real or paid project LLM Provider. Browser and backend Chat checks use mocks only.
- Do not delete or rebuild the user's ignored local SQLite database.
- Do not run or retry a Claude Code review; the user explicitly cancelled that review path.
- Do not claim a Fable 5 result; that review path was cancelled by the user.
- The user creates Git commits manually. Codex must not stage or commit.
- Create `v0.1.0` only after the user confirms the verified release commit and the worktree is clean.
- Use an annotated tag with message `AI Agent Lab v0.1.0`; do not push unless separately requested.
- Use `apply_patch` for tracked text edits and temporary review/browser scripts.
- If review reveals a behavior defect, use systematic debugging and TDD before changing production code.

---

## File Map

### Release files created by this plan

- `CHANGELOG.md`: `v0.1.0` feature, reliability/security, and limitation history.
- `docs/02-plan-1-foundation.md`: durable Plan 1 release summary, acceptance boundary, and Plan 2 bridge.
- `docs/assets/plan1/chat-workspace-desktop.png`: sanitized 1440x900 mocked Chat screenshot.
- `docs/assets/plan1/chat-workspace-mobile.png`: sanitized 390x844 mocked Chat screenshot.
- `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md`: expanded Codex final review record and external-review decision.

### Existing files updated by this plan

- `README.md`: English `v0.1.0` release entry point and screenshot links.
- `README_CN.md`: Chinese release entry point matching the English factual boundary.
- `docs/00-project-overview.md`: Plan 1 completion and Plan 2 handoff.
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`: Batch 12, final acceptance, and bridge evidence.
- `docs/superpowers/specs/2026-07-13-plan1-m4-release-final-review-design.md`: approved design already created before this plan.
- `docs/superpowers/plans/2026-07-13-plan1-m4-release-final-review-implementation.md`: this execution plan.

### Conditional behavior-fix files

No production file is pre-authorized merely because this is a release batch. If a Codex finding is a verified must-fix behavior defect, record the exact affected test and production paths in the final review document before editing them, then execute the RED-GREEN-REFACTOR cycle in Task 6.

---

### Task 1: Verify The Committed Baseline

**Files:**
- Read: `AGENTS.md`
- Read: `AGENTS_CN.md`
- Read: `docs-plan/00-ALL PLAN/00-AI Agent Lab或AI Engineering Workspace 项目设计文档V1.0.md`
- Read: `docs-plan/00-ALL PLAN/01-PLAN-1 (V1.0).md`
- Read: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`
- Read: `README.md`
- Read: `README_CN.md`
- Read: `docs/00-project-overview.md`
- Read: `docs/01-architecture.md`
- Read: `docs/03-llm-provider.md`
- Verify: all current backend and frontend tests

**Interfaces:**
- Consumes: committed Batch 11 HEAD `1c50bc7` plus the approved uncommitted design and implementation-plan documents.
- Produces: a known-good test baseline and confirmation that no real environment file needs to be read.

- [ ] **Step 1: Confirm the Git handoff and expected uncommitted scope**

Run from the repository root:

```powershell
git status --short --untracked-files=all
git log -3 --oneline
git diff --check
git tag --list --sort=version:refname
```

Expected:

- HEAD starts with `1c50bc7 test(plan1): harden chat workspace checks and docs`.
- Only the approved S7-S8 design and plan documents are untracked at this point.
- `git diff --check` has no errors.
- `v0.1.0` does not already exist.

- [ ] **Step 2: Verify worktree mode without creating a new branch**

Run:

```powershell
git rev-parse --git-dir
git rev-parse --git-common-dir
git branch --show-current
git rev-parse --show-superproject-working-tree
```

Expected: normal main checkout, no superproject. Continue in place because the user explicitly requested work in this workspace and owns manual commits.

- [ ] **Step 3: Check only whether prohibited local environment files exist**

Run without reading file contents:

```powershell
@('.env', 'backend/.env', 'frontend/.env') | ForEach-Object {
  [pscustomobject]@{ Path = $_; Exists = Test-Path -LiteralPath $_ }
}
```

Expected: record presence only. If any exists, do not open it; make every verification command set explicit safe environment variables or use mocks.

- [ ] **Step 4: Run the backend baseline**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
cd ..
```

Expected: 114 tests pass, with only the already-known Starlette TestClient/httpx deprecation warning; `pip check` reports no broken requirements. If the count changes only because later review adds tests, require all tests to pass.

- [ ] **Step 5: Run the frontend baseline**

Run:

```powershell
cd frontend
npm run typecheck
npm run test -- --run
npm run build
cd ..
```

Expected: typecheck passes, 8 files / 35 tests pass, and the production build succeeds. Treat any failure as a baseline blocker before creating release materials.

---

### Task 2: Write Truthful v0.1.0 Release Documentation

**Files:**
- Create: `CHANGELOG.md`
- Create: `docs/02-plan-1-foundation.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`

**Interfaces:**
- Consumes: implemented Plan 1 behavior documented in `docs/01-architecture.md` and `docs/03-llm-provider.md`.
- Produces: release-facing claims and limitation text that the final reviews and screenshots can validate.

This task changes documentation only. The user approved documentation work without behavior TDD; validate it with exact content and link checks instead of adding production tests.

- [ ] **Step 1: Create `CHANGELOG.md` with the exact release boundary**

Use `apply_patch` to create these sections:

```markdown
# Changelog

All notable changes to AI Agent Lab are documented in this file.

## [0.1.0] - 2026-07-13

### Added

- FastAPI and React/Vite project foundations with service-specific environment examples.
- SQLite/SQLAlchemy/Alembic persistence for conversations, messages, and successful LLM calls.
- Vendor-neutral LLM contracts, an OpenAI-compatible adapter, and a strict Model Registry.
- Non-streaming and SSE Chat with model selection, recent conversations, and refresh recovery.
- Successful-call token, estimated cost, and Provider latency persistence.
- Safe request IDs, classified HTTP/SSE errors, redacted request/model-call logs, and mocked regression coverage.
- Responsive Chat workspace states and sanitized desktop/mobile release screenshots.

### Security And Reliability

- Provider, database, validation, and unexpected failures return fixed readable responses without exposing credentials, SQL, upstream bodies, or complete messages.
- Failed and cancelled turns roll back instead of leaving partial persisted conversation state.
- Release verification uses mocks and a fresh temporary database; it does not call a real Provider or modify the user's local database.

### Known Limitations

- Live DeepSeek/OpenRouter connectivity is configuration-supported but not exercised by release verification.
- Token, estimated cost, and latency are persisted on `LLMCall` but are not displayed in the frontend.
- Provider retries/fallback, persistent failed-call audit rows, and Plan 4 Trace are not implemented.
- SSE failures after response start use a terminal `event: error` frame on an HTTP 200 stream.
- `models.json` is not yet declared as wheel/sdist package data; the supported current workflow is an editable source install.
- Older ignored local SQLite databases can predate the current foreign-key indexes and are not automatically rebuilt.
- Conversation pagination/search/rename/delete and Markdown rendering are deferred.
```

Do not add an `[Unreleased]` capability list that implies Plan 2 work already exists.

- [ ] **Step 2: Create `docs/02-plan-1-foundation.md`**

Use `apply_patch` with these exact top-level sections:

```markdown
# Plan 1 Foundation Release

## Release Boundary
## Implemented Workspace
## Architecture Map
## API Surface
## Persistence And Transactions
## Errors, Logs, And Usage Metadata
## Frontend States
## Verification Model
## Sanitized Demo
## Current Limitations
## Plan 2 Bridge
```

Required content:

- State that `v0.1.0` is local-first and primarily single-user, with SQLite as the supported primary database.
- Link to `01-architecture.md` and `03-llm-provider.md` instead of duplicating their internals.
- List the seven implemented HTTP routes from the README.
- Explain successful-turn atomicity and failure/cancellation rollback.
- State that usage/cost/latency live in `LLMCall`, not in the current UI.
- Embed `assets/plan1/chat-workspace-desktop.png` and `assets/plan1/chat-workspace-mobile.png`, each captioned `Sanitized mock demonstration; no live Provider or real credential was used.`
- Repeat every limitation from the design, including the old local SQLite drift, package-data, SSE 200 error frame, failed-call persistence, no retry/fallback, no real Provider release check, and deferred conversation/Markdown features.
- Define the Plan 2 bridge as stability checks only: Provider chat contract, Conversation/Message identity, streaming/non-streaming coexistence, request-linked logs, and reproducible startup. Do not add Tool Calling implementation.

- [ ] **Step 3: Update `README.md` release state**

Use `apply_patch` to make these factual changes:

- Replace `Current plan: Plan 1, target v0.1.0` with `Current release: v0.1.0 (Plan 1 foundation)`.
- Replace completed/next Step lines with `Completed scope: P1-M1-S1 through P1-M4-S8` and `Next scope: P2-M1-S1 Plan 1 handoff verification; no Plan 2 capability is implemented yet`.
- Remove the Batch 11 commit note.
- Add `## v0.1.0 Demo` containing the two tracked images and the sanitized-mock caption.
- Add links to `CHANGELOG.md`, `docs/02-plan-1-foundation.md`, `docs/01-architecture.md`, and `docs/03-llm-provider.md`.
- Add a compact `## Known Limitations` that points to the full foundation document and does not hide the no-live-Provider and package-data limitations.
- Preserve all verified startup and test commands.

- [ ] **Step 4: Update `README_CN.md` with matching facts**

Mirror the English release boundary in Chinese:

```text
当前版本：v0.1.0（Plan 1 工程底座）
已完成范围：P1-M1-S1～P1-M4-S8
下一范围：P2-M1-S1，仅先做 Plan 1 交接检查；尚未实现 Plan 2 能力
```

Add the same image paths, sanitized Mock explanation, document links, and limitations. Do not introduce a Chinese-only claim absent from `README.md`.

- [ ] **Step 5: Update the project overview**

In `docs/00-project-overview.md`:

- Change `Current Stage` to Plan 1 `v0.1.0` release completion.
- Replace the next S7-S8 paragraph with `P2-M1-S1` bridge verification.
- Link the foundation release document and changelog.
- Preserve the later-Plan non-goals.

- [ ] **Step 6: Validate documentation claims and links**

Run:

```powershell
rg -n 'P1-M4-S7|P1-M4-S8|target `v0.1.0`|Batch 11 commit note' README.md README_CN.md docs/00-project-overview.md
rg -n 'live Provider|real credential|LLMCall|package data|HTTP 200|retry|fallback' CHANGELOG.md docs/02-plan-1-foundation.md README.md README_CN.md
@(
  'CHANGELOG.md',
  'docs/02-plan-1-foundation.md',
  'docs/01-architecture.md',
  'docs/03-llm-provider.md'
) | ForEach-Object { if (-not (Test-Path -LiteralPath $_)) { throw "Missing release document: $_" } }
git diff --check
```

Expected: no stale next-batch text, every limitation family is present, all linked files exist, and diff check passes. Image-link existence is verified after Task 3.

---

### Task 3: Generate And Visually Verify Sanitized Screenshots

**Files:**
- Create: `docs/assets/plan1/chat-workspace-desktop.png`
- Create: `docs/assets/plan1/chat-workspace-mobile.png`
- Temporarily create then delete: `docs-local/plan1-release-browser-mock.js`
- Temporarily create then delete: Vite logs under the operating-system temporary directory

**Interfaces:**
- Consumes: the real React application and deterministic intercepted health/models/conversations/messages/stream routes.
- Produces: two durable PNG release assets and browser acceptance evidence without a backend Provider call.

- [ ] **Step 1: Verify Playwright CLI prerequisites**

Run:

```powershell
Get-Command node | Select-Object -ExpandProperty Source
Get-Command npm | Select-Object -ExpandProperty Source
Get-Command npx | Select-Object -ExpandProperty Source
npx --yes --package @playwright/cli playwright-cli --help
```

Expected: Node/npm/npx and Playwright CLI are callable. Do not add a repository dependency.

- [ ] **Step 2: Create the temporary deterministic browser script with `apply_patch`**

Create the final-asset directory, then create `docs-local/plan1-release-browser-mock.js` with `apply_patch` containing one async Playwright function:

```powershell
New-Item -ItemType Directory -Path 'docs/assets/plan1' -Force | Out-Null
```

Use these fixed non-sensitive values:

```javascript
async (page) => {
  const api = "http://localhost:8000/api/v1";
  const conversationId = "11111111-1111-4111-8111-111111111111";
  const userMessageId = "22222222-2222-4222-8222-222222222222";
  const assistantMessageId = "33333333-3333-4333-8333-333333333333";
  const llmCallId = "44444444-4444-4444-8444-444444444444";
  const userContent = "What does the Plan 1 foundation provide?";
  const assistantContent =
    "Plan 1 provides a tested FastAPI and React chat foundation with model selection, streaming responses, persisted conversations, usage metadata, safe errors, and request-linked logs.";
  let completed = false;

  const conversation = {
    id: conversationId,
    title: userContent,
    default_provider: "openai_compatible",
    default_model: "example-model",
    created_at: "2026-07-13T12:00:00",
    updated_at: "2026-07-13T12:01:00",
  };
  const messages = [
    {
      id: userMessageId,
      conversation_id: conversationId,
      role: "user",
      content: userContent,
      model: "example-model",
      provider: "openai_compatible",
      created_at: "2026-07-13T12:00:00",
    },
    {
      id: assistantMessageId,
      conversation_id: conversationId,
      role: "assistant",
      content: assistantContent,
      model: "example-model",
      provider: "openai_compatible",
      created_at: "2026-07-13T12:01:00",
    },
  ];

  await page.route(`${api}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    if (request.method() === "GET" && path.endsWith("/health")) {
      return json({ status: "ok", service: "ai-agent-lab-backend" });
    }
    if (request.method() === "GET" && path.endsWith("/models")) {
      return json([
        {
          provider: "openai_compatible",
          model: "example-model",
          display_name: "Example Model",
          supports_streaming: true,
          supports_tools: false,
          supports_json: false,
          input_price_per_1m: null,
          output_price_per_1m: null,
        },
      ]);
    }
    if (request.method() === "GET" && path.endsWith("/conversations")) {
      return json(completed ? [conversation] : []);
    }
    if (request.method() === "GET" && path.endsWith(`/${conversationId}/messages`)) {
      return json(messages);
    }
    if (request.method() === "POST" && path.endsWith("/chat/stream")) {
      const body = request.postDataJSON();
      if (
        body.provider !== "openai_compatible" ||
        body.model !== "example-model" ||
        body.content !== userContent
      ) {
        throw new Error(`Unexpected Chat request: ${JSON.stringify(body)}`);
      }
      completed = true;
      const terminal = {
        conversation_id: conversationId,
        user_message: messages[0],
        assistant_message: messages[1],
        provider: "openai_compatible",
        model: "example-model",
        usage: { input_tokens: 12, output_tokens: 24, total_tokens: 36 },
        llm_call_id: llmCallId,
      };
      const sse =
        `event: delta\ndata: ${JSON.stringify({ content: assistantContent })}\n\n` +
        `event: done\ndata: ${JSON.stringify(terminal)}\n\n`;
      return route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body: sse,
      });
    }
    return json({ error: { code: "unexpected_mock_route", message: path, request_id: "55555555-5555-4555-8555-555555555555" } }, 500);
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("http://127.0.0.1:4174", { waitUntil: "networkidle" });
  await page.getByRole("textbox", { name: "Message" }).fill(userContent);
  await page.getByRole("button", { name: "Send message" }).click();
  await page.getByText(assistantContent, { exact: true }).waitFor();
  await page.waitForURL(`**/?conversation=${conversationId}`);
  await page.reload({ waitUntil: "networkidle" });
  await page.getByText(assistantContent, { exact: true }).waitFor();
  await page.getByText("API connected", { exact: true }).waitFor();
  await page.getByText("Ready", { exact: true }).waitFor();
  await page.screenshot({
    path: "docs/assets/plan1/chat-workspace-desktop.png",
    fullPage: true,
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Conversation history" }).waitFor();
  await page.getByRole("textbox", { name: "Message" }).waitFor();
  await page.getByText(assistantContent, { exact: true }).waitFor();
  await page.screenshot({
    path: "docs/assets/plan1/chat-workspace-mobile.png",
    fullPage: true,
  });
}
```

The exact async-function wrapper is required by `playwright-cli run-code --filename`.

- [ ] **Step 3: Start Vite without loading a repository `.env`**

First confirm `frontend/.env` presence without reading it. If absent, start Vite:

```powershell
$viteOut = Join-Path $env:TEMP 'ai-agent-lab-plan1-vite.out.log'
$viteErr = Join-Path $env:TEMP 'ai-agent-lab-plan1-vite.err.log'
$vite = Start-Process -FilePath 'npm.cmd' -ArgumentList @(
  'run', 'dev', '--', '--host', '127.0.0.1', '--port', '4174'
) -WorkingDirectory (Resolve-Path 'frontend') -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $viteOut -RedirectStandardError $viteErr
```

Poll `http://127.0.0.1:4174` for at most 30 seconds. Do not open or echo environment files.

- [ ] **Step 4: Run the isolated browser acceptance and create both PNG files**

Run from the repository root:

```powershell
npx --yes --package @playwright/cli playwright-cli --session plan1-release open about:blank
npx --yes --package @playwright/cli playwright-cli --session plan1-release run-code --filename docs-local/plan1-release-browser-mock.js
npx --yes --package @playwright/cli playwright-cli --session plan1-release console error
npx --yes --package @playwright/cli playwright-cli --session plan1-release network
npx --yes --package @playwright/cli playwright-cli --session plan1-release close
```

Expected:

- no unexpected console errors;
- intercepted requests include health, models, conversations, stream, refresh conversations, and restored messages;
- the URL contains the fixed sanitized conversation UUID;
- both screenshot files exist.

- [ ] **Step 5: Verify image dimensions and inspect both screenshots visually**

Use the local image-inspection tool on both PNG files. Also run a read-only dimension check with the workspace image library or PowerShell-compatible image metadata.

Acceptance:

- desktop is 1440x900 or a taller full-page equivalent at 1440 CSS pixels wide;
- mobile is 390x844 or a taller full-page equivalent at 390 CSS pixels wide;
- text is legible and not clipped;
- desktop shows model, recent conversation, healthy API, user message, and assistant answer;
- mobile shows the responsive header/history control, model identity, completed answer, and composer;
- no path, username, credential, real model response, or browser chrome is visible.

- [ ] **Step 6: Clean temporary browser and Vite state**

Stop the captured Vite process if it still runs, close the Playwright session, and use `apply_patch` to delete `docs-local/plan1-release-browser-mock.js`. Remove only the two known temporary log paths with native PowerShell `Remove-Item -LiteralPath` after verifying each resolves under `$env:TEMP`.

Run:

```powershell
Get-NetTCPConnection -LocalPort 4174 -State Listen -ErrorAction SilentlyContinue
git status --short --untracked-files=all
```

Expected: no listener on 4174; only intended tracked release assets and documents appear.

---

### Task 4: Perform The Codex Final Review

**Files:**
- Create: `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md`
- Read: all Plan 1 production, test, migration, documentation, and release-candidate files

**Interfaces:**
- Consumes: one complete release candidate including screenshots and changelog.
- Produces: evidence-backed Codex findings and an explicit pending gate for the user's Fable 5 result.

- [ ] **Step 1: Run the Codex final self-review**

Review the entire candidate, not only the current diff. At minimum inspect:

```powershell
git diff --stat
git diff -- . ':(exclude)docs/assets/plan1/*.png'
git log --oneline --reverse
rg --files backend/app backend/tests frontend/src docs README.md README_CN.md CHANGELOG.md
```

Review these exact categories:

- Plan boundary and release-claim truthfulness;
- thin route/service/provider ownership;
- transaction, rollback, migration, and SQLite behavior;
- Provider classification and upstream-body/credential safety;
- request ID continuity and log redaction;
- non-streaming/streaming/cancellation correctness;
- frontend initialization, stale response, error, Stop, and recovery states;
- automated test coverage and mocked browser evidence;
- Plan 2 bridge stability without implementing Plan 2.

Record concrete file/line evidence for every issue. Do not call a stylistic preference a must-fix.

- [ ] **Step 2: Classify Codex findings**

Use exactly four classes:

```text
Must fix
Fix later
Record as limitation
Not applicable
```

Rules:

- Must fix only for acceptance failure, security leak, data integrity defect, repeatable behavior bug, or unstable Plan 2 foundation.
- Fix later must identify the scheduled Plan or bridge check.
- Record as limitation must already be visible in release docs or trigger a documentation patch.
- Not applicable must cite the contradicting requirement or implementation evidence.

- [ ] **Step 3: Create the final review record with real results**

Use `apply_patch` to create `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md` with these headings:

```markdown
# Plan 1 v0.1.0 Final Review

## Candidate And Scope
## Codex Self-Review
## Manual Fable 5 Review
## Finding Classification
## Fixes And Re-Verification
## Acceptance Evidence
## Residual Limitations
## Release Commit And Tag Handoff
```

Requirements:

- Fill the Codex section only with actual results.
- Set Manual Fable 5 Review to `Pending user-provided result` until the user responds.
- Never put invented Fable output into the record.
- State that Claude Code review was cancelled at the user's direction and is not release evidence.
- Do not include raw model chain-of-thought, secrets, complete logs, or large copied diffs.
- Include finding classifications in a table with source, severity, file, decision, and reason.

- [ ] **Step 4: Stop if any must-fix finding exists**

Do not continue to Fable handoff with an unresolved must-fix Codex finding. Execute Task 6 for each verified defect, then repeat the affected review section.

---

### Task 5: Cancelled Manual Fable 5 Review Gate

> **Superseded:** The user cancelled this task because Fable 5 quota was not
> available and explicitly assigned final review to Codex. The original steps
> remain below only as planning history and are not release gates.

**Files:**
- Modify after user response: `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md`

**Interfaces:**
- Consumes: candidate with no unresolved Codex must-fix finding plus current automated/browser evidence.
- Produces: the user's actual Fable 5 findings or explicit no-finding conclusion.

- [ ] **Step 1: Provide a concise Fable 5 review package to the user**

Report:

- exact Step scope `P1-M4-S7～S8`;
- current HEAD and uncommitted file list;
- release design and implementation-plan links;
- Codex conclusion;
- fresh backend/frontend/browser verification counts;
- known limitations;
- security prohibitions covering real `.env`, secrets, credentials, browser profiles, credential stores, ignored local databases, and real Provider calls;
- a request for Fable findings with severity, file/line, evidence, and recommendation.

- [ ] **Step 2: Pause before release completion**

Do not mark S8 complete, ask for the manual release commit, or create the tag while the Fable result is pending.

- [ ] **Step 3: Record the user's actual Fable result**

After the user supplies it, update the Manual Fable 5 Review and Finding Classification sections using `apply_patch`. If the user reports no findings, record that exact conclusion and the date; do not embellish it.

- [ ] **Step 4: Verify every actionable Fable finding before changing code**

Use the receiving-code-review workflow. Reproduce behavior findings, compare claims against requirements and current code, and classify them. Route verified must-fix defects through Task 6.

---

### Task 6: Fix Verified Release-Blocking Findings With TDD

**Files:**
- Test: exact affected existing or new test file identified in the review record
- Modify: smallest affected production file identified in the review record
- Modify: `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md`
- Modify when user-visible: relevant README, changelog, or formal documentation file

**Interfaces:**
- Consumes: one reproduced and classified must-fix finding.
- Produces: a regression test that failed for the defect, minimal correction, passing focused/full checks, and recorded evidence.

Skip this task only when all three review sources have no verified must-fix finding.

- [ ] **Step 1: Diagnose before editing**

Record in the review document:

```text
Observed behavior
Expected Plan 1 behavior
Root cause
Smallest affected boundary
Regression test path and test name
```

- [ ] **Step 2: Write one minimal regression test**

Add the test in the closest existing suite. Do not add a production workaround, test-only method, or broad refactor.

- [ ] **Step 3: Run the focused test and observe RED**

Before editing production code, add the concrete focused command to the finding's `Root cause` entry in the review record. The command must name the actual newly added test file and test case. Run that recorded command verbatim.

Expected: the assertion fails for the reproduced defect, not for syntax, fixture, or environment setup.

- [ ] **Step 4: Apply the smallest production fix**

Use `apply_patch`. Stay within Plan 1 and the affected module boundary.

- [ ] **Step 5: Run focused GREEN and adjacent regression tests**

Run the focused command again, then the affected module suite. Expected: all pass with no new error/warning beyond the known TestClient deprecation warning.

- [ ] **Step 6: Update the review classification and relevant documentation**

Record the exact RED evidence, correction, GREEN command, and result. If a release statement changed, update all English/Chinese locations consistently.

- [ ] **Step 7: Repeat review for the corrected area**

Codex re-reviews the patch. If the finding came from Fable, prepare the corrected evidence for the user to re-check manually in Cursor.

---

### Task 7: Run Full Acceptance And Finalize Plan 1 Records

**Files:**
- Modify: `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`
- Modify if review changed facts: `CHANGELOG.md`, `README.md`, `README_CN.md`, `docs/00-project-overview.md`, `docs/02-plan-1-foundation.md`

**Interfaces:**
- Consumes: all classified reviews and resolved must-fix findings.
- Produces: final reproducible evidence and release-ready documentation.

- [ ] **Step 1: Run fresh backend verification**

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
cd ..
```

Record exact pass counts, duration, and known warning.

- [ ] **Step 2: Verify a fresh temporary SQLite migration**

Create a uniquely named database under `$env:TEMP`, set `DATABASE_URL` only for the three commands, and never point Alembic at the user database:

```powershell
$dbPath = Join-Path $env:TEMP ("ai-agent-lab-v010-" + [guid]::NewGuid().ToString() + '.db')
$env:DATABASE_URL = 'sqlite:///' + ($dbPath -replace '\\', '/')
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
cd ..
Remove-Item Env:DATABASE_URL
if (-not ((Resolve-Path -LiteralPath $dbPath).Path).StartsWith((Resolve-Path $env:TEMP).Path)) { throw 'Unsafe temporary database path' }
Remove-Item -LiteralPath $dbPath
```

Expected: head `20260712_0001`, no new upgrade operations, and only the verified temp file is removed.

- [ ] **Step 3: Run Uvicorn/API smoke on a temporary database**

Start Uvicorn on `127.0.0.1:8012` with an explicit temporary `DATABASE_URL` and no Provider key:

```powershell
$apiDb = Join-Path $env:TEMP ("ai-agent-lab-v010-api-" + [guid]::NewGuid().ToString() + '.db')
$uvicornOut = Join-Path $env:TEMP 'ai-agent-lab-v010-uvicorn.out.log'
$uvicornErr = Join-Path $env:TEMP 'ai-agent-lab-v010-uvicorn.err.log'
$env:DATABASE_URL = 'sqlite:///' + ($apiDb -replace '\\', '/')
$uvicorn = Start-Process -FilePath (Resolve-Path '.venv/Scripts/python.exe') `
  -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8012') `
  -WorkingDirectory (Resolve-Path 'backend') -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $uvicornOut -RedirectStandardError $uvicornErr

try {
  Add-Type -AssemblyName System.Net.Http
  $client = [System.Net.Http.HttpClient]::new()
  $base = 'http://127.0.0.1:8012'
  $ready = $false
  foreach ($attempt in 1..60) {
    try {
      $probe = $client.GetAsync("$base/api/v1/health").Result
      if ([int]$probe.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  if (-not $ready) { throw 'Uvicorn did not become ready on port 8012' }

  $health = $client.GetAsync("$base/api/v1/health").Result
  $healthBody = $health.Content.ReadAsStringAsync().Result | ConvertFrom-Json
  $healthRequestId = ($health.Headers.GetValues('X-Request-ID') | Select-Object -First 1)
  $parsedHealthId = [guid]::Empty
  if ([int]$health.StatusCode -ne 200 -or $healthBody.status -ne 'ok' -or
      $healthBody.service -ne 'ai-agent-lab-backend' -or
      -not [guid]::TryParse($healthRequestId, [ref]$parsedHealthId)) {
    throw 'Health smoke failed'
  }

  $openapi = ($client.GetStringAsync("$base/openapi.json").Result | ConvertFrom-Json)
  $requiredPaths = @(
    '/api/v1/health',
    '/api/v1/models',
    '/api/v1/conversations',
    '/api/v1/conversations/{conversation_id}/messages',
    '/api/v1/chat/completions',
    '/api/v1/chat/stream'
  )
  $availablePaths = @($openapi.paths.psobject.Properties.Name)
  $missingPaths = @($requiredPaths | Where-Object { $_ -notin $availablePaths })
  if ($missingPaths.Count -ne 0) { throw "Missing OpenAPI paths: $($missingPaths -join ', ')" }

  $validation = $client.GetAsync("$base/api/v1/conversations/not-a-uuid/messages").Result
  $validationBody = $validation.Content.ReadAsStringAsync().Result | ConvertFrom-Json
  $validationHeaderId = ($validation.Headers.GetValues('X-Request-ID') | Select-Object -First 1)
  if ([int]$validation.StatusCode -ne 422 -or
      $validationBody.error.code -ne 'validation_error' -or
      $validationBody.error.request_id -ne $validationHeaderId) {
    throw 'Validation error smoke failed'
  }

  $methodResponse = $client.PostAsync("$base/api/v1/health", $null).Result
  $methodBody = $methodResponse.Content.ReadAsStringAsync().Result | ConvertFrom-Json
  $methodHeaderId = ($methodResponse.Headers.GetValues('X-Request-ID') | Select-Object -First 1)
  if ([int]$methodResponse.StatusCode -ne 405 -or
      $methodBody.error.code -ne 'http_error' -or
      $methodBody.error.request_id -ne $methodHeaderId) {
    throw 'Method error smoke failed'
  }
} finally {
  if ($null -ne $client) { $client.Dispose() }
  if (-not $uvicorn.HasExited) { Stop-Process -Id $uvicorn.Id -Force }
  Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
  $tempRoot = (Resolve-Path $env:TEMP).Path
  foreach ($path in @($apiDb, $uvicornOut, $uvicornErr)) {
    if (Test-Path -LiteralPath $path) {
      $resolved = (Resolve-Path -LiteralPath $path).Path
      if (-not $resolved.StartsWith($tempRoot)) { throw "Unsafe cleanup path: $resolved" }
      Remove-Item -LiteralPath $resolved
    }
  }
}

if (Get-NetTCPConnection -LocalPort 8012 -State Listen -ErrorAction SilentlyContinue) {
  throw 'Port 8012 still has a listener after cleanup'
}
```

Verify:

- `GET /api/v1/health` returns 200 and the expected service;
- `X-Request-ID` is a UUID;
- OpenAPI contains health, models, conversations, conversation messages, non-stream Chat, and stream Chat routes;
- malformed conversation UUID returns 422 `validation_error` with body/header request IDs matching;
- unsupported method returns 405 `http_error` with safe text;
- no listener remains after cleanup.

Do not call either Chat route against a real Provider during this smoke.

- [ ] **Step 4: Run fresh frontend verification**

```powershell
cd frontend
npm run typecheck
npm run test -- --run
npm run build
cd ..
```

Record exact file/test counts and the successful Vite build summary.

- [ ] **Step 5: Re-run the mocked browser acceptance after any UI change**

If Task 6 changed frontend behavior or CSS, repeat Task 3 and visually inspect both screenshots again. If no UI file changed, verify the final PNG hashes, dimensions, and README links without regenerating them.

- [ ] **Step 6: Validate docs, secrets, and artifacts**

Run:

```powershell
git diff --check
git status --short --untracked-files=all
git diff --stat
git diff --numstat
rg -n 'P1-M4-S7|P1-M4-S8|target `v0.1.0`|Pending user-provided result' README.md README_CN.md docs CHANGELOG.md docs-plan/01-PLAN1
git diff -- . ':(exclude)docs/assets/plan1/*.png' | rg -n -i 'api[_-]?key\s*[:=]\s*[^\s]*[A-Za-z0-9]{12,}|authorization:\s*bearer\s+[A-Za-z0-9._-]{12,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
rg --files | rg '\.(pem|key|p12|pfx)$|(^|[\\/])\.env$|playwright-report|test-results|\.playwright-cli|\.log$|\.db$|\.sqlite3?$'
```

Interpretation:

- secret scan should have no release-diff hit;
- any fake credential already present in tracked tests must be identified as an existing clearly fake test value, not silently ignored;
- artifact scan must not show real `.env`, temp DBs, browser profiles, or logs;
- `Pending user-provided result` must be absent only after Task 5 is complete.

- [ ] **Step 7: Finalize Plan 1 execution records**

After the expanded Codex result is recorded and all checks pass, update the execution table:

- Batch 12 status: `已完成`.
- S7 and S8 completion note: release materials, expanded Codex review, fixes, full verification, and annotated tag handoff.
- Final acceptance checklist: every implemented evidence item `done`; the tag row notes that the annotated tag is created immediately after the user-owned release commit.
- Plan 2 bridge checklist: mark only evidence-backed stability checks done; do not claim Tool Calling exists.
- Next scope: `P2-M1-S1` only.

Update the final review record with actual command results and no pending placeholders.

- [ ] **Step 8: Final diff self-review**

Confirm:

- every changed file belongs to S7-S8 or a recorded must-fix repair;
- no Plan 2 capability or future directory was added;
- README, changelog, foundation doc, review record, screenshots, project overview, and execution table agree;
- screenshots are the only intended binary files;
- no tag exists yet while changes are uncommitted.

---

### Task 8: Manual Release Commit Handoff And Annotated Tag

**Files:**
- No file changes after the verified release candidate is handed off, unless the user's commit check reveals a mismatch.

**Interfaces:**
- Consumes: complete verified working tree and the user's manual release commit.
- Produces: annotated `v0.1.0` tag pointing exactly at that commit.

- [ ] **Step 1: Hand off the verified release candidate**

Provide:

- change summary;
- exact backend/frontend/browser/migration results;
- expanded Codex final-review conclusion and external-review decision;
- residual limitations;
- `git status --short` output;
- suggested manual commit message:

```text
chore: release v0.1.0 foundation chat
```

Do not stage or commit.

- [ ] **Step 2: Wait for the user to confirm the manual commit**

This is a hard gate. Do not create `v0.1.0` while the release files are uncommitted.

- [ ] **Step 3: Verify the release commit before tagging**

After user confirmation, run:

```powershell
git status --short --untracked-files=all
git log -3 --oneline
git diff --check
git tag --list v0.1.0
```

Expected: clean worktree, new release commit at HEAD, diff check clean, and no existing `v0.1.0` tag.

- [ ] **Step 4: Create the annotated tag**

Run:

```powershell
git tag -a v0.1.0 -m 'AI Agent Lab v0.1.0'
```

This command is authorized by S8 only after the preceding gate. Do not push it.

- [ ] **Step 5: Verify tag identity and annotation**

Run:

```powershell
$head = git rev-parse HEAD
$tagCommit = git rev-parse 'v0.1.0^{}'
if ($head -ne $tagCommit) { throw "v0.1.0 points to $tagCommit, expected $head" }
git tag -n99 v0.1.0
git show --no-patch --decorate --format=fuller v0.1.0
git status --short --untracked-files=all
```

Expected: tag annotation is `AI Agent Lab v0.1.0`, dereferenced tag commit equals HEAD, and worktree remains clean.

- [ ] **Step 6: Report Plan 1 completion**

Report S7-S8 and Plan 1 complete only now. State that the tag is local unless the user separately asks to push it. Recommend the next batch as `P2-M1-S1` only, beginning with the documented Plan 1 handoff verification.

---

## Plan Self-Review Checklist

- [x] Every approved design requirement maps to a task.
- [x] Both screenshots use fixed mocked data and no real Provider.
- [x] Expanded Codex final review is agent-owned; cancelled external review paths are not claimed as evidence.
- [x] The user-owned release commit remains a hard gate before the annotated tag.
- [x] Unknown review defects cannot be patched without diagnosis, a recorded exact test path, and observed RED.
- [x] Full backend, frontend, migration, Uvicorn, browser, docs, secret, artifact, and Git verification is specified.
- [x] No task stages, commits, pushes, or implements Plan 2.
- [x] The annotated tag can only point to the user-created verified release commit.
