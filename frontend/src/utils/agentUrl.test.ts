import { describe, expect, it } from "vitest";

import {
  buildAgentRunUrl,
  buildTraceRunUrl,
  buildWorkspaceUrl,
  readAgentRunId,
  readTraceRunId,
  readWorkspace,
} from "./agentUrl";

const RUN_ID = "00000000-0000-0000-0000-000000000101";

describe("Agent workspace URL helpers", () => {
  it("defaults to Chat and recognizes the explicit workspaces", () => {
    expect(readWorkspace("")).toBe("chat");
    expect(readWorkspace("?workspace=agent")).toBe("agent");
    expect(readWorkspace("?workspace=knowledge")).toBe("knowledge");
    expect(readWorkspace("?workspace=trace")).toBe("trace");
    expect(readWorkspace("?workspace=unknown")).toBe("chat");
  });

  it("accepts only a UUID TraceRun ID", () => {
    expect(readTraceRunId(`?workspace=trace&run=${RUN_ID}`)).toBe(RUN_ID);
    expect(readTraceRunId("?workspace=trace&run=not-a-uuid")).toBeNull();
  });

  it("accepts only a UUID AgentRun ID", () => {
    expect(readAgentRunId(`?run=${RUN_ID}`)).toBe(RUN_ID);
    expect(readAgentRunId(`?run=${RUN_ID.toUpperCase()}`)).toBe(
      RUN_ID.toUpperCase(),
    );
    expect(readAgentRunId("?run=not-a-uuid")).toBeNull();
  });

  it("switches workspace while clearing incompatible run and preserving other state", () => {
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?conversation=chat-1&run=${RUN_ID}#result`,
        "agent",
      ),
    ).toBe(
      "http://localhost:5173/?conversation=chat-1&workspace=agent#result",
    );
  });

  it("returns to the default Chat URL without deleting other state", () => {
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?workspace=agent&conversation=chat-1&run=${RUN_ID}`,
        "chat",
      ),
    ).toBe(
      "http://localhost:5173/?conversation=chat-1",
    );
  });

  it("selects Knowledge while preserving unrelated state", () => {
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?conversation=chat-1&run=${RUN_ID}#documents`,
        "knowledge",
      ),
    ).toBe(
      "http://localhost:5173/?conversation=chat-1&workspace=knowledge#documents",
    );
  });

  it("clears Agent and Trace run IDs only when changing workspaces", () => {
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?workspace=agent&run=${RUN_ID}`,
        "trace",
      ),
    ).toBe("http://localhost:5173/?workspace=trace");
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?workspace=trace&run=${RUN_ID}`,
        "trace",
      ),
    ).toBe(`http://localhost:5173/?workspace=trace&run=${RUN_ID}`);
  });

  it("sets and clears only the AgentRun query", () => {
    const url = buildAgentRunUrl(
      "http://localhost:5173/?workspace=agent&conversation=chat-1#tool-calls",
      RUN_ID,
    );
    expect(url).toBe(
      `http://localhost:5173/?workspace=agent&conversation=chat-1&run=${RUN_ID}#tool-calls`,
    );
    expect(buildAgentRunUrl(url, null)).toBe(
      "http://localhost:5173/?workspace=agent&conversation=chat-1#tool-calls",
    );
  });

  it("sets and clears only the TraceRun query", () => {
    const url = buildTraceRunUrl(
      "http://localhost:5173/?workspace=trace&conversation=chat-1#steps",
      RUN_ID,
    );
    expect(url).toBe(
      `http://localhost:5173/?workspace=trace&conversation=chat-1&run=${RUN_ID}#steps`,
    );
    expect(buildTraceRunUrl(url, null)).toBe(
      "http://localhost:5173/?workspace=trace&conversation=chat-1#steps",
    );
  });
});
