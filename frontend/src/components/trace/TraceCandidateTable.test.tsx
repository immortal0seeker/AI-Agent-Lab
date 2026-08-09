import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import TraceCandidateTable from "./TraceCandidateTable";
import type { RagRetrievalRun } from "../../types/trace";


const retrieval: RagRetrievalRun = {
  id: "00000000-0000-0000-0000-000000000201",
  trace_run_id: "00000000-0000-0000-0000-000000000101",
  knowledge_base_id: "00000000-0000-0000-0000-000000000301",
  strategy_name: "naive_vector",
  original_query: "Where is the design?",
  rewritten_query: null,
  top_k: 5,
  candidate_count: 2,
  selected_count: 1,
  score_threshold: 0.5,
  latency_ms: 12,
  metadata_filter_json: {},
  strategy_config_json: {},
  created_at: "2026-08-09T12:00:00",
  candidates: [
    {
      id: "00000000-0000-0000-0000-000000000401",
      retrieval_run_id: "00000000-0000-0000-0000-000000000201",
      document_id: "00000000-0000-0000-0000-000000000501",
      chunk_id: "00000000-0000-0000-0000-000000000601",
      rank: 1,
      final_rank: 1,
      source: "dense",
      dense_score: 0.91,
      sparse_score: null,
      fused_score: 0.88,
      rerank_score: null,
      selected: true,
      content_preview: "Architecture source",
      metadata_json: { filename: "architecture.md" },
      created_at: "2026-08-09T12:00:00",
    },
    {
      id: "00000000-0000-0000-0000-000000000402",
      retrieval_run_id: "00000000-0000-0000-0000-000000000201",
      document_id: "00000000-0000-0000-0000-000000000502",
      chunk_id: "00000000-0000-0000-0000-000000000602",
      rank: 2,
      final_rank: null,
      source: "dense",
      dense_score: 0.81,
      sparse_score: null,
      fused_score: null,
      rerank_score: null,
      selected: false,
      content_preview: "Secondary source",
      metadata_json: {},
      created_at: "2026-08-09T12:00:00",
    },
  ],
};


describe("TraceCandidateTable", () => {
  it("renders ordered candidates, exact score names, previews, and IDs", () => {
    const html = renderToStaticMarkup(
      <TraceCandidateTable retrieval={retrieval} />,
    );

    expect(html.indexOf("Rank 1")).toBeLessThan(html.indexOf("Rank 2"));
    expect(html).toContain("dense_score");
    expect(html).toContain("fused_score");
    expect(html).not.toContain("sparse_score");
    expect(html).toContain(retrieval.candidates[0].document_id);
    expect(html).toContain(retrieval.candidates[0].chunk_id);
    expect(html).toContain("Architecture source");
    expect(html).toContain("Selected");
  });

  it("renders a bounded zero-candidate state", () => {
    const html = renderToStaticMarkup(
      <TraceCandidateTable
        retrieval={{
          ...retrieval,
          candidate_count: 0,
          selected_count: 0,
          candidates: [],
        }}
      />,
    );

    expect(html).toContain("No retrieval candidates recorded");
  });
});
