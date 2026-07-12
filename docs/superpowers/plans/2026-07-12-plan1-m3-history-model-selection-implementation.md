# Plan 1 M3 History And Model Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P1-M3-S7` through `P1-M3-S9` with model selection, recent conversation navigation, URL-based refresh recovery, and M3 test completion.

**Architecture:** Add independent read-only Models, Conversations, and Messages API contracts. Extend the existing Zustand Chat store into the workspace coordinator, while keeping resource fetching in typed API modules and URL synchronization in a pure helper plus `ChatPage` effects.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, SQLAlchemy 2, SQLite, pytest 9, React 19, TypeScript 5.9, Zustand 5, Lucide React, Vitest 4, Playwright CLI.

## Global Constraints

- Work only on `P1-M3-S7` through `P1-M3-S9`.
- Do not add database fields or Alembic migrations.
- Do not add conversation rename/delete/search/pagination, Markdown rendering, token/cost/latency persistence, M4 logging/error envelopes, Tool Calling, RAG, Memory, MCP, Voice, Vision, or Desktop behavior.
- Persist title, selected provider/model, and activity time only with a successful Chat transaction.
- Use `?conversation=<uuid>` for refresh recovery; do not add React Router or localStorage.
- Use existing dependencies; do not install another frontend package.
- Use mocks and browser interception; do not read repository `.env` files or call paid APIs.
- M3 receives Codex self-review only; concentrated Fable 5 or Claude Code review remains after M4.
- The user creates the single Batch 9 Git commit manually after verification.

---

### Task 1: Conversation Listing And Successful-Turn Metadata

**Files:**
- Modify: `backend/app/services/conversation_service.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/test_conversation_service.py`
- Modify: `backend/tests/test_chat_service.py`

**Interfaces:**
- Produces: `ConversationService.list_conversations()` and `ConversationService.record_successful_turn()`.
- Consumes: existing `Conversation`, `Message`, `utc_now()`, and Chat transaction boundaries.

- [x] **Step 1: Write failing Conversation Service tests**

Add tests proving recent-activity order, deterministic ID tie-breaking, title normalization/truncation, provider/model updates, and monotonic activity time:

```python
def test_service_lists_conversations_by_recent_activity(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    older = service.create_conversation(ConversationCreate(title="Older"))
    newer = service.create_conversation(ConversationCreate(title="Newer"))
    older.updated_at = datetime(2026, 1, 1, 12, 0, 0)
    newer.updated_at = datetime(2026, 1, 2, 12, 0, 0)
    session.flush()

    assert service.list_conversations() == [newer, older]

    session.close()
    engine.dispose()


def test_service_records_successful_turn_metadata(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    conversation = service.create_conversation(ConversationCreate())
    previous_updated_at = conversation.updated_at

    service.record_successful_turn(
        conversation,
        provider="provider-b",
        model="model-b",
        title_source="  First   prompt with spacing  ",
    )

    assert conversation.title == "First prompt with spacing"
    assert conversation.default_provider == "provider-b"
    assert conversation.default_model == "model-b"
    assert conversation.updated_at > previous_updated_at

    session.close()
    engine.dispose()
```

Add a title test using content longer than 50 characters and assert the stored title equals the first 50 normalized characters.

- [x] **Step 2: Run Conversation Service RED**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_conversation_service.py -q
```

Expected: FAIL because `list_conversations()` and `record_successful_turn()` do not exist.

- [x] **Step 3: Implement the minimal Conversation Service behavior**

Add deterministic listing and metadata updates:

```python
def list_conversations(self) -> list[Conversation]:
    statement = select(Conversation).order_by(
        Conversation.updated_at.desc(),
        Conversation.id,
    )
    return list(self._session.scalars(statement))

def record_successful_turn(
    self,
    conversation: Conversation,
    *,
    provider: str,
    model: str,
    title_source: str | None = None,
) -> None:
    if title_source is not None:
        normalized_title = " ".join(title_source.split())
        conversation.title = normalized_title[:50] or "New conversation"
    conversation.default_provider = provider
    conversation.default_model = model
    next_updated_at = utc_now()
    if next_updated_at <= conversation.updated_at:
        next_updated_at = conversation.updated_at + timedelta(microseconds=1)
    conversation.updated_at = next_updated_at
    self._session.flush()
```

- [x] **Step 4: Verify Conversation Service GREEN**

Run the focused test file and confirm all tests pass.

- [x] **Step 5: Write failing Chat metadata integration tests**

Extend non-streaming and streaming success tests to assert:

```python
assert result.conversation.title == "First user prompt"
assert result.conversation.default_provider == "openai_compatible"
assert result.conversation.default_model == "example-model"
```

For an existing conversation, send a request using another registered model and assert its defaults and `updated_at` change only after success. Extend Provider failure, streaming failure, and `aclose()` cancellation tests to assert the prior title/defaults/timestamp remain unchanged after rollback.

- [x] **Step 6: Run Chat metadata RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chat_service.py -q
```

Expected: FAIL because Chat does not call `record_successful_turn()`.

- [x] **Step 7: Integrate metadata into both successful Chat paths**

In `complete()` and `stream_complete()`, capture whether the conversation is new:

```python
is_new_conversation = request.conversation_id is None
```

After Provider completion is valid and before returning/committing, call:

```python
self._conversations.record_successful_turn(
    conversation,
    provider=request.provider,
    model=request.model,
    title_source=request.content if is_new_conversation else None,
)
```

Keep the call inside the existing transaction so failure and cancellation rollback all metadata.

- [x] **Step 8: Verify backend service GREEN**

Run both focused service files and confirm all tests pass.

---

### Task 2: Models, Conversation List, And Message List APIs

**Files:**
- Create: `backend/app/schemas/model.py`
- Create: `backend/app/api/v1/models.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/api/v1/conversations.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_chat_api.py`

**Interfaces:**
- Produces: `ModelRead`, `GET /api/v1/models`, `GET /api/v1/conversations`, and `GET /api/v1/conversations/{id}/messages`.
- Consumes: `ModelRegistry.list_models()`, `ConversationService.list_conversations()`, and `ConversationService.list_messages()`.

- [x] **Step 1: Write failing API contract tests**

Extend OpenAPI assertions with:

```python
assert "/api/v1/models" in paths
assert "/api/v1/conversations/{conversation_id}/messages" in paths
```

Add API behavior tests:

```python
def test_models_api_returns_registry_order(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "provider": "openai_compatible",
            "model": "example-model",
            "display_name": "Example Model",
            "supports_streaming": True,
            "supports_tools": False,
            "supports_json": False,
            "input_price_per_1m": None,
            "output_price_per_1m": None,
        }
    ]


def test_conversation_api_lists_recent_conversations_and_messages(
    api_context: Any,
) -> None:
    client, session_factory, _, _ = api_context
    with session_factory() as session:
        older = Conversation(
            title="Older",
            updated_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        newer = Conversation(
            title="Newer",
            updated_at=datetime(2026, 1, 2, 12, 0, 0),
        )
        session.add_all([older, newer])
        session.flush()
        session.add_all(
            [
                Message(
                    conversation_id=newer.id,
                    role="assistant",
                    content="Second",
                    created_at=datetime(2026, 1, 2, 12, 0, 2),
                ),
                Message(
                    conversation_id=newer.id,
                    role="user",
                    content="First",
                    created_at=datetime(2026, 1, 2, 12, 0, 1),
                ),
            ]
        )
        session.commit()
        older_id = str(older.id)
        newer_id = str(newer.id)

    conversations = client.get("/api/v1/conversations")
    messages = client.get(f"/api/v1/conversations/{newer_id}/messages")

    assert conversations.status_code == 200
    assert [item["id"] for item in conversations.json()] == [
        newer_id,
        older_id,
    ]
    assert messages.status_code == 200
    assert [item["content"] for item in messages.json()] == [
        "First",
        "Second",
    ]
```

Add a message-list 404 assertion matching the existing
`Conversation not found: <uuid>` response.

- [x] **Step 2: Run API RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chat_api.py -q
```

Expected: FAIL because the Models route and list/message routes are absent.

- [x] **Step 3: Add the API model schema**

Create `ModelRead` with the exact Registry fields:

```python
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    display_name: str
    supports_streaming: bool
    supports_tools: bool
    supports_json: bool
    input_price_per_1m: Decimal | None = None
    output_price_per_1m: Decimal | None = None
```

Export it from `app.schemas`.

- [x] **Step 4: Implement the Models route**

Create a thin Registry adapter:

```python
router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelRead])
def list_models(
    registry: ModelRegistry = Depends(get_model_registry),
) -> list[ModelRead]:
    return [ModelRead.model_validate(model) for model in registry.list_models()]
```

Include `models_router` in `app.main` under the existing API v1 prefix.

- [x] **Step 5: Implement Conversation read routes**

Add routes before `/{conversation_id}` to avoid ambiguous routing:

```python
@router.get("", response_model=list[ConversationRead])
def list_conversations(
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationRead]:
    return [
        ConversationRead.model_validate(item)
        for item in service.list_conversations()
    ]


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
def list_conversation_messages(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> list[MessageRead]:
    return [
        MessageRead.model_validate(item)
        for item in service.list_messages(conversation_id)
    ]
```

- [x] **Step 6: Verify API GREEN**

Run the focused API tests, then:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m alembic check
```

Expected: all tests pass and Alembic reports no new upgrade operations.

---

### Task 3: Frontend Resource APIs And URL Helper

**Files:**
- Create: `frontend/src/types/models.ts`
- Create: `frontend/src/types/conversations.ts`
- Create: `frontend/src/api/models.ts`
- Create: `frontend/src/api/models.test.ts`
- Create: `frontend/src/api/conversations.ts`
- Create: `frontend/src/api/conversations.test.ts`
- Create: `frontend/src/utils/conversationUrl.ts`
- Create: `frontend/src/utils/conversationUrl.test.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

**Interfaces:**
- Produces: `ModelOption`, `ConversationSummary`, `fetchModels()`, `fetchConversations()`, `fetchConversationMessages()`, `readConversationId()`, and `buildConversationUrl()`.
- Consumes: existing `API_BASE_URL`, `createApiUrl()`, and `ApiMessage`.

- [x] **Step 1: Write failing shared JSON client tests**

Add tests for successful JSON, backend string detail, and fallback HTTP status:

```typescript
it("uses backend detail for JSON request failures", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Conversation missing" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );

  await expect(getJson("/conversations/missing")).rejects.toThrow(
    "Conversation missing",
  );
});
```

- [x] **Step 2: Run client RED and implement readable JSON errors**

Run `npm run test -- src/api/client.test.ts`, confirm the old generic message fails, then update `getJson()` to parse `{ detail?: unknown }` safely and fall back to `Request failed with status <code>`.

- [x] **Step 3: Write failing Models and Conversations API tests**

Mock fetch and assert exact URLs and typed data for:

```typescript
fetchModels();
fetchConversations();
fetchConversationMessages("conversation-1");
```

Use backend-shaped snake_case fixtures, including Registry capability fields and ordered persisted messages.

- [x] **Step 4: Define resource types and wrappers**

Create:

```typescript
export type ModelOption = {
  provider: string;
  model: string;
  display_name: string;
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_json: boolean;
  input_price_per_1m: string | null;
  output_price_per_1m: string | null;
};

export type ConversationSummary = {
  id: string;
  title: string;
  default_provider: string | null;
  default_model: string | null;
  created_at: string;
  updated_at: string;
};
```

Implement wrappers using `getJson<T>()` and URL-encode the conversation ID.

- [x] **Step 5: Verify resource API GREEN**

Run both focused API test files and confirm they pass.

- [x] **Step 6: Write failing URL helper tests**

Cover valid UUID reading, invalid value rejection, replacement, removal, unrelated query preservation, and hash preservation:

```typescript
expect(
  buildConversationUrl("http://localhost:5173/?tab=chat#messages", "conversation-id"),
).toBe("http://localhost:5173/?tab=chat&conversation=conversation-id#messages");
```

Use a valid UUID in `readConversationId()` tests.

- [x] **Step 7: Implement pure URL helpers**

Implement:

```typescript
export function readConversationId(search: string): string | null;
export function buildConversationUrl(href: string, conversationId: string | null): string;
```

Use `URLSearchParams`, preserve unrelated URL state, and validate UUID text with an anchored case-insensitive UUID pattern.

- [x] **Step 8: Verify frontend utility GREEN**

Run all Task 3 tests plus `npm run typecheck`.

---

### Task 4: Zustand Workspace Initialization And Recovery

**Files:**
- Modify: `frontend/src/stores/chatStore.ts`
- Modify: `frontend/src/stores/chatStore.test.ts`
- Modify: `frontend/src/types/chat.ts`

**Interfaces:**
- Produces: expanded `ChatStore`, `ChatStoreDependencies`, `initialize()`, `selectModel()`, `selectConversation()`, and `refreshConversations()`.
- Consumes: Task 3 API functions/types and existing `streamChat()`.

- [x] **Step 1: Refactor existing test setup without changing behavior**

Change store construction from a single streamer argument to dependency overrides:

```typescript
const store = createChatStore({ streamChat: streamer });
```

Provide default successful empty implementations for model/conversation APIs in the test helper so the four existing stream tests remain unchanged.

- [x] **Step 2: Verify existing store tests remain GREEN**

Run `npm run test -- src/stores/chatStore.test.ts` before adding new behavior.

- [x] **Step 3: Write failing initialization and selection tests**

Add tests for:

- models and conversations load in parallel
- configured environment model wins when present; first Registry entry is fallback
- URL conversation ID restores messages and saved model
- selecting another model changes the next Chat request
- selecting a conversation maps persisted user/assistant messages to complete UI messages
- a stale history request cannot replace a newer selection
- New Chat clears conversation/messages but retains model
- successful Chat refreshes and reorders conversation summaries
- no model disables send by making `sendMessage()` a no-op with readable workspace error

Use deferred Promises for stale-response tests and injected functions rather than global fetch mocks.

- [x] **Step 4: Run expanded store RED**

Run the focused store test and confirm failures are for missing state/actions.

- [x] **Step 5: Implement expanded dependency and state contracts**

Use this dependency shape:

```typescript
export type ChatStoreDependencies = {
  streamChat: StreamChatFunction;
  fetchModels: () => Promise<ModelOption[]>;
  fetchConversations: () => Promise<ConversationSummary[]>;
  fetchConversationMessages: (conversationId: string) => Promise<ApiMessage[]>;
  defaultProvider: string;
  defaultModel: string;
};
```

Production dependencies pass the two existing Vite environment defaults;
tests override them with literal values.

Add state fields:

```typescript
models: ModelOption[];
conversations: ConversationSummary[];
selectedProvider: string | null;
selectedModel: string | null;
workspaceStatus: "idle" | "loading" | "ready" | "error";
conversationStatus: "idle" | "loading" | "error";
workspaceError: string | null;
selectionRequestId: string | null;
```

Keep existing stream `status` and `error` separate from workspace loading errors.

- [x] **Step 6: Implement initialization and model selection**

`initialize(conversationId)` must:

1. return early when `workspaceStatus` is already `loading` or `ready`
2. load models and conversations with `Promise.all`
3. select `VITE_DEFAULT_PROVIDER/VITE_DEFAULT_MODEL` when registered, otherwise the first model
4. store ready/empty/error state
5. call `selectConversation()` only when the URL ID exists in the loaded list

`selectModel(provider, model)` must accept only a registered pair and do nothing during streaming.

- [x] **Step 7: Implement guarded conversation selection**

Generate a selection request ID, keep existing messages visible while loading, and apply fetched messages only when the ID is still current. Restore saved provider/model only when that exact pair exists in `models`.

Map persisted messages to:

```typescript
{
  id: message.id,
  role: message.role,
  content: message.content,
  status: "complete",
}
```

The current Plan 1 database only stores user/assistant turns through Chat; ignore unsupported roles defensively rather than inventing UI behavior.

- [x] **Step 8: Update streaming send and New Chat behavior**

Build requests from `selectedProvider/selectedModel`. After successful `done`,
await `refreshConversations()`. That action catches its own request failure,
stores `workspaceError`, and does not throw back into the completed Chat path,
so persisted messages remain complete. New Chat aborts the active stream,
invalidates selection requests, clears selected conversation/messages/errors,
and retains the model pair.

- [x] **Step 9: Verify store GREEN**

Run the focused store tests, all frontend tests, and typecheck.

---

### Task 5: Model Selector, Conversation Navigation, And URL Wiring

**Files:**
- Create: `frontend/src/components/ModelSelector.tsx`
- Create: `frontend/src/components/ConversationList.tsx`
- Modify: `frontend/src/components/ChatHeader.tsx`
- Modify: `frontend/src/components/WorkspaceSidebar.tsx`
- Modify: `frontend/src/components/MessageComposer.tsx`
- Modify: `frontend/src/components/MessageList.tsx`
- Modify: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Produces: usable model selection, recent conversation list, loading/empty/error states, and URL synchronization.
- Consumes: Task 4 store actions/state and Task 3 URL helpers.

- [x] **Step 1: Add the model selector**

Implement a native `<select>` labeled `Model` with stable option values produced by a helper such as `JSON.stringify([provider, model])`. Display `display_name`, keep provider visible in secondary text or option copy, and disable the control while loading, empty, or streaming.

- [x] **Step 2: Add the conversation list**

Render compact buttons with title and formatted recent time. Include:

- loading placeholder rows with stable height
- `No saved conversations` empty state
- selected state using `aria-current="true"`
- disabled interaction while streaming or loading a conversation

Use `ConversationList` in the desktop sidebar. On mobile, `WorkspaceSidebar` exposes the same list through an icon button and a compact overlay panel; selecting a conversation closes the panel.

- [x] **Step 3: Wire page initialization and URL recovery**

On mount:

```typescript
void initialize(readConversationId(window.location.search));
```

After `workspaceStatus` becomes `ready`, subscribe to `conversationId` and
update the current URL without navigation. This prevents the initial `null`
store value from clearing a valid query parameter before restoration finishes:

```typescript
window.history.replaceState(
  null,
  "",
  buildConversationUrl(window.location.href, conversationId),
);
```

Avoid duplicate network initialization under React StrictMode by keeping the guard in the store.

- [x] **Step 4: Complete async UI states**

- show conversation loading without clearing the previous message list
- show workspace and stream errors separately
- disable composer when no selected model, during initialization, or during history loading
- show a short loading label in the message area when restoring the first conversation
- keep New Chat available to cancel an active stream

- [x] **Step 5: Implement responsive styling**

Keep the existing neutral palette and 6px-or-less command radii. Give the desktop sidebar a stable scrollable conversation region, keep API status anchored below it, and verify the mobile overlay fits within 390px width without covering the composer controls incoherently.

- [x] **Step 6: Run static frontend verification**

Run:

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

Expected: all commands exit 0.

- [x] **Step 7: Run Playwright browser verification**

Start Vite and intercept Models, Conversations, Messages, Health, and Stream requests. Verify on 1440x900 and 390x844:

1. model options load and selection changes
2. conversations render newest first
3. selecting a conversation loads ordered messages and updates the URL
4. reload with the URL restores the same messages and model
5. New Chat clears URL/messages and preserves model selection
6. loading, empty, and API error states remain readable
7. no text overflow, horizontal scrolling, or control overlap

Inspect screenshots with `view_image`. Keep screenshots temporary unless they are sanitized, durable M3 acceptance evidence.

---

### Task 6: M3 Documentation, Regression Verification, And Self-Review

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/03-llm-provider.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`
- Modify: this implementation plan checklist

**Interfaces:**
- Produces: accurate M3 completion documentation and a verified manual-commit batch.

- [x] **Step 1: Synchronize documentation**

Document:

- `GET /api/v1/models`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{id}/messages`
- automatic first-message titles
- last-successful model/activity semantics
- `?conversation=<uuid>` refresh recovery
- frontend model and conversation loading states
- M3 completed through `P1-M3-S9`
- next scope `P1-M4-S1` through `P1-M4-S3`

Mark Batch 9 complete. Do not claim Markdown, rename/delete, real Provider verification, or M4 observability.

- [x] **Step 2: Run complete backend verification**

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
```

Run `F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m pip check` from the repository root.

- [x] **Step 3: Run complete frontend verification**

From `frontend`:

```powershell
npm run typecheck
npm run test
npm run build
```

- [x] **Step 4: Run startup smoke without repository secrets**

Start Uvicorn from a newly created empty temporary working directory with `PYTHONPATH` pointing to `backend`, then verify:

- `GET /api/v1/health` returns 200
- OpenAPI contains all Models, Conversations, Messages, non-streaming Chat, and streaming Chat routes

Start Vite and confirm it reaches ready. Stop both processes and confirm ports are released. Do not start the backend from a directory where Pydantic could read a repository `.env` file.

- [x] **Step 5: Run final repository checks**

Run:

```powershell
git diff --check
git status --short
```

Scan changed and untracked files for credential-like values, verify no `.db`, `dist`, cache, Playwright session, or screenshot artifact is tracked, and confirm the diff contains only Batch 9 files.

- [x] **Step 6: Complete Codex self-review**

Review:

- list/message ordering and 404 behavior
- metadata rollback on Provider failure/cancellation
- Registry response contains no Provider credentials
- strict URL UUID handling and unrelated query preservation
- stale history/stream callback suppression
- no-model and failed-initialization behavior
- desktop/mobile accessibility and layout
- docs accuracy and Plan 1 boundaries

Classify every finding as must fix, later batch, limitation, or not applicable. Fix blocking issues and rerun affected verification.

- [x] **Step 7: Prepare manual commit guidance**

Do not stage or commit. Suggest this message after every check passes:

```text
feat(chat): add model selection and conversation recovery
```
