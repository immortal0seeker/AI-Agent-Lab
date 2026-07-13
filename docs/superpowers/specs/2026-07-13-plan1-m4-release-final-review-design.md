# Plan 1 v0.1.0 Release And Final Review Design

**Date:** 2026-07-13  
**Scope:** `P1-M4-S7` through `P1-M4-S8` only  
**Status:** Implemented and fully verified; manual release commit and annotated
tag pending

**Execution amendment:** The approved design originally used a user-owned
Cursor/Fable 5 review gate. On 2026-07-13 the user cancelled that path because
the available quota was insufficient and assigned the complete final review to
Codex. References below are updated to the resulting Codex-only final review;
Claude Code also remains cancelled and is not release evidence.

## 1. Goal

Prepare sanitized Plan 1 release materials, review the complete `v0.1.0`
candidate, fix release-blocking findings, run the full Plan 1 acceptance suite,
and create an annotated `v0.1.0` tag after the user manually creates the
verified release commit.

This batch closes Plan 1. It must not introduce Tool Calling, RAG, Memory,
Trace persistence, Provider retry policy, MCP, Voice, Vision, Desktop, or any
other later-Plan capability.

## 2. Release Strategy

Use a release-materials-first workflow:

1. Prepare the changelog, Plan 1 summary, current limitations, and sanitized
   screenshots.
2. Perform an expanded Codex review of the complete release candidate.
3. Classify every finding and fix only verified release-blocking defects in
   this batch through TDD.
4. Re-run the complete acceptance suite after all fixes.
5. Hand the verified working tree to the user for the manual release commit.
6. Create and verify the annotated tag only after that commit exists.

This order keeps screenshots, documentation, reviewed code, and the tagged
release commit aligned.

## 3. Release Artifacts

### 3.1 New Files

- `CHANGELOG.md` records `v0.1.0` using a compact Keep a Changelog-style
  structure. It separates implemented features, security/robustness work, and
  known limitations.
- `docs/02-plan-1-foundation.md` is the durable Plan 1 release summary. It
  describes the implemented boundary, architecture entry points, acceptance
  evidence, current limitations, and the bridge into Plan 2.
- `docs/assets/plan1/chat-workspace-desktop.png` is a sanitized desktop Chat
  workspace screenshot generated against deterministic mocked API and SSE
  responses.
- `docs/assets/plan1/chat-workspace-mobile.png` is the corresponding sanitized
  mobile viewport screenshot.
- `docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md` records the Codex
  review, the user-provided manual Fable 5 review, finding classifications,
  fixes, verification evidence, remaining limitations, and tag handoff.

### 3.2 Updated Files

- `README.md` and `README_CN.md` become Plan 1 release-facing entry points,
  embed the sanitized screenshots, link the changelog and release summary, and
  state the exact `v0.1.0` boundary.
- `docs/00-project-overview.md` records the Plan 1 release boundary and makes
  the Plan 2 handoff the next scope.
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md` records Batch 12 acceptance
  and the release/tag handoff without adding later-Plan implementation work.

Production code is not changed merely to produce release materials. If final
review identifies a blocking defect, its smallest relevant production and test
files may be changed through a failing-test-first cycle.

## 4. Screenshot Design

The two tracked PNG files use deterministic mock data and browser request
interception. They must not use a real Provider, API key, local conversation
database, or unsanitized local information.

The desktop screenshot shows:

- the engineering-workspace layout;
- a selected example Registry model;
- recent conversation navigation;
- one user message and one completed streamed assistant response;
- healthy/ready workspace state.

The mobile screenshot shows:

- the responsive Chat layout;
- accessible history navigation;
- the same sanitized completed conversation;
- a usable composer and visible model identity.

The documentation labels both images as sanitized mock demonstrations. No
temporary Playwright profiles, traces, scripts, logs, or extra screenshots are
retained.

## 5. Release Truthfulness

The `v0.1.0` release may claim only verified Plan 1 capabilities:

- FastAPI and React/Vite foundations;
- SQLite and Alembic conversation persistence;
- a vendor-neutral LLM Provider contract, OpenAI-compatible adapter, and Model
  Registry;
- non-streaming and SSE Chat;
- model selection, recent conversations, and refresh recovery;
- successful-call token, estimated cost, and latency persistence;
- unified safe errors, request IDs, and redacted diagnostic logs;
- automated backend/frontend checks and mocked desktop/mobile browser
  acceptance.

The release must explicitly avoid these overclaims:

- Mock verification does not prove live DeepSeek or OpenRouter connectivity.
- Token, cost, and latency are persisted on `LLMCall`; they are not displayed
  in the current frontend.
- The release does not include automatic Provider retry/fallback, persistent
  Trace, Tool Calling, RAG, Memory, or later-Plan features.
- Screenshots do not represent a paid or live model invocation.

## 6. Known Limitations

The release summary and changelog record, at minimum:

- an older ignored local SQLite database can predate the foreign-key index
  migration alignment; verification uses a new temporary database and never
  deletes or rebuilds the user's local database;
- `models.json` works from the editable source tree but is not yet declared as
  setuptools wheel/sdist package data;
- an SSE error after streaming starts remains an HTTP 200 response with a
  terminal `event: error` frame;
- failed or cancelled model calls roll back the turn and do not persist a
  failed `LLMCall` audit row;
- Provider retries and fallback policy are not implemented;
- conversation pagination, rename, delete, search, and Markdown rendering are
  deferred;
- real Provider connectivity is not part of release verification.

## 7. Final Review

### 7.1 Codex Review

Codex reviews the full release candidate for:

- Step and Plan scope compliance;
- route/service/provider boundaries;
- transaction and migration consistency;
- Provider/error/logging secret safety;
- streaming and cancellation correctness;
- frontend asynchronous-state and stale-response protection;
- test adequacy and release-document truthfulness;
- Plan 2 bridge stability.

### 7.2 External Review Decision

No external review result is claimed. The user cancelled the attempted Claude
Code review after it did not return a usable result, then cancelled the planned
Cursor/Fable 5 review when its quota was insufficient. The user explicitly
assigned the final review, corrections, and verification to Codex while
retaining ownership of the release commit.

### 7.3 Finding Classification

Every finding is recorded as one of:

- **Must fix:** blocks Plan 1 acceptance, security, data integrity, or Plan 2
  foundation stability; fix now with TDD where behavior changes.
- **Fix later:** valid improvement assigned to a later scoped batch or Plan.
- **Record as limitation:** accepted `v0.1.0` boundary that must remain visible.
- **Not applicable:** unsupported by evidence, outside scope, or based on an
  incorrect assumption; include the reason.

Review suggestions are verified against the code and requirements before any
change is made.

## 8. Verification And Acceptance

### 8.1 Backend

- Run the complete pytest suite.
- Run `pip check`.
- Upgrade a fresh temporary SQLite database to Alembic head, check current
  heads, and run `alembic check`.
- Start Uvicorn and verify health, required OpenAPI routes, request IDs, safe
  validation/method errors, and cleanup.
- Use mock Providers only for Chat/stream persistence and error coverage.

### 8.2 Frontend

- Run TypeScript checking.
- Run the complete frontend test suite.
- Run a production build.
- Run mocked browser acceptance for initialization loading/error/Retry, model
  selection, streaming completion, conversation URL recovery, and responsive
  desktop/mobile layout.
- Generate the two release screenshots from the sanitized completed-flow
  state.

### 8.3 Release Safety

- Confirm root, backend, and frontend real `.env` files are not read.
- Scan tracked changes for credential-like material and prohibited artifacts.
- Run `git diff --check`.
- Confirm temporary databases, browser profiles, logs, scripts, and service
  listeners are removed.
- Confirm the diff contains only S7-S8 release work plus verified blocking
  fixes, if any.

## 9. Git And Tag Handoff

The user remains the commit owner. Codex does not stage or commit the release
batch.

After all review and acceptance checks pass:

1. Codex reports the verified diff and suggested release commit message.
2. The user manually creates the release commit.
3. Codex verifies the clean working tree and release commit.
4. Codex creates the annotated tag:

   ```text
   v0.1.0
   AI Agent Lab v0.1.0
   ```

5. Codex verifies that `v0.1.0` resolves to the manual release commit.

The tag is not created against an earlier commit and is not created while
release changes remain uncommitted.

## 10. Completion Criteria

`P1-M4-S7` and `P1-M4-S8` are complete only when:

- release materials are tracked, sanitized, and internally consistent;
- both screenshots represent the approved mocked flows;
- the expanded Codex final review is recorded and all findings are classified;
- every must-fix issue is resolved and re-verified;
- all backend, frontend, browser, migration, documentation, and safety checks
  pass;
- the user-created release commit contains the verified candidate;
- the annotated `v0.1.0` tag exists and points to that commit;
- no later-Plan capability was implemented.
