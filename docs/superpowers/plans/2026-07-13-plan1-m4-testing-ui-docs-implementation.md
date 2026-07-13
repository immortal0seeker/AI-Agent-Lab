# Plan 1 M4 Testing, UI States, And Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P1-M4-S4` through `P1-M4-S6` with focused backend contract coverage, recoverable frontend initialization states, and accurate startup/configuration documentation.

**Architecture:** Extend existing backend tests without changing production behavior unless a new test exposes a defect. Add one presentational frontend component and wire it through `ChatPage`, while reusing the existing Zustand initialization action. Finish with documentation and environment-example corrections, then run full local and browser verification.

**Tech Stack:** Python 3.11, FastAPI, pytest, SQLAlchemy, React 19, TypeScript, Zustand, Vitest, React DOM server rendering, Vite, SQLite, Alembic.

## Global Constraints

- Work only on `P1-M4-S4` through `P1-M4-S6`.
- Do not add dependencies, migrations, release screenshots, `CHANGELOG.md`, tags, Trace, Tool Calling, RAG, Memory, MCP, Voice, Vision, Desktop, or later-plan capabilities.
- Do not read real `.env` files and do not call a real or paid Provider.
- Use mock Providers, temporary databases, and mocked browser requests.
- Keep all example credentials empty and all test credentials obviously fake.
- The user creates the Git commit manually. Do not stage or commit during the tasks below.
- Follow TDD for every production-code change: observe the intended test fail, make the smallest implementation, and rerun it.
- Treat the known Starlette TestClient/httpx deprecation warning as an existing non-blocking limitation.

---

### Task 1: Add Health And Provider Contract Coverage

**Files:**
- Modify: `backend/tests/test_health.py`
- Modify: `backend/tests/test_openai_compatible_provider.py`

**Interfaces:**
- Consumes: `RequestContextMiddleware`, `OpenAICompatibleProvider.stream_chat()`, `ProviderTimeoutError`, and `ProviderUnknownError`.
- Produces: regression coverage for successful request IDs and safe streaming transport classification.

- [ ] **Step 1: Add a health request-ID test**

Add `from uuid import UUID` and this test to `backend/tests/test_health.py`:

```python
def test_health_endpoint_includes_server_request_id() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "client-controlled"},
        )

    request_id = response.headers["x-request-id"]
    assert response.status_code == 200
    assert request_id != "client-controlled"
    UUID(request_id)
```

- [ ] **Step 2: Run the focused health test**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_health.py -q
```

Expected: all health tests pass. This documents existing behavior, so a pass on the first run is valid.

- [ ] **Step 3: Add streaming transport-classification tests**

Add the following parameterized test to `backend/tests/test_openai_compatible_provider.py`:

```python
@pytest.mark.parametrize(
    ("error_type", "expected_error"),
    [
        (httpx.ReadTimeout, ProviderTimeoutError),
        (httpx.ConnectError, ProviderUnknownError),
    ],
)
def test_stream_chat_translates_transport_errors_without_private_text(
    error_type: type[httpx.RequestError],
    expected_error: type[ProviderRequestError],
) -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise error_type("private streaming diagnostic", request=request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            async for _ in provider.stream_chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            ):
                pass

    with pytest.raises(expected_error) as exc_info:
        asyncio.run(exercise())

    assert "private streaming diagnostic" not in str(exc_info.value)
    assert "test-secret-key" not in str(exc_info.value)
```

Use the already imported `ProviderRequestError`; no new production symbol is introduced.

- [ ] **Step 4: Run the focused Provider tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
```

Expected: all Provider adapter tests pass. If the new test fails because private text leaks or the error class is wrong, keep the test and make only the smallest adapter correction required by the approved design.

- [ ] **Step 5: Record the manual-commit checkpoint**

```powershell
git diff --check
git status --short
```

Expected: only the design/plan files and the two backend test files are new or modified at this checkpoint. Do not stage or commit.

---

### Task 2: Add Chat, Conversation, And Unified-Error Coverage

**Files:**
- Modify: `backend/tests/test_chat_api.py`
- Create: `backend/tests/test_error_handling.py`
- Modify only if a test exposes a defect: `backend/app/api/errors.py`, `backend/app/core/request_context.py`, or the directly responsible existing module

**Interfaces:**
- Consumes: unified error envelope `{error: {code, message, request_id}}`, `X-Request-ID`, Chat transaction rollback, and current Provider error subclasses.
- Produces: API-level coverage for classified HTTP/SSE errors, conversation defaults/validation, safe 405 responses, and safe unexpected failures.

- [ ] **Step 1: Extend the test Provider classes**

Import `ProviderRateLimitError` and `ProviderTimeoutError` in `backend/tests/test_chat_api.py`, then add:

```python
class TimeoutProvider(MockProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        raise ProviderTimeoutError(
            "private timeout diagnostic",
            status_code=504,
        )


class RateLimitedStreamingProvider(MockProvider):
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        if False:
            yield ChatChunk()
        raise ProviderRateLimitError(
            "private rate-limit diagnostic",
            status_code=429,
        )
```

- [ ] **Step 2: Add non-streaming classified-error rollback coverage**

Add:

```python
def test_chat_api_maps_timeout_and_rolls_back(api_context: Any) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = TimeoutProvider()

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello",
        },
    )

    assert response.status_code == 504
    assert response.json() == {
        "error": {
            "code": "provider_timeout",
            "message": "The model provider timed out",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private timeout diagnostic" not in response.text
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
```

- [ ] **Step 3: Add streaming classified-error rollback coverage**

Add:

```python
def test_stream_chat_api_maps_rate_limit_and_rolls_back(
    api_context: Any,
) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = RateLimitedStreamingProvider()

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello stream",
        },
    )

    assert response.status_code == 200
    assert parse_sse_events(response.text) == [
        (
            "error",
            {
                "error": {
                    "code": "provider_rate_limit",
                    "message": "The model provider rate limit was exceeded",
                    "request_id": response.headers["x-request-id"],
                }
            },
        )
    ]
    assert "private rate-limit diagnostic" not in response.text
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
```

- [ ] **Step 4: Add conversation default and validation coverage**

Add:

```python
def test_conversation_api_uses_default_title(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.post("/api/v1/conversations", json={})

    assert response.status_code == 201
    assert response.json()["title"] == "New conversation"
    assert response.json()["default_provider"] is None
    assert response.json()["default_model"] is None


def test_conversation_api_rejects_malformed_id_with_unified_error(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    response = client.get("/api/v1/conversations/not-a-uuid")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
            "request_id": response.headers["x-request-id"],
        }
    }
```

- [ ] **Step 5: Add isolated unified-error tests**

Create `backend/tests/test_error_handling.py`:

```python
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.core.request_context import RequestContextMiddleware


SENSITIVE_DETAIL = "private unexpected diagnostic"


def create_test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(test_app)

    @test_app.get("/ok")
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/explode")
    def explode() -> None:
        raise RuntimeError(SENSITIVE_DETAIL)

    return test_app


def test_method_not_allowed_uses_unified_error() -> None:
    with TestClient(create_test_app()) as client:
        response = client.post("/ok")

    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Method not allowed",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_unexpected_error_is_safe_and_request_linked(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.error"):
        with TestClient(
            create_test_app(),
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/explode")

    request_id = response.headers["x-request-id"]
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "The request could not be completed",
            "request_id": request_id,
        }
    }
    assert SENSITIVE_DETAIL not in response.text
    assert SENSITIVE_DETAIL not in caplog.text
    assert any(
        record.getMessage() == "request_failed"
        and record.error_code == "internal_error"
        and record.request_id == request_id
        for record in caplog.records
    )
```

- [ ] **Step 6: Run the focused API/error tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chat_api.py tests/test_error_handling.py -q
```

Expected: all tests pass. If any new contract test fails, preserve the test, diagnose the responsible layer, and make the smallest production change. Do not weaken safe messages or rollback assertions to make a test pass.

- [ ] **Step 7: Run the complete backend suite**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass with only the known TestClient/httpx deprecation warning.

---

### Task 3: Drive Explicit Frontend Initialization States With Tests

**Files:**
- Create: `frontend/src/pages/ChatPage.test.tsx`
- Create: `frontend/src/components/WorkspaceStatusPanel.tsx`
- Modify: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `workspaceStatus`, `workspaceError`, `initialize(conversationId)`, and `readConversationId(search)`.
- Produces: distinct loading and initialization-error views, plus an accessible Retry action.

- [ ] **Step 1: Write failing page-state tests**

Create `frontend/src/pages/ChatPage.test.tsx`:

```tsx
import { afterEach, describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { useChatStore } from "../stores/chatStore";
import ChatPage from "./ChatPage";


const initialState = useChatStore.getState();

afterEach(() => {
  useChatStore.setState(initialState, true);
});

describe("ChatPage workspace states", () => {
  it("shows initialization loading instead of the ready empty state", () => {
    useChatStore.setState({
      workspaceStatus: "loading",
      workspaceError: null,
      messages: [],
    });

    const html = renderToStaticMarkup(<ChatPage />);

    expect(html).toContain("Loading Chat workspace...");
    expect(html).not.toContain("Start a conversation");
  });

  it("shows one initialization error with a retry action", () => {
    const message = "Unable to initialize Chat workspace";
    useChatStore.setState({
      workspaceStatus: "error",
      workspaceError: message,
      messages: [],
    });

    const html = renderToStaticMarkup(<ChatPage />);

    expect(html.match(new RegExp(message, "g"))).toHaveLength(1);
    expect(html).toContain(">Retry<");
    expect(html).not.toContain("Start a conversation");
  });
});
```

- [ ] **Step 2: Run the tests and verify RED**

Run from `frontend/`:

```powershell
npm run test -- --run src/pages/ChatPage.test.tsx
```

Expected: both assertions fail because the current page still renders the empty state during initialization and has no Retry action.

- [ ] **Step 3: Add the minimal status component**

Create `frontend/src/components/WorkspaceStatusPanel.tsx`:

```tsx
import { AlertCircle, LoaderCircle, RotateCcw } from "lucide-react";


type WorkspaceStatusPanelProps =
  | { status: "loading" }
  | { status: "error"; message: string; onRetry: () => void };


export default function WorkspaceStatusPanel(
  props: WorkspaceStatusPanelProps,
) {
  if (props.status === "loading") {
    return (
      <div className="workspace-state" role="status" aria-live="polite">
        <LoaderCircle size={20} aria-hidden="true" />
        <strong>Loading Chat workspace...</strong>
        <span>Loading models and recent conversations.</span>
      </div>
    );
  }

  return (
    <div className="workspace-state workspace-state--error" role="alert">
      <AlertCircle size={22} aria-hidden="true" />
      <strong>Unable to load Chat workspace</strong>
      <span>{props.message}</span>
      <button type="button" onClick={props.onRetry}>
        <RotateCcw size={15} aria-hidden="true" />
        Retry
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Wire the component through ChatPage**

In `frontend/src/pages/ChatPage.tsx`:

1. Import `WorkspaceStatusPanel`.
2. Add a retry function that calls the existing initializer with the current URL conversation ID:

```tsx
const retryInitialization = () => {
  void initialize(readConversationId(window.location.search));
};
```

3. Restrict the existing top banner to the ready workspace so initialization errors are not duplicated:

```tsx
const visibleError =
  workspaceStatus === "ready" ? (error ?? workspaceError) : null;
```

4. Replace the unconditional message-list rendering inside `.chat-content` with:

```tsx
{workspaceStatus === "error" ? (
  <WorkspaceStatusPanel
    status="error"
    message={workspaceError ?? "Unable to initialize Chat workspace"}
    onRetry={retryInitialization}
  />
) : workspaceStatus !== "ready" ? (
  <WorkspaceStatusPanel status="loading" />
) : (
  <>
    {isConversationLoading ? (
      <div className="conversation-loading" role="status">
        <LoaderCircle size={15} aria-hidden="true" />
        Loading conversation...
      </div>
    ) : null}
    <MessageList messages={messages} />
  </>
)}
```

Keep the existing composer/model disabled conditions unchanged.

- [ ] **Step 5: Add focused styles**

Add to `frontend/src/styles.css` near `.chat-content`:

```css
.workspace-state {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  min-height: 100%;
  padding: 32px;
  color: #6c7981;
  text-align: center;
}

.workspace-state > svg {
  animation: loading-spin 1s linear infinite;
}

.workspace-state strong {
  color: #303941;
  font-size: 15px;
}

.workspace-state span {
  font-size: 12px;
}

.workspace-state--error > svg {
  color: #b13d2e;
  animation: none;
}

.workspace-state--error button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 5px;
  padding: 7px 12px;
  border: 1px solid #c9d1d6;
  border-radius: 5px;
  background: #ffffff;
  color: #344149;
  font-weight: 650;
}
```

Add `.workspace-state > svg` to the existing reduced-motion selector.

- [ ] **Step 6: Run the page-state tests and verify GREEN**

```powershell
npm run test -- --run src/pages/ChatPage.test.tsx
```

Expected: 2 tests pass.

- [ ] **Step 7: Run frontend typecheck and existing tests**

```powershell
npm run typecheck
npm run test -- --run
```

Expected: typecheck and all tests pass.

---

### Task 4: Document Retry Re-Initialization In The Store Contract

**Files:**
- Modify: `frontend/src/stores/chatStore.test.ts`
- Modify only if the existing behavior test fails: `frontend/src/stores/chatStore.ts`

**Interfaces:**
- Consumes: `initialize(conversationId)` from the `error` state.
- Produces: a stable contract that Retry clears the error and reaches `ready` after a later successful request.

- [ ] **Step 1: Add the retry contract test**

Add to `frontend/src/stores/chatStore.test.ts`:

```tsx
it("retries initialization after a failed attempt", async () => {
  let modelCalls = 0;
  const store = createChatStore(
    createWorkspaceDependencies({
      fetchModels: async () => {
        modelCalls += 1;
        if (modelCalls === 1) {
          throw new Error("Registry temporarily unavailable");
        }
        return models;
      },
    }),
  );

  await store.getState().initialize(null);
  expect(store.getState()).toMatchObject({
    workspaceStatus: "error",
    workspaceError: "Registry temporarily unavailable",
  });

  await store.getState().initialize(null);
  expect(store.getState()).toMatchObject({
    models,
    conversations,
    selectedProvider: "provider-a",
    selectedModel: "model-a",
    workspaceStatus: "ready",
    workspaceError: null,
  });
  expect(modelCalls).toBe(2);
});
```

- [ ] **Step 2: Run the store test**

```powershell
npm run test -- --run src/stores/chatStore.test.ts
```

Expected: the test passes because the existing guard only blocks `loading` and `ready`, not `error`. If it fails, retain the contract and make only the smallest store correction; do not add retry counts, delays, or backoff.

- [ ] **Step 3: Run the complete frontend checks**

```powershell
npm run typecheck
npm run test -- --run
npm run build
```

Expected: all frontend checks pass and Vite produces `dist/` as an ignored build artifact.

---

### Task 5: Align Environment Examples And Plan 1 Documentation

**Files:**
- Modify: `.env.example`
- Modify: `backend/.env.example`
- Modify: `frontend/.env.example`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/03-llm-provider.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: the implemented startup commands, settings aliases, frontend environment names, UI states, and verification commands.
- Produces: an accurate clean-start guide and completed S4-S6 plan record.

- [ ] **Step 1: Clarify the three environment examples**

Make the root example begin with:

```dotenv
# Workspace-level reference for AI Agent Lab.
# The current backend and frontend do not load this root file automatically.
# Copy the service-specific examples instead; never commit real secrets.
```

Make `backend/.env.example` begin with:

```dotenv
# Copy to backend/.env for local backend commands.
# Keep OPENAI_COMPATIBLE_API_KEY empty in tracked files.
```

Make `frontend/.env.example` begin with:

```dotenv
# Copy to frontend/.env for local Vite commands.
# VITE_* values are exposed to the browser and must never contain secrets.
```

Keep the existing variable names and safe example values unchanged.

- [ ] **Step 2: Update README stage and clean-start instructions**

In both READMEs:

- change completed scope to `P1-M1-S1` through `P1-M4-S6`;
- change next scope to `P1-M4-S7` through `P1-M4-S8`;
- explain that users copy `backend/.env.example` to `backend/.env` and
  `frontend/.env.example` to `frontend/.env`, while the root example is not
  automatically loaded;
- retain an empty Provider key and state that health/startup/tests work without
  a real Provider call;
- describe initialization loading, initialization error with Retry, ready empty,
  conversation loading, streaming, completed, stopped, and Chat-error states;
- change the commit note to Batch 11 and use the suggested message
  `test(plan1): harden chat workspace checks and docs`.

Use these exact verification blocks:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

- [ ] **Step 3: Update formal docs**

Make these exact scope changes:

```text
docs/00-project-overview.md: completed through P1-M4-S6; next P1-M4-S7-S8.
docs/01-architecture.md: document WorkspaceStatusPanel and Retry data flow.
docs/03-llm-provider.md: list the expanded mock error/stream verification and keep the no-real-provider boundary.
```

Do not describe screenshots, a changelog, a final review result, or a tag as completed.

- [ ] **Step 4: Mark only Batch 11 steps complete**

In the execution table:

- mark Batch 11 complete;
- mark `P1-M4-S4`, `P1-M4-S5`, and `P1-M4-S6` complete;
- leave Batch 12, `P1-M4-S7`, and `P1-M4-S8` incomplete.

- [ ] **Step 5: Check documentation and configuration consistency**

```powershell
rg -n "P1-M4-S3|P1-M4-S4.*P1-M4-S6|Batch 10|finalized during Plan 1" README.md README_CN.md docs .env.example backend/.env.example frontend/.env.example
rg -n "OPENAI_COMPATIBLE_API_KEY\s*=\s*\S+" .env.example backend/.env.example frontend/.env.example README.md README_CN.md docs
git diff --check
```

Expected: no stale stage/Batch 10 text, no non-empty key, and no whitespace errors. Review every match rather than assuming zero output for the scope-range search.

---

### Task 6: Run Full Verification And Codex Self-Review

**Files:**
- Verify all changed files.
- Do not create release artifacts or commits.

**Interfaces:**
- Consumes: all Task 1-5 deliverables.
- Produces: fresh completion evidence and a manual-commit handoff.

- [ ] **Step 1: Run backend verification**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: all tests pass, pip reports no broken requirements, and only the known TestClient/httpx warning remains.

- [ ] **Step 2: Verify a fresh temporary SQLite database**

Set `DATABASE_URL` only for the command process to a new temporary database,
then run:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
```

Expected: head is current and Alembic reports no new upgrade operations. Delete only the newly created temporary database after resolving and verifying its path. Do not touch the user's existing local SQLite file.

- [ ] **Step 3: Run frontend verification**

From `frontend/`:

```powershell
npm run typecheck
npm run test -- --run
npm run build
```

Expected: typecheck, all tests, and production build pass.

- [ ] **Step 4: Run Uvicorn smoke checks**

Start Uvicorn on an unused local port with a temporary SQLite database and a hidden background process. Verify:

```text
GET /api/v1/health -> 200 with UUID X-Request-ID
GET /openapi.json -> required Plan 1 routes exist
GET /api/v1/conversations/not-a-uuid -> 422 validation_error with matching request ID
POST /api/v1/health -> 405 http_error with matching request ID
```

Stop the process and confirm the port has no listener.

- [ ] **Step 5: Run Vite and browser-mock smoke checks**

Before browser automation, load the repository `playwright` skill. Start Vite in a hidden background process, mock `/models`, `/conversations`, `/health`, and Chat requests, then verify:

```text
initial models request fails -> one initialization error and Retry are visible
click Retry -> models/conversations load, empty state appears, composer is enabled
loading state appears without the ready empty prompt
normal mocked Chat still streams and reaches completed state
desktop and mobile layouts remain usable
```

Stop Vite and confirm its port has no listener. Store no private screenshots; S7 owns release screenshots.

- [ ] **Step 6: Run scope, secret, and artifact scans**

```powershell
git status --short
git diff --stat
git diff --check
rg -n --hidden -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/.venv/**' '(sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,}|OPENAI_COMPATIBLE_API_KEY\s*=\s*\S+)' .
rg --files -g '*.pem' -g '*.key' -g 'id_rsa*' -g 'id_ed25519*'
```

Expected: only clearly fake test credentials may match; no real secrets or sensitive artifacts are present. Confirm build output, databases, caches, and logs are ignored or removed from the status list.

- [ ] **Step 7: Complete Codex self-review**

Check every item:

```text
Only P1-M4-S4-S6 files and behavior changed.
No later-plan or S7-S8 release capability was added.
No production backend change lacks a demonstrated failing test.
Frontend Retry does not add retry loops, backoff, or hidden automatic retries.
Normal Chat and conversation recovery remain intact.
README/docs/env examples match actual loading paths and commands.
No real secret or full sensitive content appears in code, docs, tests, logs, or status.
Fresh verification evidence supports every completion claim.
```

- [ ] **Step 8: Prepare the manual-commit handoff**

Report:

- change summary;
- verification results;
- Codex self-review findings;
- whether Fable 5 / Claude Code review is needed;
- residual risks and limitations;
- next batch `P1-M4-S7` through `P1-M4-S8`;
- suggested commit message: `test(plan1): harden chat workspace checks and docs`.

Do not stage, commit, tag, or push.
