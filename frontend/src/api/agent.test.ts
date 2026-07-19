import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AgentApiError,
  createAgentRun,
  fetchAgentRun,
  fetchAgentToolCalls,
} from "./agent";
import type { AgentRunExecution, ToolCall } from "../types/agent";

const runId = "00000000-0000-0000-0000-000000000101";
const conversationId = "00000000-0000-0000-0000-000000000102";

const toolCall: ToolCall = {
  id: "00000000-0000-0000-0000-000000000104",
  tool_call_id: "call-read-readme",
  agent_run_id: runId,
  conversation_id: conversationId,
  tool_name: "read_file",
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
  started_at: "2026-07-19T12:00:00",
  ended_at: "2026-07-19T12:00:00.020000",
  latency_ms: 20,
  created_at: "2026-07-19T12:00:00",
};

const execution: AgentRunExecution = {
  id: runId,
  conversation_id: conversationId,
  user_message_id: "00000000-0000-0000-0000-000000000103",
  status: "completed",
  goal: "Read README.md",
  final_answer: "A local AI engineering workspace.",
  error: null,
  started_at: "2026-07-19T12:00:00",
  ended_at: "2026-07-19T12:00:01",
  latency_ms: 1000,
  created_at: "2026-07-19T12:00:00",
  tool_calls: [toolCall],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

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

  it("keeps a structured failed run as a successful HTTP result", async () => {
    const failedExecution: AgentRunExecution = {
      ...execution,
      status: "failed",
      final_answer: null,
      error: "Agent reached the maximum number of steps",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(failedExecution), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      createAgentRun({
        provider: "provider-a",
        model: "tools-model",
        input: "Keep reading",
      }),
    ).resolves.toEqual(failedExecution);
  });

  it("queries one run and its ToolCalls", async () => {
    const { tool_calls: _toolCalls, ...run } = execution;
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(run), {
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([toolCall]), {
          headers: { "Content-Type": "application/json" },
        }),
      );
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

  it("uses a fixed fallback for non-JSON failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("private upstream body", { status: 502 })),
    );

    await expect(fetchAgentRun(runId)).rejects.toMatchObject({
      message: "Request failed with status 502",
      code: null,
      requestId: null,
      status: 502,
    });
  });

  it("normalizes a successful response with invalid JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not-json", { status: 200 })),
    );

    await expect(fetchAgentToolCalls(runId)).rejects.toMatchObject({
      message: "Agent API returned invalid JSON",
      status: 200,
    });
  });
});
