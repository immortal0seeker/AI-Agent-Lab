# Plan 1 M4 Testing, UI States, And Documentation Design

**Date:** 2026-07-13

**Scope:** `P1-M4-S4` through `P1-M4-S6`

## Goal

Finish the second Milestone 4 batch by closing focused backend test gaps,
making the frontend workspace initialization states explicit and recoverable,
and bringing the startup and configuration documentation in line with the
implemented Plan 1 system.

## Constraints

- Work only on `P1-M4-S4` through `P1-M4-S6`.
- Do not add Tool Calling, RAG, Memory, Trace, Evaluation, MCP, Voice, Vision,
  Desktop, or other later-plan capabilities.
- Do not prepare screenshots, `CHANGELOG.md`, a release tag, or final-review
  materials; those belong to `P1-M4-S7` and `P1-M4-S8`.
- Do not add dependencies or a database migration.
- Do not read real `.env` files or call a real or paid Provider.
- Keep backend routes thin and preserve the existing service and Provider
  boundaries.
- The user creates the Git commit manually.

## Chosen Approach

Use audit-driven, minimal hardening. Existing coverage is retained and only
meaningful contract gaps are added. Backend production code changes only when
a new test demonstrates a real defect. The frontend gains one focused
presentation component for workspace initialization states rather than a
broader store or page refactor.

Broader error-matrix duplication and a full frontend state-machine refactor
were rejected because they would enlarge the diff without improving the
acceptance boundary of this batch.

## Backend Test Design

The new tests cover one important contract at each relevant boundary:

- Health: a successful response includes a server-generated UUID in
  `X-Request-ID`.
- Provider: streaming timeout and transport failures use the established error
  taxonomy and never expose low-level diagnostics or test credentials.
- Chat: representative classified Provider failures map to the correct HTTP or
  SSE error envelope and keep the transactional rollback guarantee.
- Conversation: malformed conversation IDs return the unified validation
  envelope, and default conversation creation remains stable.
- Error handling: an unexpected exception produces a safe `internal_error`;
  method-not-allowed responses use the unified envelope; neither response nor
  captured logs contain the sensitive exception text.

These tests extend, rather than duplicate, the Batch 10 coverage for usage,
cost, latency, request-linked logging, Provider error classification, database
errors, and ordinary Chat rollback.

## Frontend State Design

Create a small `WorkspaceStatusPanel` component with two variants:

- `loading`: show a progress indicator and an accessible status label while
  Registry models and conversation summaries are loading.
- `error`: show the safe initialization error and an accessible `Retry`
  button.

`ChatPage` renders these states before the normal message workspace:

1. While `workspaceStatus` is `loading`, show the workspace loading panel and
   do not also show the empty-chat prompt.
2. When `workspaceStatus` is `error`, show the error panel and Retry action.
   Suppress the existing top error banner for this same initialization error
   so the message is not duplicated.
3. When `workspaceStatus` is `ready`, retain the existing conversation-loading,
   empty, streaming, completed, stopped, and Chat-error paths.

Retry calls the existing `initialize()` action with the currently valid
conversation ID from the URL. The store already permits initialization from
the `error` state, so no new store state or retry policy is introduced. The
composer and model selector remain disabled until initialization succeeds.

Transient Chat, refresh, and conversation-loading errors continue to use the
existing banner after the workspace is ready.

## Frontend Test Design

- Render `WorkspaceStatusPanel` with React server rendering to verify the
  loading status and the error/Retry controls without adding a DOM testing
  dependency.
- Add a store test that fails initialization once, retries it, and verifies the
  successful models, conversations, selected model, cleared error, and ready
  status.
- Use a browser mock smoke check to verify that a failed initial models or
  conversations request shows Retry and that clicking it restores the normal
  empty, model-selection, conversation, and composer state.

The new component is introduced test-first. Existing behavior-only coverage
may pass immediately because it documents an already implemented contract;
production changes still require a failing test first.

## Documentation And Configuration Design

Update:

- `README.md` and `README_CN.md`
- root, backend, and frontend `.env.example` files
- `docs/00-project-overview.md`
- `docs/01-architecture.md`
- `docs/03-llm-provider.md`
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

The documentation will:

- mark completion through `P1-M4-S6` and point to `P1-M4-S7` through
  `P1-M4-S8` as the next batch;
- give a clean-environment startup sequence for Python 3.11, editable backend
  installation, Alembic migration, Uvicorn, npm installation, and Vite;
- explain that backend configuration is read from `backend/.env` when commands
  run from the backend directory and Vite configuration is read from
  `frontend/.env`;
- state that the root `.env.example` is a workspace-level reference and is not
  automatically consumed by either current application;
- document the frontend loading, empty, initialization-error, Retry, Chat-error,
  streaming, stopped, and success states;
- keep all example credentials empty and state that tests use mocks only.

No release claim, screenshot inventory, changelog entry, or tag is added in
this batch.

## Verification

Completion requires fresh evidence from:

- backend full pytest suite;
- `pip check`;
- frontend typecheck, full Vitest suite, and production build;
- a new temporary SQLite database upgraded to Alembic head and checked for
  migration drift, without touching the user's local database;
- Uvicorn smoke checks for health, OpenAPI, validation, and safe errors;
- Vite plus browser mocks for loading, initialization failure, Retry recovery,
  empty state, and normal Chat readiness;
- `git diff --check`, secret-pattern scanning, generated-artifact scanning, and
  port cleanup checks.

## Acceptance Criteria

- The backend coverage explicitly includes health, Provider, Chat,
  conversation, and unified-error contracts.
- Initialization loading is distinct from the ready empty state.
- Initialization failure has a working Retry path and does not duplicate its
  error message.
- Existing ready-state Chat behavior remains unchanged.
- A new reader can identify which environment example to copy, migrate a fresh
  SQLite database, start both services, and run the documented checks.
- No real secret, external Provider call, later-plan capability, release
  artifact, new dependency, or migration is introduced.
