import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import TraceStepTimeline, {
  retrievalForStep,
  retrievalRunIdForStep,
} from "./TraceStepTimeline";
import type { TraceRunDetail, TraceStep } from "../../types/trace";


const traceId = "00000000-0000-0000-0000-000000000101";
const retrievalId = "00000000-0000-0000-0000-000000000201";
const now = "2026-08-09T12:00:00";

function step(
  index: number,
  stepType: TraceStep["step_type"],
  output: Record<string, unknown> | null = {},
): TraceStep {
  return {
    id: `00000000-0000-0000-0000-${String(index).padStart(12, "0")}`,
    trace_run_id: traceId,
    step_index: index,
    step_type: stepType,
    name: stepType,
    status: index === 3 ? "failed" : "completed",
    input_json: { step: index },
    output_json: output,
    error_message: index === 3 ? "Safe model failure" : null,
    latency_ms: index * 2,
    started_at: now,
    ended_at: now,
    created_at: now,
  };
}

const ragTraceDetail: TraceRunDetail = {
  id: traceId,
  run_type: "rag_chat",
  status: "failed",
  title: null,
  input_text: "Where is the design?",
  output_text: null,
  conversation_id: null,
  agent_run_id: null,
  user_message_id: null,
  provider: "mock",
  model: "mock-chat",
  total_input_tokens: null,
  total_output_tokens: null,
  total_tokens: null,
  estimated_cost: null,
  latency_ms: 20,
  error_message: "Safe run failure",
  metadata_json: { prompt_version: "naive-rag-v1" },
  started_at: now,
  ended_at: now,
  created_at: now,
  steps: [
    step(1, "rag_retrieve", { retrieval_run_id: retrievalId }),
    step(2, "build_prompt"),
    step(3, "llm_call", null),
    step(4, "final_answer"),
  ],
  retrieval_runs: [
    {
      id: retrievalId,
      trace_run_id: traceId,
      knowledge_base_id: "00000000-0000-0000-0000-000000000301",
      strategy_name: "naive_vector",
      original_query: "Where is the design?",
      rewritten_query: null,
      top_k: 5,
      candidate_count: 2,
      selected_count: 2,
      score_threshold: null,
      latency_ms: 12,
      metadata_filter_json: {},
      strategy_config_json: {},
      created_at: now,
      candidates: [
        {
          id: "00000000-0000-0000-0000-000000000401",
          retrieval_run_id: retrievalId,
          document_id: "00000000-0000-0000-0000-000000000501",
          chunk_id: "00000000-0000-0000-0000-000000000601",
          rank: 1,
          final_rank: 1,
          source: "dense",
          dense_score: 0.91,
          sparse_score: null,
          fused_score: null,
          rerank_score: null,
          selected: true,
          content_preview: "First source",
          metadata_json: {},
          created_at: now,
        },
        {
          id: "00000000-0000-0000-0000-000000000402",
          retrieval_run_id: retrievalId,
          document_id: "00000000-0000-0000-0000-000000000502",
          chunk_id: "00000000-0000-0000-0000-000000000602",
          rank: 2,
          final_rank: 2,
          source: "dense",
          dense_score: 0.81,
          sparse_score: null,
          fused_score: null,
          rerank_score: null,
          selected: true,
          content_preview: "Second source",
          metadata_json: {},
          created_at: now,
        },
      ],
    },
  ],
};


describe("TraceStepTimeline", () => {
  it("renders ordered steps, metadata, retrieval evidence, and failures", () => {
    const html = renderToStaticMarkup(
      <TraceStepTimeline detail={ragTraceDetail} />,
    );

    expect(html.indexOf("rag_retrieve")).toBeLessThan(
      html.indexOf("build_prompt"),
    );
    expect(html.indexOf("build_prompt")).toBeLessThan(
      html.indexOf("llm_call"),
    );
    expect(html.indexOf("Rank 1")).toBeLessThan(html.indexOf("Rank 2"));
    expect(html).toContain("Input metadata");
    expect(html).toContain("Output metadata");
    expect(html).toContain("Safe model failure");
    expect(html).toContain(
      ragTraceDetail.retrieval_runs[0].knowledge_base_id,
    );
  });

  it("defensively handles missing or malformed retrieval links", () => {
    const malformed = step(1, "rag_retrieve", { retrieval_run_id: 42 });
    const missing = step(1, "rag_retrieve", {
      retrieval_run_id: "00000000-0000-0000-0000-000000000999",
    });

    expect(retrievalRunIdForStep(malformed)).toBeNull();
    expect(retrievalForStep(missing, ragTraceDetail.retrieval_runs)).toBeNull();
    expect(
      renderToStaticMarkup(
        <TraceStepTimeline
          detail={{ ...ragTraceDetail, steps: [malformed, missing] }}
        />,
      ),
    ).toContain("Retrieval audit is unavailable for this Step");
  });
});
