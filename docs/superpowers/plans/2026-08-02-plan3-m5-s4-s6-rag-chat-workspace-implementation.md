# Plan 3 M5 S4～S6 RAG Chat Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. This
> repository explicitly forbids subagents, branches, worktrees, staging, and
> commits for this batch; keep checkbox progress in this file and leave Git to
> the user.

**Goal:** Add a typed, non-streaming frontend RAG Chat flow inside the existing
Knowledge workspace, including exact source citations and traceable IDs.

**Architecture:** The existing `KnowledgeBasePage` keeps Knowledge Base and
document ownership and adds Documents/RAG Chat tabs. A focused Zustand store
owns registered-model initialization, one dedicated Conversation per current
RAG session, non-streaming requests, current-session turns, and stale-response
guards. Small answer/source components render exact backend data as escaped
text without adding retrieval behavior.

**Tech Stack:** React 19, TypeScript, Zustand, Vitest/jsdom, Vite, existing
FastAPI RAG/Conversation/Model APIs.

## Global Constraints

- Implement only `P3-M5-S4～S6`; do not start M6 or Plan 4+ runtime.
- Do not add or modify backend routes, ORM models, schemas, migrations, or the
  protected `backend/ai_agent_lab.db`.
- Do not read `.env`, secrets, or real credentials and do not call a real LLM,
  Embedding Provider, or network Tool.
- Browser and test flows use complete synthetic responses and temporary state.
- RAG remains non-streaming and source cards are current-session only.
- Use TDD: every production behavior follows an observed, expected RED.
- Keep routes/API wrappers thin and render answer/source/metadata as React text.
- Do not stage, commit, push, tag, switch branch, or create a worktree.

---

### Task 1: Strict RAG And Conversation API Contracts (S4)

**Files:**
- Create: `frontend/src/types/rag.ts`
- Create: `frontend/src/api/rag.ts`
- Create: `frontend/src/api/rag.test.ts`
- Modify: `frontend/src/types/conversations.ts`
- Modify: `frontend/src/api/conversations.ts`
- Modify: `frontend/src/api/conversations.test.ts`

**Interfaces:**
- Consumes: shared `createApiUrl`, `readResponseError`, `ApiMessage`, and
  `TokenUsage`.
- Produces: `queryKnowledgeBase(request)`,
  `createRagChat(request, { signal? })`, and `createConversation(request)`.

- [x] **Step 1: Write the failing RAG API contract tests**

Add complete synthetic Query and Chat resources mirroring every backend field.
Tests must verify:

```ts
await expect(queryKnowledgeBase(queryRequest)).resolves.toEqual(queryResponse);
await expect(createRagChat(chatRequest, { signal })).resolves.toEqual(chatResponse);
expect(fetchMock).toHaveBeenCalledWith(
  "http://localhost:8000/api/v1/rag/chat",
  expect.objectContaining({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chatRequest),
    signal,
  }),
);
```

Also cover safe structured error text, a fixed transport error, and fixed
invalid-success-JSON error.

- [x] **Step 2: Run the RAG API tests and verify RED**

Run:

```powershell
npm test -- --run src/api/rag.test.ts
```

Expected: collection fails because `./rag` and `../types/rag` do not exist.

- [x] **Step 3: Add exact RAG types and minimal wrappers**

The public shapes are:

```ts
export type RagRetrievalRequest = {
  knowledge_base_id: string;
  query: string;
  top_k?: number;
  score_threshold?: number | null;
};

export type RagChatRequest = RagRetrievalRequest & {
  conversation_id: string;
  provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number | null;
};

export function queryKnowledgeBase(
  request: RagRetrievalRequest,
): Promise<RagQueryResponse>;

export function createRagChat(
  request: RagChatRequest,
  options?: { signal?: AbortSignal },
): Promise<RagChatResponse>;
```

Use one private JSON request helper with fixed messages. Do not log or include
raw response bodies in frontend errors.

- [x] **Step 4: Verify RAG API GREEN**

Run the Task 1 RAG API command. Expected: all RAG API tests pass.

- [x] **Step 5: Write the failing Conversation create test**

Extend the existing test file with:

```ts
await expect(
  createConversation({
    title: "RAG · Engineering notes",
    default_provider: "mock",
    default_model: "mock-model",
  }),
).resolves.toEqual(createdConversation);
```

Assert `POST /conversations` and the exact JSON body.

- [x] **Step 6: Run the Conversation API test and verify RED**

Run:

```powershell
npm test -- --run src/api/conversations.test.ts
```

Expected: import/type failure because `createConversation` and
`ConversationCreate` do not exist.

- [x] **Step 7: Add the minimal typed Conversation create wrapper**

Add:

```ts
export type ConversationCreate = {
  title?: string;
  default_provider?: string | null;
  default_model?: string | null;
};
```

The wrapper uses the existing shared JSON helpers and does not change list or
message behavior.

- [x] **Step 8: Verify complete Task 1 GREEN**

Run both focused API test files and `npm run typecheck`.

---

### Task 2: Focused RAG Store And Request Ownership (S4)

**Files:**
- Create: `frontend/src/stores/ragStore.ts`
- Create: `frontend/src/stores/ragStore.test.ts`

**Interfaces:**
- Consumes: RAG Chat, Conversation create, and Models API functions.
- Produces: `createRagStore()`, `useRagStore`, `initialize()`,
  `setKnowledgeBase(id, name)`, `selectModel(provider, model)`, `sendQuery()`,
  `newChat()`, and current-session `turns`.

- [x] **Step 1: Write failing store tests for initialization and first turn**

Use injected complete dependency fakes, not module mocks. Verify:

```ts
await store.getState().initialize();
store.getState().setKnowledgeBase(KB_ID, "Engineering notes");
await expect(store.getState().sendQuery("What changed?")).resolves.toBe(true);

expect(createConversation).toHaveBeenCalledWith({
  title: "RAG · Engineering notes",
  default_provider: "mock",
  default_model: "mock-model",
});
expect(chat).toHaveBeenCalledWith(
  expect.objectContaining({
    conversation_id: CONVERSATION_ID,
    knowledge_base_id: KB_ID,
    query: "What changed?",
    top_k: 5,
    temperature: 0.2,
  }),
  expect.objectContaining({ signal: expect.any(AbortSignal) }),
);
expect(store.getState().turns).toEqual([expectedTurn]);
```

Also verify model fallback, no-model workspace state, error preservation, a
second turn reusing the Conversation, `newChat()`, and KB switch reset.

- [x] **Step 2: Run store tests and verify RED**

Run:

```powershell
npm test -- --run src/stores/ragStore.test.ts
```

Expected: collection fails because the store module does not exist.

- [x] **Step 3: Implement the minimal store state machine**

Use these bounded states:

```ts
type RagWorkspaceStatus = "idle" | "loading" | "ready" | "error";
type RagRequestStatus = "idle" | "sending" | "error";

export type RagStore = {
  models: ModelOption[];
  selectedKnowledgeBaseId: string | null;
  selectedKnowledgeBaseName: string | null;
  selectedProvider: string | null;
  selectedModel: string | null;
  conversationId: string | null;
  turns: RagTurn[];
  workspaceStatus: RagWorkspaceStatus;
  requestStatus: RagRequestStatus;
  workspaceError: string | null;
  requestError: string | null;
  initialize: () => Promise<void>;
  setKnowledgeBase: (id: string, name: string) => void;
  selectModel: (provider: string, model: string) => void;
  sendQuery: (query: string) => Promise<boolean>;
  newChat: () => void;
};
```

Conversation creation and RAG Chat share one request ownership token. Store a
new Conversation ID only while the request still owns state.

- [x] **Step 4: Add failing trust-boundary and stale-response tests**

Cover mismatched response Conversation, metadata Knowledge Base, per-source
Knowledge Base, non-contiguous source indices, used-source count, KB switch
during a pending request, and late failure after `newChat()`.

- [x] **Step 5: Run the new tests and verify expected RED failures**

Expected: invalid ownership is currently accepted or stale state is applied.

- [x] **Step 6: Add fail-closed validation and invalidation**

Use fixed messages such as:

```text
RAG API returned inconsistent response ownership
RAG API returned inconsistent source metadata
```

Never interpolate IDs, source content, or backend diagnostics into those
messages.

- [x] **Step 7: Verify store GREEN and adjacent API tests**

Run store, RAG API, Models API, and Conversation API tests together.

---

### Task 3: RAG Chat Page Inside Knowledge Workspace (S5)

**Files:**
- Create: `frontend/src/pages/RagChatPage.tsx`
- Create: `frontend/src/pages/RagChatPage.test.tsx`
- Create: `frontend/src/components/rag/RagComposer.tsx`
- Modify: `frontend/src/pages/KnowledgeBasePage.tsx`
- Modify: `frontend/src/pages/KnowledgeBasePage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: selected `KnowledgeBase`, `useRagStore`, and existing
  `ModelSelector`.
- Produces: accessible Documents/RAG Chat tabs and a non-streaming question
  flow with loading/error/empty/result states.

- [x] **Step 1: Write failing Knowledge tab integration tests**

Verify the existing document flow is the default, the RAG tab renders the
selected Knowledge Base name, changing the selected Knowledge Base updates the
RAG owner, and returning to Documents preserves current upload state.

- [x] **Step 2: Run Knowledge page tests and verify RED**

Expected: no tablist or RAG Chat view exists.

- [x] **Step 3: Add the minimal tab shell and page boundary**

Use semantic `role="tablist"`, `role="tab"`, `aria-selected`, and one visible
tabpanel. Keep Knowledge Base creation/list outside the tabpanel.

- [x] **Step 4: Write failing RagChatPage DOM tests**

Render the real page/components with a test store. Cover model-loading, model
error/retry, empty prompt, sending state, success, safe request error with draft
preservation, New RAG chat, and no-model state.

- [x] **Step 5: Run RagChatPage tests and verify RED**

Expected: the page and composer imports are missing.

- [x] **Step 6: Implement the minimal page and composer**

The composer contract is:

```ts
type RagComposerProps = {
  busy: boolean;
  disabled: boolean;
  error: string | null;
  onSend: (query: string) => Promise<boolean>;
};
```

It trims the question and clears only when `onSend()` resolves `true`.
`RagChatPage` calls `setKnowledgeBase(id, name)` in an effect and never logs
questions or responses.

- [x] **Step 7: Verify S5 GREEN**

Run the Knowledge page, RAG page, store, and API tests plus TypeScript checking.

---

### Task 4: Answer And Source Citation Components (S6)

**Files:**
- Create: `frontend/src/components/rag/RagAnswerPanel.tsx`
- Create: `frontend/src/components/rag/RagAnswerPanel.test.tsx`
- Create: `frontend/src/components/rag/SourceCitationList.tsx`
- Create: `frontend/src/components/rag/RagSourceCard.tsx`
- Create: `frontend/src/components/rag/SourceCitationList.test.tsx`
- Modify: `frontend/src/pages/RagChatPage.tsx`
- Modify: `frontend/src/pages/RagChatPage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: complete `RagTurn` and `RagSource` values.
- Produces: ordered answer/source UI with exact traceable identifiers.

- [x] **Step 1: Write failing source-list component tests**

Use a complete source response. Assert filename, exact content, formatted score,
heading/page, document/chunk IDs, chunk index, metadata keys/values, stable
source order, and the explicit zero-source state.

Add an XSS regression where content/metadata contain `<img onerror=...>` and
assert it appears only as text with no `img` element.

- [x] **Step 2: Run source tests and verify RED**

Expected: source component imports are missing.

- [x] **Step 3: Implement source list/card with bounded metadata formatting**

Sort nothing: render the backend array in its existing order. Format scores to
four decimal places. Format scalar metadata directly and nested metadata with
stable JSON; truncate only the visual metadata value at 2,000 characters with
an ellipsis.

- [x] **Step 4: Write failing answer-panel tests**

Assert answer text, RAG Query ID, LLM Call ID, Conversation ID, strategy, Top-K,
result/source counts, context characters, resolved provider/model, and source
delegation.

- [x] **Step 5: Run answer tests and verify RED**

Expected: answer panel import is missing.

- [x] **Step 6: Implement and integrate the answer panel**

Render one answer panel per current-session turn. Keep answer/content as plain
text with CSS `white-space: pre-wrap`; do not add a Markdown/HTML renderer.

- [x] **Step 7: Verify S6 GREEN and full focused frontend set**

Run all RAG component/page/store/API tests and existing Knowledge tests.

---

### Task 5: Documentation, Browser Acceptance, And Final Gates

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs/23-naive-rag.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this implementation plan as checkpoints complete

**Interfaces:**
- Consumes: the final tested behavior and fresh verification evidence.
- Produces: current, non-overclaiming user and architecture documentation.

- [x] **Step 1: Update exact behavior and limitations**

Document typed wrappers/store, Knowledge tabs, dedicated RAG Conversation,
answer/source fields, audit IDs, non-streaming behavior, current-session-only
source history, and the still backend-only Agent knowledge Tool.

- [x] **Step 2: Run complete frontend and backend verification**

Run:

```powershell
npm test -- --run
npm run typecheck
npm run build
```

Run complete backend pytest from a system temporary working directory with the
backend source on `PYTHONPATH`, plus `pip check`. Never make the protected user
database discoverable as the working database.

- [x] **Step 3: Run local mocked browser smoke**

Intercept local health, Knowledge Base list, Models, Conversation create, and
RAG Chat responses. Verify desktop and narrow viewports: select RAG Chat, ask a
question, see answer/source/score/metadata/audit IDs, start a new RAG chat, and
observe zero console errors. Remove every synthetic fixture and browser artifact
after inspection.

- [x] **Step 4: Run final documentation and repository gates**

Check all Markdown local links/images, `git diff --check`, exact changed-path
allowlist, staged paths, branch/refs/tags, high-confidence secrets/private-key
headers, executable later-Plan runtime, network Tool runtime, and tracked/
untracked artifacts. Run Compose config; report Docker/Qdrant runtime truthfully
if the daemon remains unavailable.

- [x] **Step 5: Codex self-review and affected re-verification**

Classify every finding as must-fix, fix later, recorded limitation, or not
applicable. Fix must-fix findings through RED/GREEN and re-run affected checks.
Confirm no S4～S6 code adds streaming, Advanced RAG, backend APIs, or Plan 4+.
