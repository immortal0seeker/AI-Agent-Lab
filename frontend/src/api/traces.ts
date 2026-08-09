import { API_BASE_URL, createApiUrl } from "./client";
import type { TraceRunDetail, TraceRunSummary } from "../types/trace";

type TraceErrorEnvelope = {
  error?: {
    code?: unknown;
    message?: unknown;
    request_id?: unknown;
  };
};

type TraceApiErrorOptions = {
  code?: string | null;
  requestId?: string | null;
  status?: number | null;
};

export class TraceApiError extends Error {
  readonly code: string | null;
  readonly requestId: string | null;
  readonly status: number | null;

  constructor(message: string, options: TraceApiErrorOptions = {}) {
    super(message);
    this.name = "TraceApiError";
    this.code = options.code ?? null;
    this.requestId = options.requestId ?? null;
    this.status = options.status ?? null;
  }
}

function structuredError(payload: unknown): TraceErrorEnvelope["error"] {
  if (typeof payload !== "object" || payload === null) {
    return undefined;
  }
  const candidate = payload as TraceErrorEnvelope;
  return typeof candidate.error === "object" && candidate.error !== null
    ? candidate.error
    : undefined;
}

async function requestTraceJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(createApiUrl(API_BASE_URL, path));
  } catch {
    throw new TraceApiError("Unable to reach Trace API");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    if (response.ok) {
      throw new TraceApiError("Trace API returned invalid JSON", {
        status: response.status,
      });
    }
    throw new TraceApiError(`Request failed with status ${response.status}`, {
      status: response.status,
    });
  }

  if (!response.ok) {
    const error = structuredError(payload);
    throw new TraceApiError(
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

export function fetchTraceRuns(limit = 50): Promise<TraceRunSummary[]> {
  return requestTraceJson<TraceRunSummary[]>(`/traces?limit=${limit}`);
}

export function fetchTraceRunDetail(
  traceRunId: string,
): Promise<TraceRunDetail> {
  return requestTraceJson<TraceRunDetail>(
    `/traces/${encodeURIComponent(traceRunId)}`,
  );
}
