export type TraceRunType =
  | "chat"
  | "agent"
  | "rag_query"
  | "rag_chat"
  | "evaluation"
  | "tool";

export type TraceStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type TraceStepType =
  | "build_context"
  | "llm_call"
  | "tool_call"
  | "rag_retrieve"
  | "query_rewrite"
  | "bm25_search"
  | "vector_search"
  | "hybrid_fusion"
  | "parent_child_expand"
  | "rerank"
  | "build_prompt"
  | "final_answer"
  | "eval_metric";

export type RetrievalCandidateSource =
  | "dense"
  | "sparse"
  | "hybrid"
  | "parent"
  | "rerank";

export type TraceRunSummary = {
  id: string;
  run_type: TraceRunType;
  status: TraceStatus;
  title: string | null;
  input_preview: string;
  conversation_id: string | null;
  agent_run_id: string | null;
  user_message_id: string | null;
  provider: string | null;
  model: string | null;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
  total_tokens: number | null;
  estimated_cost: string | null;
  latency_ms: number | null;
  error_message: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type TraceStep = {
  id: string;
  trace_run_id: string;
  step_index: number;
  step_type: TraceStepType;
  name: string;
  status: TraceStatus;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown> | null;
  error_message: string | null;
  latency_ms: number | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type RagRetrievalCandidate = {
  id: string;
  retrieval_run_id: string;
  chunk_id: string;
  document_id: string;
  rank: number;
  final_rank: number | null;
  source: RetrievalCandidateSource;
  dense_score: number | null;
  sparse_score: number | null;
  fused_score: number | null;
  rerank_score: number | null;
  selected: boolean;
  content_preview: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type RagRetrievalRun = {
  id: string;
  trace_run_id: string;
  knowledge_base_id: string;
  strategy_name: "naive_vector";
  original_query: string;
  rewritten_query: string | null;
  top_k: number;
  candidate_count: number;
  selected_count: number;
  score_threshold: number | null;
  latency_ms: number;
  metadata_filter_json: Record<string, unknown>;
  strategy_config_json: Record<string, unknown>;
  created_at: string;
  candidates: RagRetrievalCandidate[];
};

export type TraceRunDetail = Omit<TraceRunSummary, "input_preview"> & {
  input_text: string;
  output_text: string | null;
  metadata_json: Record<string, unknown>;
  steps: TraceStep[];
  retrieval_runs: RagRetrievalRun[];
};
