// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/health", () => ({ fetchHealth: vi.fn() }));
vi.mock("../api/traces", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/traces")>();
  return {
    ...actual,
    fetchTraceRuns: vi.fn(),
    fetchTraceRunDetail: vi.fn(),
  };
});

import { fetchHealth } from "../api/health";
import {
  fetchTraceRunDetail,
  fetchTraceRuns,
  TraceApiError,
} from "../api/traces";
import type { TraceRunDetail, TraceRunSummary } from "../types/trace";
import TraceTimelinePage from "./TraceTimelinePage";


const firstId = "00000000-0000-0000-0000-000000000101";
const secondId = "00000000-0000-0000-0000-000000000102";
const deepLinkId = "00000000-0000-0000-0000-000000000199";
const now = "2026-08-09T12:00:00";
const reactTestEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT: boolean;
};

function summary(id: string, input: string): TraceRunSummary {
  return {
    id,
    run_type: "rag_chat",
    status: "completed",
    title: null,
    input_preview: input,
    conversation_id: null,
    agent_run_id: null,
    user_message_id: null,
    provider: "mock",
    model: "mock-chat",
    total_input_tokens: null,
    total_output_tokens: null,
    total_tokens: null,
    estimated_cost: null,
    latency_ms: 10,
    error_message: null,
    started_at: now,
    ended_at: now,
    created_at: now,
  };
}

function detail(id: string, input: string, output: string): TraceRunDetail {
  const { input_preview: _inputPreview, ...detailSummary } = summary(id, input);
  return {
    ...detailSummary,
    input_text: input,
    output_text: output,
    metadata_json: {},
    steps: [],
    retrieval_runs: [],
  };
}

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
    await Promise.resolve();
  });
}

function mountPage(): { container: HTMLDivElement; root: Root } {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => {
    root.render(<TraceTimelinePage onSelectWorkspace={vi.fn()} />);
  });
  return { container, root };
}

function clickButton(container: HTMLElement, label: string): void {
  const button = Array.from(container.querySelectorAll("button")).find(
    (candidate) => candidate.getAttribute("aria-label") === label,
  );
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error(`Button not found: ${label}`);
  }
  act(() => button.click());
}

beforeEach(() => {
  reactTestEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
  window.history.replaceState(null, "", "/?workspace=trace");
  vi.mocked(fetchHealth).mockResolvedValue({
    status: "ok",
    service: "AI Agent Lab Backend",
  });
  vi.mocked(fetchTraceRuns).mockReset();
  vi.mocked(fetchTraceRunDetail).mockReset();
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("TraceTimelinePage mounted async flows", () => {
  it("selects the first recent Run and writes its URL", async () => {
    vi.mocked(fetchTraceRuns).mockResolvedValue([
      summary(firstId, "First question"),
      summary(secondId, "Second question"),
    ]);
    vi.mocked(fetchTraceRunDetail).mockResolvedValue(
      detail(firstId, "First question", "First answer"),
    );

    const { container, root } = mountPage();
    await flushEffects();

    expect(fetchTraceRunDetail).toHaveBeenCalledWith(firstId);
    expect(window.location.search).toContain(`run=${firstId}`);
    expect(container.textContent).toContain("First answer");
    expect(
      container.querySelector(".trace-detail__header h2")?.textContent,
    ).toBe("First question");
    act(() => root.unmount());
  });

  it("loads a valid deep link even when absent from the recent list", async () => {
    window.history.replaceState(
      null,
      "",
      `/?workspace=trace&run=${deepLinkId}`,
    );
    vi.mocked(fetchTraceRuns).mockResolvedValue([summary(firstId, "Recent")]);
    vi.mocked(fetchTraceRunDetail).mockResolvedValue(
      detail(deepLinkId, "Deep question", "Deep answer"),
    );

    const { container, root } = mountPage();
    await flushEffects();

    expect(fetchTraceRunDetail).toHaveBeenCalledWith(deepLinkId);
    expect(container.textContent).toContain("Deep answer");
    expect(window.location.search).toContain(`run=${deepLinkId}`);
    act(() => root.unmount());
  });

  it("renders list empty and retries a list error", async () => {
    vi.mocked(fetchTraceRuns)
      .mockRejectedValueOnce(
        new TraceApiError("Trace list unavailable", {
          requestId: "request-list-1",
        }),
      )
      .mockResolvedValueOnce([]);

    const { container, root } = mountPage();
    await flushEffects();
    expect(container.textContent).toContain("Trace list unavailable");
    expect(container.textContent).toContain("request-list-1");

    clickButton(container, "Retry Trace list");
    await flushEffects();
    expect(container.textContent).toContain("No Trace Runs recorded yet");
    act(() => root.unmount());
  });

  it("keeps the list usable and retries the same detail ID", async () => {
    vi.mocked(fetchTraceRuns).mockResolvedValue([
      summary(firstId, "First question"),
    ]);
    vi.mocked(fetchTraceRunDetail)
      .mockRejectedValueOnce(new TraceApiError("Trace detail unavailable"))
      .mockResolvedValueOnce(
        detail(firstId, "First question", "Recovered answer"),
      );

    const { container, root } = mountPage();
    await flushEffects();
    expect(container.textContent).toContain("Trace detail unavailable");
    expect(container.textContent).toContain("First question");

    clickButton(container, "Retry Trace detail");
    await flushEffects();
    expect(fetchTraceRunDetail).toHaveBeenLastCalledWith(firstId);
    expect(container.textContent).toContain("Recovered answer");
    act(() => root.unmount());
  });

  it("ignores a stale detail response after a newer Run is selected", async () => {
    const first = deferred<TraceRunDetail>();
    vi.mocked(fetchTraceRuns).mockResolvedValue([
      summary(firstId, "First question"),
      summary(secondId, "Second question"),
    ]);
    vi.mocked(fetchTraceRunDetail)
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(
        detail(secondId, "Second question", "Second answer"),
      );
    const { container, root } = mountPage();
    await flushEffects();

    clickButton(container, `View Trace ${secondId}`);
    await flushEffects();
    await act(async () => {
      first.resolve(detail(firstId, "First question", "Stale first answer"));
      await first.promise;
    });

    expect(container.textContent).toContain("Second answer");
    expect(container.textContent).not.toContain("Stale first answer");
    act(() => root.unmount());
  });

  it("ignores late list and detail responses after unmount", async () => {
    const list = deferred<TraceRunSummary[]>();
    const run = deferred<TraceRunDetail>();
    window.history.replaceState(
      null,
      "",
      `/?workspace=trace&run=${deepLinkId}`,
    );
    vi.mocked(fetchTraceRuns).mockReturnValue(list.promise);
    vi.mocked(fetchTraceRunDetail).mockReturnValue(run.promise);
    const { root } = mountPage();

    act(() => root.unmount());
    await act(async () => {
      list.resolve([summary(firstId, "Late list")]);
      run.resolve(detail(deepLinkId, "Late question", "Late answer"));
      await Promise.all([list.promise, run.promise]);
    });

    expect(window.location.search).toContain(`run=${deepLinkId}`);
  });
});
