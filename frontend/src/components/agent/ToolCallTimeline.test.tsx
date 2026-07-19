import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ToolCallTimeline from "./ToolCallTimeline";
import type { ToolCall, ToolCallStatus } from "../../types/agent";

function createToolCall(
  status: ToolCallStatus,
  index: number,
): ToolCall {
  const success = status === "success";
  const terminal = !["pending", "running"].includes(status);
  return {
    id: `00000000-0000-0000-0000-00000000010${index}`,
    tool_call_id: `call-${status}`,
    agent_run_id: "00000000-0000-0000-0000-000000000201",
    conversation_id: "00000000-0000-0000-0000-000000000202",
    tool_name: index % 2 === 0 ? "list_dir" : "read_file",
    arguments: {
      path: index === 1 ? '<script>alert("unsafe")</script>' : ".",
    },
    result: terminal
      ? {
          tool_name: index % 2 === 0 ? "list_dir" : "read_file",
          success,
          content: success ? "Workspace summary" : "",
          data: null,
          error: success ? null : `Safe ${status} error`,
          metadata: {},
        }
      : null,
    status,
    error: terminal && !success ? `Safe ${status} error` : null,
    started_at: status === "pending" ? null : "2026-07-19T12:00:00",
    ended_at: terminal ? "2026-07-19T12:00:00.025000" : null,
    latency_ms: terminal ? 25 : null,
    created_at: "2026-07-19T12:00:00",
  };
}

describe("ToolCallTimeline", () => {
  it("renders an explicit empty ToolCall state", () => {
    expect(renderToStaticMarkup(<ToolCallTimeline toolCalls={[]} />)).toContain(
      "This run did not call any tools.",
    );
  });

  it("keeps ToolCalls in input order and exposes traceable IDs", () => {
    const pendingCall = createToolCall("pending", 1);
    const successCall = createToolCall("success", 2);
    const failedCall = createToolCall("failed", 3);
    const html = renderToStaticMarkup(
      <ToolCallTimeline
        toolCalls={[pendingCall, successCall, failedCall]}
      />,
    );

    expect(html).toContain("read_file");
    expect(html).toContain("list_dir");
    expect(html).toContain("Pending");
    expect(html).toContain("Success");
    expect(html).toContain("Failed");
    expect(html).toContain("Provider call ID");
    expect(html).toContain("Database ID");
    expect(html).not.toContain('<script>alert("unsafe")</script>');
    expect(html).toContain("&lt;script&gt;alert");
    expect(html.indexOf(pendingCall.id)).toBeLessThan(
      html.indexOf(successCall.id),
    );
    expect(html.indexOf(successCall.id)).toBeLessThan(
      html.indexOf(failedCall.id),
    );
  });

  it.each([
    ["running", "Running", "pending"],
    ["timeout", "Timeout", "error"],
    ["blocked", "Blocked", "error"],
  ] as const)(
    "renders %s with the expected label and tone",
    (status, label, tone) => {
      const html = renderToStaticMarkup(
        <ToolCallTimeline toolCalls={[createToolCall(status, 4)]} />,
      );

      expect(html).toContain(label);
      expect(html).toContain(`tool-call-status--${tone}`);
    },
  );
});
