import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchTraceRunDetail,
  fetchTraceRuns,
  TraceApiError,
} from "./traces";
import type { TraceRunDetail, TraceRunSummary } from "../types/trace";

const traceId = "00000000-0000-0000-0000-000000000101";
const createdAt = "2026-08-09T12:00:00";

const summary: TraceRunSummary = {
  id: traceId,
  run_type: "rag_chat",
  status: "completed",
  title: "Architecture answer",
  input_preview: "Where is the design?",
  conversation_id: null,
  agent_run_id: null,
  user_message_id: null,
  provider: "mock",
  model: "mock-chat",
  total_input_tokens: 7,
  total_output_tokens: 5,
  total_tokens: 12,
  estimated_cost: "0.00000700",
  latency_ms: 18,
  error_message: null,
  started_at: createdAt,
  ended_at: createdAt,
  created_at: createdAt,
};

const { input_preview: _inputPreview, ...detailSummary } = summary;
const detail: TraceRunDetail = {
  ...detailSummary,
  input_text: "Where is the design?",
  output_text: "In the architecture document.",
  metadata_json: { prompt_version: "naive-rag-v1" },
  steps: [],
  retrieval_runs: [],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Trace API", () => {
  it("queries the default list, explicit list, and encoded detail URLs", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([summary]), {
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([summary]), {
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(detail), {
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchTraceRuns()).resolves.toEqual([summary]);
    await expect(fetchTraceRuns(25)).resolves.toEqual([summary]);
    await expect(fetchTraceRunDetail(traceId)).resolves.toEqual(detail);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "http://localhost:8000/api/v1/traces?limit=50",
      "http://localhost:8000/api/v1/traces?limit=25",
      `http://localhost:8000/api/v1/traces/${traceId}`,
    ]);
  });

  it("preserves safe structured error fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "trace_run_not_found",
              message: "Trace run not found",
              request_id: "request-trace-1",
            },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const error = await fetchTraceRunDetail(traceId).catch(
      (reason: unknown) => reason,
    );

    expect(error).toBeInstanceOf(TraceApiError);
    expect(error).toMatchObject({
      message: "Trace run not found",
      code: "trace_run_not_found",
      requestId: "request-trace-1",
      status: 404,
    });
  });

  it("normalizes network and non-JSON failures without leaking bodies", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private network")));
    await expect(fetchTraceRuns()).rejects.toMatchObject({
      message: "Unable to reach Trace API",
      status: null,
    });

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("private upstream body", { status: 502 }),
      ),
    );
    await expect(fetchTraceRuns()).rejects.toMatchObject({
      message: "Request failed with status 502",
      code: null,
      requestId: null,
      status: 502,
    });
  });

  it("rejects successful non-JSON responses with a fixed error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not-json", { status: 200 })),
    );

    await expect(fetchTraceRunDetail(traceId)).rejects.toMatchObject({
      message: "Trace API returned invalid JSON",
      status: 200,
    });
  });
});
