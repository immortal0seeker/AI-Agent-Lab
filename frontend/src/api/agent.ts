import { API_BASE_URL, createApiUrl } from "./client";
import type {
  AgentRun,
  AgentRunCreate,
  AgentRunExecution,
  ToolCall,
} from "../types/agent";

type AgentErrorEnvelope = {
  error?: {
    code?: unknown;
    message?: unknown;
    request_id?: unknown;
  };
};

type AgentApiErrorOptions = {
  code?: string | null;
  requestId?: string | null;
  status?: number | null;
};

export class AgentApiError extends Error {
  readonly code: string | null;
  readonly requestId: string | null;
  readonly status: number | null;

  constructor(message: string, options: AgentApiErrorOptions = {}) {
    super(message);
    this.name = "AgentApiError";
    this.code = options.code ?? null;
    this.requestId = options.requestId ?? null;
    this.status = options.status ?? null;
  }
}

function structuredError(payload: unknown): AgentErrorEnvelope["error"] {
  if (typeof payload !== "object" || payload === null) {
    return undefined;
  }
  const candidate = payload as AgentErrorEnvelope;
  return typeof candidate.error === "object" && candidate.error !== null
    ? candidate.error
    : undefined;
}

async function requestAgentJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(createApiUrl(API_BASE_URL, path), init);
  } catch {
    throw new AgentApiError("Unable to reach Agent API");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    if (response.ok) {
      throw new AgentApiError("Agent API returned invalid JSON", {
        status: response.status,
      });
    }
    throw new AgentApiError(`Request failed with status ${response.status}`, {
      status: response.status,
    });
  }

  if (!response.ok) {
    const error = structuredError(payload);
    throw new AgentApiError(
      typeof error?.message === "string"
        ? error.message
        : `Request failed with status ${response.status}`,
      {
        code: typeof error?.code === "string" ? error.code : null,
        requestId:
          typeof error?.request_id === "string" ? error.request_id : null,
        status: response.status,
      },
    );
  }

  return payload as T;
}

export function createAgentRun(
  request: AgentRunCreate,
): Promise<AgentRunExecution> {
  return requestAgentJson<AgentRunExecution>("/agents/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function fetchAgentRun(runId: string): Promise<AgentRun> {
  return requestAgentJson<AgentRun>(`/agents/runs/${runId}`);
}

export function fetchAgentToolCalls(runId: string): Promise<ToolCall[]> {
  return requestAgentJson<ToolCall[]>(`/agents/runs/${runId}/tool-calls`);
}
