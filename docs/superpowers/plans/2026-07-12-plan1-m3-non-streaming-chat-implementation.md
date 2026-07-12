# Plan 1 M3 Non-Streaming Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `P1-M3-S1` through `P1-M3-S3` with transactional Conversation and non-streaming Chat services plus thin FastAPI routes.

**Architecture:** Synchronous SQLAlchemy services share one request-scoped session, while Chat Service awaits an injected `BaseLLMProvider`. The backend owns conversation history, Registry validates model identity, a provider mapping resolves adapters, and request dependencies commit on success or roll back on error.

**Tech Stack:** Python 3.11, FastAPI 0.138, Pydantic 2, SQLAlchemy 2, SQLite, pytest 9, FastAPI TestClient.

## Global Constraints

- Work only on `P1-M3-S1` through `P1-M3-S3`.
- Do not add API-level streaming, frontend Chat, conversation list/history endpoints, Tool Calling, JSON mode, cost/latency recording, retries, logging, RAG, Memory, MCP, Voice, Vision, or Desktop behavior.
- Use temporary SQLite databases and mock Providers only.
- Keep routes thin and business logic in services.
- Persist no token/cost/latency values before `P1-M4-S1`.
- M3 uses Codex self-review only; the next Fable 5 review is after M4.
- The user creates the Git commit manually.

---

### Task 1: Conversation Service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/errors.py`
- Create: `backend/app/services/conversation_service.py`
- Create: `backend/tests/test_conversation_service.py`

**Interfaces:**
- Produces: `ConversationNotFoundError` and `ConversationService.create_conversation()`, `get_conversation()`, `append_message()`, `list_messages()`.

- [ ] **Step 1: Write failing Conversation Service tests**

Use a temporary SQLite session to assert create/lookup, message append, deterministic message ordering, and readable missing-conversation failure.

- [ ] **Step 2: Verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_conversation_service.py -q
```

Expected: collection fails because `app.services.conversation_service` does not exist.

- [ ] **Step 3: Implement minimal service behavior**

Inject `Session`, use existing ORM/Pydantic schemas, call `flush()` after inserts, query ordered messages, and raise `ConversationNotFoundError` for unknown UUIDs.

- [ ] **Step 4: Verify GREEN**

Run the focused test and expect all Conversation Service tests to pass.

---

### Task 2: Non-Streaming Chat Service

**Files:**
- Create: `backend/app/schemas/chat.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/chat_service.py`
- Modify: `backend/app/services/errors.py`
- Modify: `backend/app/services/__init__.py`
- Create: `backend/tests/test_chat_service.py`

**Interfaces:**
- Consumes: `ConversationService`, `ModelRegistry`, `Mapping[str, BaseLLMProvider]`, and `ChatCompletionRequest`.
- Produces: `ChatCompletionResult`, `ChatModelNotFoundError`, `ChatProviderUnavailableError`, and `ChatService.complete()`.

- [ ] **Step 1: Write failing successful-chat tests**

Create a mock Provider that captures `ChatRequest` and returns `LLMResponse`. Assert new and existing conversation history, assistant persistence, actual response model, completed `LLMCall`, and returned usage.

- [ ] **Step 2: Verify success-path RED**

Run `tests/test_chat_service.py` and expect missing module/type failures.

- [ ] **Step 3: Implement the success path**

Validate Registry/model and provider mapping, compose history, await Provider chat, append assistant and `LLMCall`, flush, and return `ChatCompletionResult`.

- [ ] **Step 4: Verify success-path GREEN**

Run focused Chat Service success tests.

- [ ] **Step 5: Write failing error/rollback tests**

Assert unknown models fail before Provider invocation, unavailable adapters fail clearly, and Provider exceptions roll back newly created ORM records.

- [ ] **Step 6: Verify error-path RED**

Run focused tests and confirm missing validation/rollback behavior fails for the expected reason.

- [ ] **Step 7: Implement minimal errors and rollback**

Add focused service exceptions and roll back before re-raising `LLMProviderError`.

- [ ] **Step 8: Verify Chat Service GREEN**

Run Chat Service tests followed by the full backend suite.

---

### Task 3: FastAPI Dependencies And Routes

**Files:**
- Create: `backend/app/api/dependencies.py`
- Create: `backend/app/api/errors.py`
- Create: `backend/app/api/v1/conversations.py`
- Create: `backend/app/api/v1/chat.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_chat_api.py`

**Interfaces:**
- Produces: request-scoped session/provider/registry/service dependencies, three routes, and basic exception handlers.

- [ ] **Step 1: Write failing OpenAPI and Conversation API tests**

Override database dependencies with a temporary SQLite session and assert route visibility, conversation creation, lookup, and 404 response.

- [ ] **Step 2: Verify API RED**

Run `tests/test_chat_api.py` and expect missing routes.

- [ ] **Step 3: Implement dependencies, basic handlers, and Conversation routes**

Yield a request session that commits after success and rolls back on exceptions. Add service dependencies, basic safe exception mappings, and thin Conversation routes.

- [ ] **Step 4: Verify Conversation API GREEN**

Run focused Conversation API tests.

- [ ] **Step 5: Write failing Chat API tests**

Override provider mapping and Registry dependencies. Assert 200 response shape, persistence, 400 unknown model, 503 missing adapter, 502 Provider failure with rollback, and 422 invalid content.

- [ ] **Step 6: Verify Chat API RED**

Run the Chat API tests and confirm the route/behavior is absent.

- [ ] **Step 7: Implement the thin Chat route**

Call `ChatService.complete()` and map `ChatCompletionResult` into `ChatCompletionResponse` without persistence or Provider logic in the route.

- [ ] **Step 8: Verify API GREEN**

Run focused API tests and the complete backend suite.

---

### Task 4: Documentation, Review Cadence, And Verification

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

- [ ] **Step 1: Synchronize implemented behavior and review cadence**

Mark Batch 7 complete, set the next scope to `P1-M3-S4` through `P1-M3-S6`, document the three routes and mock-only verification, and change M3 review actions to Codex-only while retaining the M4 final consolidated review.

- [ ] **Step 2: Run complete verification**

Run backend pytest, frontend typecheck/test/build, backend/frontend smoke checks, `pip check`, `git diff --check`, status, credential scan, and scope review.

- [ ] **Step 3: Complete Codex self-review**

Check transaction atomicity, route thinness, no real credentials, no later-step features, docs accuracy, and known limitations. Do not request Fable 5 for M3.
