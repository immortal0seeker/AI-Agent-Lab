// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/agent", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/agent")>();
  return {
    ...actual,
    createAgentRun: vi.fn(),
    fetchAgentRun: vi.fn(),
    fetchAgentToolCalls: vi.fn(),
  };
});
vi.mock("../api/health", () => ({ fetchHealth: vi.fn() }));
vi.mock("../api/models", () => ({ fetchModels: vi.fn() }));

import {
  AgentApiError,
  createAgentRun,
  fetchAgentRun,
  fetchAgentToolCalls,
} from "../api/agent";
import { fetchHealth } from "../api/health";
import { fetchModels } from "../api/models";
import type { AgentRunExecution } from "../types/agent";
import AgentPage from "./AgentPage";

const runId = "00000000-0000-0000-0000-000000000101";
const conversationId = "00000000-0000-0000-0000-000000000102";
const reactTestEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT: boolean;
};
const execution: AgentRunExecution = {
  id: runId,
  conversation_id: conversationId,
  user_message_id: "00000000-0000-0000-0000-000000000103",
  status: "completed",
  goal: "Read README.md",
  final_answer: "The workspace is ready.",
  error: null,
  started_at: "2026-07-20T12:00:00",
  ended_at: "2026-07-20T12:00:01",
  latency_ms: 1000,
  created_at: "2026-07-20T12:00:00",
  tool_calls: [
    {
      id: "00000000-0000-0000-0000-000000000104",
      tool_call_id: "call-read-readme",
      agent_run_id: runId,
      conversation_id: conversationId,
      tool_name: "read_file",
      sequence_index: 1,
      arguments: { path: "README.md" },
      result: {
        tool_name: "read_file",
        success: true,
        content: "AI Agent Lab",
        data: null,
        error: null,
        metadata: { path: "README.md" },
      },
      status: "success",
      error: null,
      started_at: "2026-07-20T12:00:00",
      ended_at: "2026-07-20T12:00:00.010000",
      latency_ms: 10,
      created_at: "2026-07-20T12:00:00",
    },
  ],
};

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

async function flushEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

function mountPage(): { container: HTMLDivElement; root: Root } {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => {
    root.render(<AgentPage onSelectWorkspace={vi.fn()} />);
  });
  return { container, root };
}

async function enterTaskAndSubmit(container: HTMLElement): Promise<void> {
  const textarea = container.querySelector("textarea");
  const form = container.querySelector("form");
  if (!(textarea instanceof HTMLTextAreaElement) || form === null) {
    throw new Error("Agent form is missing");
  }
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      "value",
    )?.set;
    setter?.call(textarea, "Read README.md");
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => {
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await Promise.resolve();
  });
}

beforeEach(() => {
  reactTestEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
  window.history.replaceState(null, "", "/?workspace=agent");
  window.sessionStorage.clear();
  vi.mocked(fetchHealth).mockResolvedValue({
    status: "ok",
    service: "AI Agent Lab Backend",
  });
  vi.mocked(fetchModels).mockResolvedValue([
    {
      provider: "mock",
      model: "tools-model",
      display_name: "Tools Model",
      supports_streaming: false,
      supports_tools: true,
      supports_json: false,
      input_price_per_1m: null,
      output_price_per_1m: null,
    },
  ]);
  vi.mocked(createAgentRun).mockReset();
  vi.mocked(fetchAgentRun).mockReset();
  vi.mocked(fetchAgentToolCalls).mockReset();
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("AgentPage mounted async flows", () => {
  it("loads a Tool-capable model and submits a traceable run", async () => {
    vi.mocked(createAgentRun).mockResolvedValue(execution);
    const { container, root } = mountPage();
    await flushEffects();

    const textarea = container.querySelector("textarea");
    expect(textarea).toBeInstanceOf(HTMLTextAreaElement);
    expect((textarea as HTMLTextAreaElement).disabled).toBe(false);

    await enterTaskAndSubmit(container);
    await flushEffects();

    expect(container.textContent).toContain("The workspace is ready.");
    expect(window.location.search).toContain(`run=${runId}`);
    expect(window.sessionStorage.getItem("ai-agent-lab:last-agent-run-id")).toBe(
      runId,
    );
    act(() => root.unmount());
  });

  it("renders a structured failed run returned with HTTP 201", async () => {
    vi.mocked(createAgentRun).mockResolvedValue({
      ...execution,
      status: "failed",
      final_answer: null,
      error: "Tool call budget exceeded",
      tool_calls: [],
    });
    const { container, root } = mountPage();
    await flushEffects();

    await enterTaskAndSubmit(container);
    await flushEffects();

    expect(container.textContent).toContain("Tool call budget exceeded");
    expect(container.textContent).toContain("Failed");
    expect(window.location.search).toContain(`run=${runId}`);
    act(() => root.unmount());
  });

  it("restores an explicit URL run and its ordered ToolCalls", async () => {
    window.history.replaceState(
      null,
      "",
      `/?workspace=agent&run=${runId}`,
    );
    const { tool_calls: toolCalls, ...run } = execution;
    vi.mocked(fetchAgentRun).mockResolvedValue(run);
    vi.mocked(fetchAgentToolCalls).mockResolvedValue(toolCalls);

    const { container, root } = mountPage();
    await flushEffects();

    expect(fetchAgentRun).toHaveBeenCalledWith(runId);
    expect(fetchAgentToolCalls).toHaveBeenCalledWith(runId);
    expect(container.textContent).toContain("Tool Call ID");
    expect(container.textContent).toContain("call-read-readme");
    act(() => root.unmount());
  });

  it("recovers a run completed after leaving without mutating the Chat URL", async () => {
    const pending = deferred<AgentRunExecution>();
    vi.mocked(createAgentRun).mockReturnValue(pending.promise);
    const first = mountPage();
    await flushEffects();
    await enterTaskAndSubmit(first.container);

    window.history.replaceState(null, "", "/");
    act(() => first.root.unmount());
    await act(async () => {
      pending.resolve(execution);
      await pending.promise;
    });

    expect(window.location.search).toBe("");
    expect(window.sessionStorage.getItem("ai-agent-lab:last-agent-run-id")).toBe(
      runId,
    );

    window.history.replaceState(null, "", "/?workspace=agent");
    const { tool_calls: toolCalls, ...run } = execution;
    vi.mocked(fetchAgentRun).mockResolvedValue(run);
    vi.mocked(fetchAgentToolCalls).mockResolvedValue(toolCalls);
    const second = mountPage();
    await flushEffects();

    expect(fetchAgentRun).toHaveBeenCalledWith(runId);
    expect(second.container.textContent).toContain("The workspace is ready.");
    act(() => second.root.unmount());
  });

  it("renders model and transport failures without unsafe details", async () => {
    vi.mocked(fetchModels).mockRejectedValueOnce(
      new Error("Unable to load tools-capable models"),
    );
    const modelFailure = mountPage();
    await flushEffects();
    expect(modelFailure.container.textContent).toContain(
      "Unable to load tools-capable models",
    );
    act(() => modelFailure.root.unmount());

    vi.mocked(fetchModels).mockResolvedValueOnce([
      {
        provider: "mock",
        model: "tools-model",
        display_name: "Tools Model",
        supports_streaming: false,
        supports_tools: true,
        supports_json: false,
        input_price_per_1m: null,
        output_price_per_1m: null,
      },
    ]);
    vi.mocked(createAgentRun).mockRejectedValueOnce(
      new AgentApiError("Provider unavailable", {
        requestId: "request-agent-dom",
        status: 503,
      }),
    );
    const transportFailure = mountPage();
    await flushEffects();
    await enterTaskAndSubmit(transportFailure.container);
    await flushEffects();
    expect(transportFailure.container.textContent).toContain(
      "Provider unavailable",
    );
    expect(transportFailure.container.textContent).toContain(
      "request-agent-dom",
    );
    act(() => transportFailure.root.unmount());
  });

  it("clears the recovery point when starting a new task", async () => {
    vi.mocked(createAgentRun).mockResolvedValue(execution);
    const { container, root } = mountPage();
    await flushEffects();
    await enterTaskAndSubmit(container);
    await flushEffects();

    const newTask = [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "New task",
    );
    if (newTask === undefined) {
      throw new Error("New task button is missing");
    }
    act(() => newTask.click());

    expect(window.sessionStorage.getItem("ai-agent-lab:last-agent-run-id")).toBeNull();
    expect(window.location.search).not.toContain("run=");
    act(() => root.unmount());
  });
});
