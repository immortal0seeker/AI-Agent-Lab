import type { ApiMessage, TokenUsage } from "./chat";

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export type RagRetrievalRequest = {
  knowledge_base_id: string;
  query: string;
  top_k?: number;
  score_threshold?: number | null;
};

export type RagChatRequest = RagRetrievalRequest & {
  conversation_id: string;
  provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number | null;
};

export type RagRetrievalResult = {
  knowledge_base_id: string;
  document_id: string;
  chunk_id: string;
  embedding_provider: string;
  embedding_model: string;
  filename: string;
  chunk_index: number;
  content: string;
  score: number;
  heading: string | null;
  page_number: number | null;
  metadata: Record<string, JsonValue>;
};

export type RagSource = RagRetrievalResult & {
  source_index: number;
};

export type RagRetrievalMetadata = {
  strategy: "naive_vector";
  knowledge_base_id: string;
  top_k: number;
  score_threshold: number | null;
  result_count: number;
};

export type RagAnswerMetadata = RagRetrievalMetadata & {
  used_source_count: number;
  context_characters: number;
};

export type RagQueryResponse = {
  rag_query_id: string;
  results: RagRetrievalResult[];
  metadata: RagRetrievalMetadata;
};

export type RagChatResponse = {
  conversation_id: string;
  rag_query_id: string;
  user_message: ApiMessage;
  assistant_message: ApiMessage;
  answer: string;
  sources: RagSource[];
  metadata: RagAnswerMetadata;
  provider: string;
  model: string;
  usage: TokenUsage | null;
  llm_call_id: string;
};

export type RagTurn = {
  query: string;
  conversation_id: string;
  rag_query_id: string;
  user_message: ApiMessage;
  assistant_message: ApiMessage;
  answer: string;
  sources: RagSource[];
  metadata: RagAnswerMetadata;
  provider: string;
  model: string;
  usage: TokenUsage | null;
  llm_call_id: string;
};
