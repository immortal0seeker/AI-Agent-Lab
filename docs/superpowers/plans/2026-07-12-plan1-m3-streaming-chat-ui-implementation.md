# Plan 1 M3 Streaming Chat And Basic UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `P1-M3-S4` through `P1-M3-S6` with atomic SSE Chat streaming, a tested frontend stream/store layer, and a usable responsive Chat workspace.

**Architecture:** `ChatService` yields protocol-neutral stream events and commits only after a complete Provider stream. The FastAPI SSE adapter owns per-stream Session lifecycle and framing, while the React frontend consumes events through a typed API wrapper and Zustand store.

**Tech Stack:** Python 3.11, FastAPI StreamingResponse, SQLAlchemy 2, pytest 9, React 19, TypeScript 5.9, Zustand, Lucide React, Vitest, Playwright.

## Global Constraints

- Work only on `P1-M3-S4` through `P1-M3-S6`.
- Do not add conversation history/list APIs, dynamic model selection, Markdown dependencies, token/cost/latency persistence, detailed M4 errors/logging, Tool Calling, RAG, Memory, MCP, Voice, Vision, or Desktop behavior.
- Persist streaming turns only after successful completion.
- Roll back on Provider failure or client cancellation.
- Use mocks and browser interception; do not read real `.env` files or call paid APIs.
- M3 uses Codex self-review only; the next Fable 5 review is after M4.
- The user creates the Git commit manually.

---

### Task 1: Backend Streaming Service And SSE Endpoint

**Files:**
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/v1/chat.py`
- Modify: `backend/tests/test_chat_service.py`
- Modify: `backend/tests/test_chat_api.py`

**Interfaces:**
- Produces: `ChatStreamDelta`, `ChatStreamCompleted`, `ChatService.stream_complete()`, `ChatStreamDeltaResponse`, `ChatStreamErrorResponse`, and `POST /api/v1/chat/stream`.

- [x] **Step 1: Write failing streaming service tests**

Assert chunk ordering, accumulated assistant content, successful commit, final usage/model, Provider failure rollback, empty-stream failure, and `aclose()` cancellation rollback.

- [x] **Step 2: Verify service RED**

Run focused Chat Service streaming tests and confirm missing `stream_complete()` behavior.

- [x] **Step 3: Implement minimal protocol-neutral streaming**

Reuse model/provider/history preparation, yield delta dataclasses, accumulate completion fields, persist once, commit before completed event, and roll back in unsuccessful generator finalization.

- [x] **Step 4: Verify service GREEN**

Run all Chat Service tests.

- [x] **Step 5: Write failing SSE API tests**

Assert OpenAPI route, `text/event-stream`, delta/done JSON frames, successful persistence, error terminal event, and failed-stream rollback.

- [x] **Step 6: Verify API RED**

Run focused API streaming tests and confirm route absence.

- [x] **Step 7: Implement SSE adapter**

Inject Session factory/Registry/providers, create and close Session inside the generator, encode compact SSE frames, and convert service/Provider failures to safe error events.

- [x] **Step 8: Verify backend GREEN**

Run focused tests and complete backend pytest.

---

### Task 2: Frontend Streaming API And Zustand Store

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/.env.example`
- Modify: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/api/chat.ts`
- Create: `frontend/src/api/chat.test.ts`
- Create: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/stores/chatStore.test.ts`

**Interfaces:**
- Produces: typed Chat/SSE models, `streamChat()`, `createChatStore()`, and `useChatStore`.

- [x] **Step 1: Install approved dependencies**

Run `npm install zustand lucide-react` in `frontend` and keep lockfile synchronized.

- [x] **Step 2: Write failing SSE parser tests**

Mock fetch with split UTF-8 stream chunks and assert delta accumulation, done response, error event rejection, missing terminal rejection, and abort propagation.

- [x] **Step 3: Verify API RED**

Run `npm run test -- src/api/chat.test.ts` and confirm missing module behavior.

- [x] **Step 4: Implement streaming API wrapper**

POST typed JSON, validate HTTP/body, decode arbitrary chunks, parse SSE frames, invoke delta callback, and return terminal done response.

- [x] **Step 5: Verify API GREEN**

Run focused frontend API tests.

- [x] **Step 6: Write failing store state tests**

Inject a fake streamer and assert optimistic user/assistant messages, delta updates, canonical done state, readable errors, stop preservation, and stale callback suppression after New Chat.

- [x] **Step 7: Verify store RED**

Run focused store tests and confirm missing store behavior.

- [x] **Step 8: Implement Zustand store**

Track active request identity/controller, guard late callbacks, and implement send/stop/new-chat transitions without persistence claims.

- [x] **Step 9: Verify store GREEN**

Run all frontend tests and typecheck.

---

### Task 3: Basic Chat Workspace UI

**Files:**
- Replace: `frontend/src/App.tsx`
- Replace: `frontend/src/styles.css`
- Create: `frontend/src/pages/ChatPage.tsx`
- Create: `frontend/src/components/WorkspaceSidebar.tsx`
- Create: `frontend/src/components/ChatHeader.tsx`
- Create: `frontend/src/components/MessageList.tsx`
- Create: `frontend/src/components/MessageComposer.tsx`

- [x] **Step 1: Implement the Chat page from tested store states**

Compose sidebar, compact header, message list, empty state, error banner, and bottom composer. Use Lucide icon buttons with labels and disabled states.

- [x] **Step 2: Implement responsive styling**

Use restrained neutral surfaces, clear status colors, stable dimensions, no nested cards, no gradients, and mobile layout without overlap.

- [x] **Step 3: Run frontend static verification**

Run typecheck, tests, and production build.

- [x] **Step 4: Run browser flow verification**

Use Playwright interception to verify health, empty, delta, completed, error, stop, and New Chat behavior on desktop and mobile. Save sanitized screenshots under `docs/assets/plan1/` only if they are suitable project evidence.

---

### Task 4: Documentation And Batch Verification

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/03-llm-provider.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

- [x] **Step 1: Synchronize behavior and status**

Mark Batch 8 complete, set next scope to `P1-M3-S7` through `P1-M3-S9`, document streaming success/rollback/stop semantics and frontend environment defaults, and avoid claiming real Provider verification.

- [x] **Step 2: Run complete verification**

Run backend pytest, frontend typecheck/test/build, backend/frontend smoke, `pip check`, browser screenshots, `git diff --check`, status, credential scan, and scope review.

- [x] **Step 3: Complete Codex self-review**

Check stream cleanup, transaction correctness, event framing, stale frontend callbacks, UI states, accessibility, responsive layout, secrets, docs, and Plan boundaries. Do not request Fable 5.
