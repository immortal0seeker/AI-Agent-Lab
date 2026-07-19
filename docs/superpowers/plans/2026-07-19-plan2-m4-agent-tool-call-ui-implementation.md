# Plan 2 M4 Agent Tool Call UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `P2-M4-S4～S6` as a dedicated, traceable Agent workspace that calls the existing synchronous Agent API and displays final answers plus ToolCall audit details without regressing Plan 1 Chat.

**Architecture:** `App` switches between Chat and Agent with lightweight URL helpers. `AgentPage` owns Agent API orchestration, while focused form, run panel, timeline, and card components own presentation. The frontend mirrors the existing backend contract and preserves safe error request IDs; no backend or later-Plan runtime changes are allowed.

**Tech Stack:** React 19, TypeScript 5.9, Zustand only for the existing Chat store, Vite 7, Vitest 4, lucide-react, FastAPI mock responses, Playwright browser smoke.

## Global Constraints

- Work only on `P2-M4-S4～S6`; do not begin M5 or Plan 3.
- Only models with `supports_tools=true` may be selected for Agent tasks.
- Use only plural `/api/v1/agents/runs`; do not add or call a singular alias.
- Treat HTTP 201 with `status="failed"` as a persisted Agent result, not a transport error.
- Preserve AgentRun, Conversation, ToolCall database, Provider ToolCall, and error Request IDs.
- Do not call a real Provider, paid API, network Tool, or read a real secret/user database.
- Do not add React Router, a new state library, Agent polling, streaming, cancellation, resume, retry, or AgentRun list UI.
- Keep Chat/Streaming/conversation behavior unchanged except for the new workspace navigation.
- Use Chinese only for comments that explain non-obvious intent; do not add redundant comments.
- Do not stage, commit, push, tag, or create/switch branches; the user commits manually.

## File Map

**Create:**

- `frontend/src/types/agent.ts` — public Agent API TypeScript contracts.
- `frontend/src/api/agent.ts` — Agent POST/GET wrappers and safe structured API error.
- `frontend/src/api/agent.test.ts` — request, response, and error contract tests.
- `frontend/src/utils/agentUrl.ts` — workspace/run URL parsing and mutation.
- `frontend/src/utils/agentUrl.test.ts` — URL preservation and UUID tests.
- `frontend/src/components/agent/toolCallView.ts` — deterministic formatting, summary, and status helpers.
- `frontend/src/components/agent/toolCallView.test.ts` — pure helper tests.
- `frontend/src/components/agent/ToolCallCard.tsx` — one ToolCall audit card.
- `frontend/src/components/agent/ToolCallTimeline.tsx` — ordered ToolCall collection and empty state.
- `frontend/src/components/agent/ToolCallTimeline.test.tsx` — component states and safe rendering.
- `frontend/src/components/agent/AgentTaskForm.tsx` — controlled task/model form.
- `frontend/src/components/agent/AgentTaskForm.test.tsx` — form eligibility and control tests.
- `frontend/src/components/agent/AgentRunPanel.tsx` — all Agent result states.
- `frontend/src/components/agent/AgentRunPanel.test.tsx` — loading/empty/error/result tests.
- `frontend/src/pages/AgentPage.tsx` — model/health/run loading and submit orchestration.
- `frontend/src/pages/AgentPage.test.tsx` — tools-capable model and pure page error helper tests.

**Modify:**

- `frontend/src/App.tsx` — URL-backed Chat/Agent workspace switch.
- `frontend/src/App.test.tsx` — default and URL-restored workspace tests.
- `frontend/src/components/WorkspaceSidebar.tsx` — discriminated Chat/Agent navigation props.
- `frontend/src/pages/ChatPage.tsx` — pass workspace navigation without changing Chat state.
- `frontend/src/pages/ChatPage.test.tsx` — preserve existing states and assert Chat navigation.
- `frontend/src/styles.css` — quiet, responsive Agent workspace and ToolCall styling.
- `README.md`, `README_CN.md`, `CHANGELOG.md` — current user-visible capability and limitation.
- `docs/00-project-overview.md`, `docs/01-architecture.md`, `docs/12-agent-api.md` — M4 S6 architecture/UI facts.
- `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md` — Batch 11 acceptance evidence and next batch.
- `docs/superpowers/plans/2026-07-19-plan2-m4-agent-tool-call-ui-implementation.md` — check off executed steps.

---

### Task 1: Agent Types, API Wrapper, and URL Contract

**Files:**

- Create: `frontend/src/types/agent.ts`
- Create: `frontend/src/api/agent.ts`
- Create: `frontend/src/api/agent.test.ts`
- Create: `frontend/src/utils/agentUrl.ts`
- Create: `frontend/src/utils/agentUrl.test.ts`

**Interfaces:**

- Produces: `AgentRunStatus`, `ToolCallStatus`, `ToolResult`, `AgentRunCreate`, `AgentRun`, `ToolCall`, `AgentRunExecution`.
- Produces: `AgentApiError`, `createAgentRun(request)`, `fetchAgentRun(runId)`, `fetchAgentToolCalls(runId)`.
- Produces: `WorkspaceView`, `readWorkspace(search)`, `readAgentRunId(search)`, `buildWorkspaceUrl(href, workspace)`, `buildAgentRunUrl(href, runId)`.

- [x] **Step 1: Write failing Agent API tests**

Create `frontend/src/api/agent.test.ts` with representative payloads and these exact assertions:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AgentApiError,
  createAgentRun,
  fetchAgentRun,
  fetchAgentToolCalls,
} from "./agent";
import type { AgentRunExecution } from "../types/agent";

const execution: AgentRunExecution = {
  id: "00000000-0000-0000-0000-000000000101",
  conversation_id: "00000000-0000-0000-0000-000000000102",
  user_message_id: "00000000-0000-0000-0000-000000000103",
  status: "completed",
  goal: "Read README.md",
  final_answer: "A local AI engineering workspace.",
  error: null,
  started_at: "2026-07-19T12:00:00",
  ended_at: "2026-07-19T12:00:01",
  latency_ms: 1000,
  created_at: "2026-07-19T12:00:00",
  tool_calls: [],
};

afterEach(() => vi.unstubAllGlobals());

describe("Agent API", () => {
  it("creates an Agent run through the plural endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(execution), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createAgentRun({
        provider: "provider-a",
        model: "tools-model",
        input: "Read README.md",
      }),
    ).resolves.toEqual(execution);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/agents/runs",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      provider: "provider-a",
      model: "tools-model",
      input: "Read README.md",
    });
  });

  it("queries one run and its ToolCalls", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(execution)))
      .mockResolvedValueOnce(new Response(JSON.stringify([])));
    vi.stubGlobal("fetch", fetchMock);

    await fetchAgentRun(execution.id);
    await fetchAgentToolCalls(execution.id);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `http://localhost:8000/api/v1/agents/runs/${execution.id}`,
      `http://localhost:8000/api/v1/agents/runs/${execution.id}/tool-calls`,
    ]);
  });

  it("preserves safe structured error fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "provider_unavailable",
              message: "The requested provider is unavailable",
              request_id: "request-agent-1",
            },
          }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const error = await createAgentRun({
      provider: "provider-a",
      model: "tools-model",
      input: "Read README.md",
    }).catch((reason: unknown) => reason);

    expect(error).toBeInstanceOf(AgentApiError);
    expect(error).toMatchObject({
      message: "The requested provider is unavailable",
      code: "provider_unavailable",
      requestId: "request-agent-1",
      status: 503,
    });
  });
});
```

- [x] **Step 2: Run API tests to verify RED**

Run: `npm test -- src/api/agent.test.ts`

Expected: FAIL during import because `./agent` and `../types/agent` do not exist.

- [x] **Step 3: Add exact public TypeScript contracts**

Create `frontend/src/types/agent.ts`:

```ts
export type AgentRunStatus =
  | "created"
  | "running"
  | "waiting_tool"
  | "completed"
  | "failed"
  | "cancelled";

export type ToolCallStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "timeout"
  | "blocked";

export type ToolResult = {
  tool_name: string;
  success: boolean;
  content: string;
  data: Record<string, unknown> | null;
  error: string | null;
  metadata: Record<string, unknown>;
};

export type AgentRunCreate = {
  conversation_id?: string | null;
  provider: string;
  model: string;
  input: string;
  temperature?: number;
  max_tokens?: number | null;
  max_steps?: number;
};

export type AgentRun = {
  id: string;
  conversation_id: string;
  user_message_id: string | null;
  status: AgentRunStatus;
  goal: string;
  final_answer: string | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type ToolCall = {
  id: string;
  tool_call_id: string;
  agent_run_id: string;
  conversation_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: ToolResult | null;
  status: ToolCallStatus;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type AgentRunExecution = AgentRun & { tool_calls: ToolCall[] };
```

- [x] **Step 4: Implement the minimal Agent API wrapper**

Create `frontend/src/api/agent.ts` around `createApiUrl(API_BASE_URL, path)`. The implementation must:

```ts
export class AgentApiError extends Error {
  readonly code: string | null;
  readonly requestId: string | null;
  readonly status: number | null;

  constructor(
    message: string,
    options: { code?: string | null; requestId?: string | null; status?: number | null } = {},
  ) {
    super(message);
    this.name = "AgentApiError";
    this.code = options.code ?? null;
    this.requestId = options.requestId ?? null;
    this.status = options.status ?? null;
  }
}

export function createAgentRun(request: AgentRunCreate): Promise<AgentRunExecution>;
export function fetchAgentRun(runId: string): Promise<AgentRun>;
export function fetchAgentToolCalls(runId: string): Promise<ToolCall[]>;
```

Use one private `requestAgentJson<T>()`. On non-2xx, parse only `error.code`, `error.message`, and `error.request_id`; use `Request failed with status N` for malformed/non-JSON failures. On a successful non-JSON body, throw `AgentApiError("Agent API returned invalid JSON", { status })`. Do not copy arbitrary response text into the error.

- [x] **Step 5: Run API tests to verify GREEN**

Run: `npm test -- src/api/agent.test.ts`

Expected: all Agent API tests PASS.

- [x] **Step 6: Write failing URL helper tests**

Create `frontend/src/utils/agentUrl.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import {
  buildAgentRunUrl,
  buildWorkspaceUrl,
  readAgentRunId,
  readWorkspace,
} from "./agentUrl";

const RUN_ID = "00000000-0000-0000-0000-000000000101";

describe("Agent workspace URL helpers", () => {
  it("defaults to Chat and recognizes only Agent workspace", () => {
    expect(readWorkspace("")).toBe("chat");
    expect(readWorkspace("?workspace=agent")).toBe("agent");
    expect(readWorkspace("?workspace=unknown")).toBe("chat");
  });

  it("accepts only a UUID AgentRun ID", () => {
    expect(readAgentRunId(`?run=${RUN_ID}`)).toBe(RUN_ID);
    expect(readAgentRunId("?run=not-a-uuid")).toBeNull();
  });

  it("switches workspace while preserving conversation, run, and hash", () => {
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?conversation=chat-1&run=${RUN_ID}#result`,
        "agent",
      ),
    ).toBe(
      `http://localhost:5173/?conversation=chat-1&run=${RUN_ID}&workspace=agent#result`,
    );
  });

  it("sets and clears only the AgentRun query", () => {
    const url = buildAgentRunUrl(
      "http://localhost:5173/?workspace=agent&conversation=chat-1",
      RUN_ID,
    );
    expect(url).toBe(
      `http://localhost:5173/?workspace=agent&conversation=chat-1&run=${RUN_ID}`,
    );
    expect(buildAgentRunUrl(url, null)).toBe(
      "http://localhost:5173/?workspace=agent&conversation=chat-1",
    );
  });
});
```

- [x] **Step 7: Run URL tests to verify RED**

Run: `npm test -- src/utils/agentUrl.test.ts`

Expected: FAIL during import because `agentUrl.ts` does not exist.

- [x] **Step 8: Implement URL helpers and verify GREEN**

Create `frontend/src/utils/agentUrl.ts` with the same case-insensitive UUID pattern as `conversationUrl.ts`. `buildWorkspaceUrl()` must delete `workspace` for Chat and set `workspace=agent` for Agent. `buildAgentRunUrl()` must only set/delete `run`.

Run: `npm test -- src/utils/agentUrl.test.ts src/api/agent.test.ts`

Expected: both files PASS.

- [x] **Step 9: Task checkpoint**

Run: `npm run typecheck`

Expected: PASS. Review `git diff -- frontend/src/types/agent.ts frontend/src/api/agent.ts frontend/src/utils/agentUrl.ts` and do not stage or commit.

---

### Task 2: ToolCall Formatting, Card, and Timeline

**Files:**

- Create: `frontend/src/components/agent/toolCallView.ts`
- Create: `frontend/src/components/agent/toolCallView.test.ts`
- Create: `frontend/src/components/agent/ToolCallCard.tsx`
- Create: `frontend/src/components/agent/ToolCallTimeline.tsx`
- Create: `frontend/src/components/agent/ToolCallTimeline.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**

- Consumes: `ToolCall`, `ToolCallStatus`, and `ToolResult` from Task 1.
- Produces: `toolCallTone(status)`, `formatLatency(ms)`, `formatJson(value)`, `summarizeText(text, limit?)`, `toolResultSections(result)`.
- Produces: `<ToolCallCard toolCall />` and `<ToolCallTimeline toolCalls />`.

- [x] **Step 1: Write failing pure helper tests**

Create tests that assert:

```ts
expect(toolCallTone("pending")).toBe("pending");
expect(toolCallTone("running")).toBe("pending");
expect(toolCallTone("success")).toBe("success");
expect(toolCallTone("failed")).toBe("error");
expect(toolCallTone("timeout")).toBe("error");
expect(toolCallTone("blocked")).toBe("error");
expect(formatLatency(null)).toBe("Not recorded");
expect(formatLatency(23)).toBe("23 ms");
expect(formatLatency(1200)).toBe("1.20 s");
expect(formatJson({ z: 1, nested: { b: 2, a: 1 }, a: 0 })).toBe(
  '{\n  "a": 0,\n  "nested": {\n    "a": 1,\n    "b": 2\n  },\n  "z": 1\n}',
);
expect(summarizeText("123456", 5)).toBe("1234…");
```

Also assert that successful content, data, and metadata become separate result sections and a failed `ToolResult.error` becomes an error section.

- [x] **Step 2: Verify helper RED**

Run: `npm test -- src/components/agent/toolCallView.test.ts`

Expected: FAIL because `toolCallView.ts` does not exist.

- [x] **Step 3: Implement deterministic bounded formatting**

Implement recursive key sorting for JSON objects, retain array order, render `Not recorded` for null latency, and default summaries to 600 characters. `toolResultSections()` returns only non-empty sections and never mutates the ToolResult.

- [x] **Step 4: Verify helper GREEN**

Run: `npm test -- src/components/agent/toolCallView.test.ts`

Expected: PASS.

- [x] **Step 5: Write failing timeline component tests**

Use `renderToStaticMarkup` to cover:

```tsx
expect(renderToStaticMarkup(<ToolCallTimeline toolCalls={[]} />)).toContain(
  "This run did not call any tools.",
);

const html = renderToStaticMarkup(
  <ToolCallTimeline toolCalls={[pendingCall, successCall, failedCall]} />,
);
expect(html).toContain("read_file");
expect(html).toContain("list_dir");
expect(html).toContain("Pending");
expect(html).toContain("Success");
expect(html).toContain("Failed");
expect(html).toContain("Provider call ID");
expect(html).toContain("Database ID");
expect(html).toContain('&quot;&lt;script&gt;&quot;');
expect(html.indexOf(pendingCall.id)).toBeLessThan(html.indexOf(successCall.id));
```

Add individual cases for `running`, `timeout`, and `blocked`; assert each uses the exact backend vocabulary and error tone class.

- [x] **Step 6: Verify component RED**

Run: `npm test -- src/components/agent/ToolCallTimeline.test.tsx`

Expected: FAIL because the components do not exist.

- [x] **Step 7: Implement ToolCallCard and ToolCallTimeline**

`ToolCallCard` must use semantic `<article>`, a visible status label, `<code>` for IDs, `<pre>` for arguments/result JSON, and escaped React text. It must prefer `toolCall.error`, then failed `result.error`, for the visible error. `ToolCallTimeline` maps in input order and uses `toolCall.id` as key.

Use these exact status labels:

```ts
const STATUS_LABELS: Record<ToolCallStatus, string> = {
  pending: "Pending",
  running: "Running",
  success: "Success",
  failed: "Failed",
  timeout: "Timeout",
  blocked: "Blocked",
};
```

- [x] **Step 8: Add quiet responsive styles and verify GREEN**

Add `.tool-call-timeline`, `.tool-call-card`, `.tool-call-status--pending|success|error`, `.tool-call-grid`, `.tool-call-json`, and `.trace-id` styles. IDs/JSON must use `overflow-wrap:anywhere` and `white-space:pre-wrap`; colors must not be the only status signal.

Run: `npm test -- src/components/agent/toolCallView.test.ts src/components/agent/ToolCallTimeline.test.tsx`

Expected: both files PASS.

- [x] **Step 9: Task checkpoint**

Run: `npm run typecheck`

Expected: PASS. Review only Task 2 paths and do not stage or commit.

---

### Task 3: Agent Task Form and Run Panel States

**Files:**

- Create: `frontend/src/components/agent/AgentTaskForm.tsx`
- Create: `frontend/src/components/agent/AgentTaskForm.test.tsx`
- Create: `frontend/src/components/agent/AgentRunPanel.tsx`
- Create: `frontend/src/components/agent/AgentRunPanel.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**

- Consumes: `ModelOption`, `AgentRunExecution`, `AgentApiError`, `ToolCallTimeline`.
- Produces: controlled `<AgentTaskForm models provider model input busy disabledReason hasRun ... />`.
- Produces: `AgentRunViewState` and `<AgentRunPanel state />`.

- [x] **Step 1: Write failing AgentRunPanel tests**

Define fixtures for completed and structured failed executions. Assert static markup for:

```tsx
{ status: "loading", message: "Running Agent task..." }
{ status: "empty" }
{ status: "no-models" }
{ status: "error", message: "The requested provider is unavailable", requestId: "request-1" }
{ status: "result", run: completedExecution }
{ status: "result", run: failedExecution }
```

The completed case must contain final answer, Run ID, Conversation ID, duration, and empty ToolCall message. The failed case must contain `Run failed`, the persisted Run ID, and safe run error. The transport error must show Request ID; the structured failed result must not label its run error as a Request ID.

- [x] **Step 2: Verify panel RED**

Run: `npm test -- src/components/agent/AgentRunPanel.test.tsx`

Expected: FAIL because `AgentRunPanel.tsx` does not exist.

- [x] **Step 3: Implement AgentRunPanel**

Use this union exactly:

```ts
export type AgentRunViewState =
  | { status: "loading"; message: string }
  | { status: "empty" }
  | { status: "no-models" }
  | { status: "error"; message: string; requestId: string | null }
  | { status: "result"; run: AgentRunExecution };
```

Render terminal `completed` and `failed` distinctly, but render all backend status values as readable badges so restored non-terminal rows remain inspectable. Do not infer missing latency or timestamps.

- [x] **Step 4: Verify panel GREEN**

Run: `npm test -- src/components/agent/AgentRunPanel.test.tsx`

Expected: PASS.

- [x] **Step 5: Write failing AgentTaskForm tests and verify RED**

Use `renderToStaticMarkup` to prove a valid tools model/task is enabled, blank input is disabled, model failure reason disables submission, `New task` is conditional, and cancel/retry controls do not exist.

Run: `npm test -- src/components/agent/AgentTaskForm.test.tsx`

Expected: FAIL because `AgentTaskForm.tsx` does not exist.

- [x] **Step 6: Add AgentTaskForm with controlled state**

Implement props with exact responsibilities:

```ts
type AgentTaskFormProps = {
  models: ModelOption[];
  provider: string | null;
  model: string | null;
  input: string;
  busy: boolean;
  disabledReason: string | null;
  hasRun: boolean;
  onSelectModel: (provider: string, model: string) => void;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onNewTask: () => void;
};
```

The submit button is enabled only when trim(input) is non-empty, provider/model are set, not busy, and `disabledReason` is null. Use the existing `ModelSelector`. The form shows `disabledReason` in text, labels the textarea `Agent task`, and does not expose cancel/retry controls.

- [x] **Step 7: Add form and result styles**

Add `.agent-workspace`, `.agent-header`, `.agent-content`, `.agent-task-form`, `.agent-actions`, `.agent-run-panel`, `.agent-run-meta`, `.agent-answer`, `.agent-state`, and mobile rules. Keep content dense, quiet, keyboard focus visible, and long IDs wrapping.

- [x] **Step 8: Task checkpoint**

Run: `npm test -- src/components/agent/AgentTaskForm.test.tsx src/components/agent/AgentRunPanel.test.tsx src/components/agent/ToolCallTimeline.test.tsx`

Run: `npm run typecheck`

Expected: all PASS. Do not stage or commit.

---

### Task 4: AgentPage, Sidebar Navigation, and Chat Regression

**Files:**

- Create: `frontend/src/pages/AgentPage.tsx`
- Create: `frontend/src/pages/AgentPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Modify: `frontend/src/components/WorkspaceSidebar.tsx`
- Modify: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/pages/ChatPage.test.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**

- Consumes: all Tasks 1–3 interfaces and existing `fetchHealth()`, `fetchModels()`, `ModelOption`, `WorkspaceSidebar`.
- Produces: `toAgentPageError(error)`, `toolsCapableModels(models)`, and `<AgentPage onSelectWorkspace />`.
- Changes: `<ChatPage onSelectWorkspace />`; `<WorkspaceSidebar>` becomes a discriminated Chat/Agent props union.

- [x] **Step 1: Write failing page helper and navigation tests**

In `AgentPage.test.tsx`, assert:

```ts
expect(toolsCapableModels(models).map((item) => item.model)).toEqual([
  "tools-model",
]);
expect(
  toAgentPageError(
    new AgentApiError("Provider unavailable", {
      code: "provider_unavailable",
      requestId: "request-7",
      status: 503,
    }),
  ),
).toEqual({ message: "Provider unavailable", requestId: "request-7" });
expect(toAgentPageError("bad")).toEqual({
  message: "Agent request failed",
  requestId: null,
});
```

In `ChatPage.test.tsx`, pass `onSelectWorkspace={() => undefined}` and assert the ready/sidebar markup includes both `Chat` and `Agent` workspace navigation while retaining the existing loading/error assertions.

In `App.test.tsx`, render the real `App` with a minimal `window` stub and assert that an empty query renders the real Chat workspace while `?workspace=agent` renders the real Agent workspace. Do not mock either page and assert mock-only marker text.

- [x] **Step 2: Verify page/navigation RED**

Run: `npm test -- src/pages/AgentPage.test.tsx src/pages/ChatPage.test.tsx`

Expected: AgentPage import fails, ChatPage cannot yet accept/render workspace navigation, and App cannot restore the Agent workspace.

- [x] **Step 3: Refactor WorkspaceSidebar with a discriminated union**

Define shared props (`health`, `activeWorkspace`, `onSelectWorkspace`) and two variants:

```ts
type ChatSidebarProps = SharedSidebarProps & {
  activeWorkspace: "chat";
  conversations: ConversationSummary[];
  selectedConversationId: string | null;
  conversationsLoading: boolean;
  navigationDisabled: boolean;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
};

type AgentSidebarProps = SharedSidebarProps & {
  activeWorkspace: "agent";
};
```

Render two buttons with `aria-current` and call `onSelectWorkspace("chat"|"agent")`. Only the Chat variant renders New Chat, desktop/mobile conversation history, and conversation callbacks. Agent renders a short `Current task` sidebar note; it must not claim Agent history exists.

- [x] **Step 4: Pass navigation through ChatPage without changing Chat flow**

Make `onSelectWorkspace: (workspace: WorkspaceView) => void` a required `ChatPage` prop. Keep every current store selector, initialization effect, URL conversation effect, health effect, MessageList, and MessageComposer behavior unchanged. Pass the new shared sidebar props plus the existing Chat variant props.

- [x] **Step 5: Implement AgentPage controller**

Implement three independent async effects/flows:

1. Health: same safe health state semantics as Chat.
2. Models: `fetchModels()`, filter `supports_tools`, select the first tools model, and preserve a model-error separate from Run state.
3. URL Run restore: if `readAgentRunId(window.location.search)` is non-null, fetch run and ToolCalls in parallel and combine them into `AgentRunExecution`; stale/unmounted responses must not set state.

Submit behavior:

```ts
const request = {
  provider: selectedProvider,
  model: selectedModel,
  input: taskInput.trim(),
};
const result = await createAgentRun(request);
setRunState({ status: "result", run: result });
window.history.replaceState(
  null,
  "",
  buildAgentRunUrl(window.location.href, result.id),
);
```

Before awaiting, set `{status:"loading", message:"Running Agent task..."}`. On catch, use `toAgentPageError`. `newTask()` clears input, sets the appropriate empty/no-model state, and deletes only `run`. A model load error disables only new submissions; if a Run result exists, keep rendering it.

- [x] **Step 6: Implement URL-backed App switch**

`App` initializes with `readWorkspace(window.location.search)`. `selectWorkspace()` updates local state and calls `history.replaceState` with `buildWorkspaceUrl`. Render:

```tsx
return workspace === "agent" ? (
  <AgentPage onSelectWorkspace={selectWorkspace} />
) : (
  <ChatPage onSelectWorkspace={selectWorkspace} />
);
```

- [x] **Step 7: Add workspace navigation/responsive styles**

Add `.workspace-navigation`, active button, `.agent-sidebar-note`, and mobile behavior. Existing `.new-chat-button`, conversation history, and API status must remain usable at desktop and 720px breakpoint.

- [x] **Step 8: Verify page/navigation GREEN**

Run: `npm test -- src/App.test.tsx src/pages/AgentPage.test.tsx src/pages/ChatPage.test.tsx src/utils/agentUrl.test.ts`

Expected: all PASS.

- [x] **Step 9: Run focused frontend regression**

Run: `npm test -- src/api/agent.test.ts src/components/agent/toolCallView.test.ts src/components/agent/ToolCallTimeline.test.tsx src/components/agent/AgentRunPanel.test.tsx src/pages/AgentPage.test.tsx src/pages/ChatPage.test.tsx src/stores/chatStore.test.ts src/utils/agentUrl.test.ts src/utils/conversationUrl.test.ts`

Expected: all selected files PASS and existing Chat store tests remain unchanged.

- [x] **Step 10: Task checkpoint**

Run: `npm run typecheck`

Expected: PASS. Review all frontend diff for S4～S6 scope and do not stage or commit.

---

### Task 5: Browser Mock Acceptance, Documentation, and Final Verification

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/12-agent-api.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify: `docs/superpowers/plans/2026-07-19-plan2-m4-agent-tool-call-ui-implementation.md`

**Interfaces:**

- Consumes: completed frontend UI/API contract and existing backend Agent API.
- Produces: fresh automated/browser evidence, current docs, and a clean user-commit-ready diff.

- [x] **Step 1: Run complete frontend automated verification before docs**

Run: `npm run typecheck`

Run: `npm test`

Run: `npm run build`

Expected: TypeScript passes, every Vitest file/test passes, and production build succeeds without tracked build artifacts.

- [x] **Step 2: Run mocked browser acceptance without a real Provider**

Start the Vite dev server hidden. Use Playwright request interception for:

- `GET /api/v1/health` -> healthy service.
- `GET /api/v1/models` -> one normal model and one `supports_tools=true` model.
- `GET /api/v1/conversations` -> empty array for Chat regression.
- `POST /api/v1/agents/runs` -> HTTP 201 completed run with one successful `read_file` ToolCall whose arguments are `{ "path": "README.md" }` and final answer summarizes the workspace structure.

Acceptance assertions:

1. Default page is Chat and still shows its empty state.
2. Agent navigation changes URL to `workspace=agent`.
3. Only the tools-capable model appears in the Agent selector.
4. Submitting `Read README.md and summarize the project structure` shows loading, then completed status.
5. Final answer, `read_file`, arguments, success, latency, Run ID, Conversation ID, Provider call ID, and database ID are visible.
6. URL contains the returned Run UUID.
7. At a mobile viewport, no horizontal page overflow and the task/result/ToolCall remain readable.
8. Separate mocked reloads cover no tools model, structured failed 201, and HTTP error with Request ID.

Save screenshots only to a system temporary directory for visual inspection and delete them after evidence is recorded. Do not create the M5-S6 release screenshot asset early.

- [x] **Step 3: Update user-facing docs with exact current boundary**

Document these facts:

- Dedicated Agent workspace is available through the sidebar.
- It only accepts Registry models with `supports_tools=true`.
- The UI shows final answer, ToolCall arguments/status/latency/result summary/errors, and traceable IDs.
- URL `run` restores a persisted AgentRun and ToolCalls.
- Tracked example model still has `supports_tools=false`; automated acceptance is mocked and proves no live Provider connectivity.
- Agent execution remains synchronous/non-streaming with no list, polling, cancel/resume/retry, strict Tool sequence, or real Provider acceptance.
- `web_fetch` remains deferred and no later Plan capability was added.

Remove the stale `docs/12-agent-api.md` statement that no frontend Agent view exists.

- [x] **Step 4: Update the Plan 2 execution table**

Mark only:

- Batch 11 complete.
- `P2-M4-S4`, `S5`, and `S6` as `Codex (done)`.
- M4 as complete after actual evidence exists.
- Next batch exactly `P2-M5-S1～S3`.

Add an acceptance record containing actual RED/GREEN counts, full frontend/backend results, browser states, security/boundary scan, and Codex self-review classification. Do not mark M5, Plan 2 final acceptance, or v0.2.0 tag complete.

- [x] **Step 5: Run backend and package regression**

Run from `backend`: `..\.venv\Scripts\python.exe -m pytest`

Run from `backend`: `..\.venv\Scripts\python.exe -m pip check`

Expected: all backend tests PASS with only the already-known Starlette TestClient/httpx deprecation warning; pip reports no broken requirements. Do not initialize a real Provider or touch `backend/ai_agent_lab.db`.

- [x] **Step 6: Re-run final frontend verification after docs/review fixes**

Run from `frontend`:

```text
npm run typecheck
npm test
npm run build
```

Expected: all PASS.

- [x] **Step 7: Run documentation, secret, boundary, and Git checks**

Verify:

- every local Markdown link/image target exists;
- tracked/current changed text contains no real credential pattern or tracked `.env`;
- no frontend `dist`, coverage, cache, temp screenshot, or user database is tracked/changed;
- no backend model/migration/provider/tool files changed;
- no `web_fetch`, RAG, Embedding, Memory, MCP, Shell, write/delete Tool runtime surface was added;
- `git diff --check` passes;
- no staged paths exist;
- `HEAD == origin/main` remains the batch baseline until the user commits.

- [x] **Step 8: Codex self-review and fix loop**

Classify every finding as:

- must fix now;
- fix in later batch;
- record as limitation;
- not applicable with reason.

For every must-fix behavior bug, first add a failing regression test, verify RED, implement the minimal fix, and re-run focused plus complete verification. Repeat until no blocking finding remains.

- [x] **Step 9: Mark this implementation plan complete and hand off**

Change every executed checkbox in this file to `[x]`. Confirm `git status` contains only S4～S6 implementation, tests, design/plan, and necessary docs. Do not stage or commit.

Suggested user-created commit message:

```text
feat(frontend): show agent tool calls
```

Handoff conclusion must explicitly say whether M4 is complete and whether the repository may enter `P2-M5-S1～S3`.
