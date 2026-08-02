from enum import StrEnum


class TraceRunType(StrEnum):
    CHAT = "chat"
    AGENT = "agent"
    RAG_QUERY = "rag_query"
    RAG_CHAT = "rag_chat"
    EVALUATION = "evaluation"
    TOOL = "tool"


class TraceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TraceStepType(StrEnum):
    BUILD_CONTEXT = "build_context"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RAG_RETRIEVE = "rag_retrieve"
    QUERY_REWRITE = "query_rewrite"
    BM25_SEARCH = "bm25_search"
    VECTOR_SEARCH = "vector_search"
    HYBRID_FUSION = "hybrid_fusion"
    PARENT_CHILD_EXPAND = "parent_child_expand"
    RERANK = "rerank"
    BUILD_PROMPT = "build_prompt"
    FINAL_ANSWER = "final_answer"
    EVAL_METRIC = "eval_metric"
