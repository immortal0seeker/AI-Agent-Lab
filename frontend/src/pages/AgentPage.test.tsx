import { describe, expect, it } from "vitest";

import { AgentApiError } from "../api/agent";
import type { ModelOption } from "../types/models";
import {
  createAgentRequestGate,
  toAgentPageError,
  toolsCapableModels,
} from "./AgentPage";

const models: ModelOption[] = [
  {
    provider: "provider-a",
    model: "chat-model",
    display_name: "Chat Model",
    supports_streaming: true,
    supports_tools: false,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
  {
    provider: "provider-a",
    model: "tools-model",
    display_name: "Tools Model",
    supports_streaming: false,
    supports_tools: true,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
];

describe("AgentPage helpers", () => {
  it("offers only Registry models that advertise Tool support", () => {
    expect(toolsCapableModels(models).map((item) => item.model)).toEqual([
      "tools-model",
    ]);
    expect(toolsCapableModels(models)).not.toBe(models);
  });

  it("preserves a safe Agent API Request ID", () => {
    expect(
      toAgentPageError(
        new AgentApiError("Provider unavailable", {
          code: "provider_unavailable",
          requestId: "request-agent-7",
          status: 503,
        }),
      ),
    ).toEqual({
      message: "Provider unavailable",
      requestId: "request-agent-7",
    });
  });

  it("uses a readable fallback for an unknown failure", () => {
    expect(toAgentPageError("private failure")).toEqual({
      message: "Agent request failed",
      requestId: null,
    });
  });

  it("keeps a normal Error message without inventing a Request ID", () => {
    expect(toAgentPageError(new Error("Unable to load Agent run"))).toEqual({
      message: "Unable to load Agent run",
      requestId: null,
    });
  });

  it("invalidates a pending request when the Agent page leaves the workspace", () => {
    const gate = createAgentRequestGate();
    const request = gate.begin();

    expect(gate.isCurrent(request)).toBe(true);
    gate.invalidate();
    expect(gate.isCurrent(request)).toBe(false);

    const nextRequest = gate.begin();
    expect(gate.isCurrent(nextRequest)).toBe(true);
  });
});
