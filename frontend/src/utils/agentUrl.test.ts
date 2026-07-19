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
    expect(readAgentRunId(`?run=${RUN_ID.toUpperCase()}`)).toBe(
      RUN_ID.toUpperCase(),
    );
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

  it("returns to the default Chat URL without deleting other state", () => {
    expect(
      buildWorkspaceUrl(
        `http://localhost:5173/?workspace=agent&conversation=chat-1&run=${RUN_ID}`,
        "chat",
      ),
    ).toBe(
      `http://localhost:5173/?conversation=chat-1&run=${RUN_ID}`,
    );
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
});
