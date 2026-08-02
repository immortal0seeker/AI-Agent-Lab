export type KnowledgeBaseCreate = {
  name: string;
  description?: string | null;
  embedding_provider?: string | null;
  embedding_model?: string | null;
  vector_store?: string;
  vector_collection_name?: string | null;
};

export type KnowledgeBase = {
  id: string;
  name: string;
  description: string | null;
  embedding_provider: string | null;
  embedding_model: string | null;
  vector_store: string;
  vector_collection_name: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentFileType = "md" | "txt" | "pdf";

export type DocumentParseStatus =
  | "uploaded"
  | "parsing"
  | "parsed"
  | "failed";

export type DocumentChunkStatus =
  | "pending"
  | "chunking"
  | "chunked"
  | "failed";

export type DocumentEmbeddingStatus =
  | "pending"
  | "embedding"
  | "ready"
  | "failed";

export type KnowledgeDocument = {
  id: string;
  knowledge_base_id: string;
  filename: string;
  original_filename: string;
  file_type: DocumentFileType;
  file_path: string;
  file_size: number;
  file_hash: string;
  parse_status: DocumentParseStatus;
  chunk_status: DocumentChunkStatus;
  embedding_status: DocumentEmbeddingStatus;
  error_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};
