import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import AgentRunPanel, { type AgentRunViewState } from "./AgentRunPanel";
import type { AgentRunExecution } from "../../types/agent";

const completedExecution: AgentRunExecution = {
  id: "00000000-0000-0000-0000-000000000101",
  conversation_id: "00000000-0000-0000-0000-000000000102",
  user_message_id: "00000000-0000-0000-0000-000000000103",
  status: "completed",
  goal: "Read README.md",
  final_answer: "The workspace contains a FastAPI backend and React frontend.",
  error: null,
  started_at: "2026-07-19T12:00:00",
  ended_at: "2026-07-19T12:00:01",
  latency_ms: 1000,
  created_at: "2026-07-19T12:00:00",
  tool_calls: [],
};

function renderState(state: AgentRunViewState): string {
  return renderToStaticMarkup(<AgentRunPanel state={state} />);
}

describe("AgentRunPanel", () => {
  it("renders a loading state with caller-provided context", () => {
    const html = renderState({
      status: "loading",
      message: "Running Agent task...",
    });

    expect(html).toContain("Running Agent task...");
    expect(html).toContain('role="status"');
  });

  it("renders the ready empty state", () => {
    const html = renderState({ status: "empty" });

    expect(html).toContain("Start an Agent task");
    expect(html).toContain("final answer and ToolCall audit trail");
  });

  it("distinguishes a Registry with no tools-capable models", () => {
    const html = renderState({ status: "no-models" });

    expect(html).toContain("No tools-capable model");
    expect(html).toContain("supports_tools=true");
  });

  it("renders a safe transport error and Request ID", () => {
    const html = renderState({
      status: "error",
      message: "The requested provider is unavailable",
      requestId: "request-agent-1",
    });

    expect(html).toContain("The requested provider is unavailable");
    expect(html).toContain("Request ID");
    expect(html).toContain("request-agent-1");
  });

  it("omits a Request ID row when the transport has none", () => {
    const html = renderState({
      status: "error",
      message: "Unable to reach Agent API",
      requestId: null,
    });

    expect(html).toContain("Unable to reach Agent API");
    expect(html).not.toContain("Request ID");
  });

  it("shows a completed answer, trace IDs, timing, and empty ToolCalls", () => {
    const html = renderState({ status: "result", run: completedExecution });

    expect(html).toContain("Completed");
    expect(html).toContain("Run ID");
    expect(html).toContain(completedExecution.id);
    expect(html).toContain("Conversation ID");
    expect(html).toContain(completedExecution.conversation_id);
    expect(html).toContain("1.00 s");
    expect(html).toContain(completedExecution.final_answer ?? "");
    expect(html).toContain("This run did not call any tools.");
  });

  it("shows a structured failed run as an auditable result", () => {
    const failedExecution: AgentRunExecution = {
      ...completedExecution,
      status: "failed",
      final_answer: null,
      error: "Agent reached the maximum number of steps",
    };
    const html = renderState({ status: "result", run: failedExecution });

    expect(html).toContain("Run failed");
    expect(html).toContain(failedExecution.id);
    expect(html).toContain("Agent reached the maximum number of steps");
    expect(html).not.toContain("Request ID");
  });

  it("keeps a restored non-terminal status inspectable", () => {
    const html = renderState({
      status: "result",
      run: { ...completedExecution, status: "waiting_tool", final_answer: null },
    });

    expect(html).toContain("Waiting for tool");
    expect(html).toContain(completedExecution.id);
  });
});
