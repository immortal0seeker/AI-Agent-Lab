import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import TraceRunList, { type TraceRunListState } from "./TraceRunList";
import type { TraceRunSummary } from "../../types/trace";


const run: TraceRunSummary = {
  id: "00000000-0000-0000-0000-000000000101",
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
  started_at: "2026-08-09T12:00:00",
  ended_at: "2026-08-09T12:00:00",
  created_at: "2026-08-09T12:00:00",
};


function renderState(state: TraceRunListState, selectedId: string | null = null) {
  return renderToStaticMarkup(
    <TraceRunList
      state={state}
      selectedId={selectedId}
      onSelect={vi.fn()}
      onRetry={vi.fn()}
    />,
  );
}


describe("TraceRunList", () => {
  it("renders loading, empty, and safe error states", () => {
    expect(renderState({ status: "loading" })).toContain(
      "Loading recent Trace Runs...",
    );
    expect(renderState({ status: "ready", runs: [] })).toContain(
      "No Trace Runs recorded yet",
    );
    const error = renderState({
      status: "error",
      message: "Trace list unavailable",
      requestId: "request-list-1",
    });
    expect(error).toContain("Trace list unavailable");
    expect(error).toContain("request-list-1");
    expect(error).toContain("Retry list");
  });

  it("renders full IDs, run labels, and selected state", () => {
    const html = renderState({ status: "ready", runs: [run] }, run.id);

    expect(html).toContain(run.id);
    expect(html).toContain("RAG Chat");
    expect(html).toContain("Completed");
    expect(html).toContain('aria-current="true"');
    expect(html).toContain(run.input_preview);
  });
});
