import importlib
from types import ModuleType
from uuid import UUID

import pytest
from pydantic import ValidationError


TRACE_RUN_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVAL_RUN_ID = UUID("00000000-0000-0000-0000-000000000002")
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000003")
KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000004")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000005")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000006")
RAG_QUERY_ID = UUID("00000000-0000-0000-0000-000000000007")
MESSAGE_ID = UUID("00000000-0000-0000-0000-000000000008")
LLM_CALL_ID = UUID("00000000-0000-0000-0000-000000000009")


@pytest.fixture
def schemas() -> ModuleType:
    try:
        return importlib.import_module("app.schemas.retrieval")
    except ModuleNotFoundError:
        pytest.fail(
            "RAG retrieval Trace schemas are not implemented",
            pytrace=False,
        )


def test_retrieval_record_schemas_serialize_exact_contract(
    schemas: ModuleType,
) -> None:
    run = schemas.RagRetrievalRunCreate(
        trace_run_id=TRACE_RUN_ID,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        strategy_name="naive_vector",
        original_query="What is the architecture?",
        top_k=3,
        candidate_count=1,
        selected_count=1,
        score_threshold=0.5,
        latency_ms=7,
        metadata_filter_json={
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "embedding_provider": "mock",
            "embedding_model": "mock-embedding",
        },
        strategy_config_json={},
    )
    candidate = schemas.RagRetrievalCandidateCreate(
        id=CANDIDATE_ID,
        retrieval_run_id=RETRIEVAL_RUN_ID,
        document_id=DOCUMENT_ID,
        chunk_id=CHUNK_ID,
        rank=1,
        final_rank=1,
        source="dense",
        dense_score=0.93,
        selected=True,
        content_preview="Bounded source preview",
        metadata_json={"filename": "guide.md", "chunk_index": 0},
    )

    assert run.model_dump(mode="json") == {
        "trace_run_id": str(TRACE_RUN_ID),
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "strategy_name": "naive_vector",
        "original_query": "What is the architecture?",
        "rewritten_query": None,
        "top_k": 3,
        "candidate_count": 1,
        "selected_count": 1,
        "score_threshold": 0.5,
        "latency_ms": 7,
        "metadata_filter_json": {
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "embedding_provider": "mock",
            "embedding_model": "mock-embedding",
        },
        "strategy_config_json": {},
    }
    assert candidate.model_dump(mode="json") == {
        "id": str(CANDIDATE_ID),
        "retrieval_run_id": str(RETRIEVAL_RUN_ID),
        "document_id": str(DOCUMENT_ID),
        "chunk_id": str(CHUNK_ID),
        "rank": 1,
        "final_rank": 1,
        "source": "dense",
        "dense_score": 0.93,
        "sparse_score": None,
        "fused_score": None,
        "rerank_score": None,
        "selected": True,
        "content_preview": "Bounded source preview",
        "metadata_json": {"filename": "guide.md", "chunk_index": 0},
    }


def test_rag_step_metadata_serializes_exact_contract(
    schemas: ModuleType,
) -> None:
    retrieve_input = schemas.RagRetrieveStepInputMetadata(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        strategy="naive_vector",
        top_k=3,
        score_threshold=0.5,
    )
    retrieve_output = schemas.RagRetrieveStepOutputMetadata(
        retrieval_run_id=RETRIEVAL_RUN_ID,
        candidate_count=1,
        selected_count=1,
    )
    prompt_input = schemas.RagPromptStepInputMetadata(
        prompt_version="naive-rag-v1",
        retrieval_run_id=RETRIEVAL_RUN_ID,
        candidate_count=1,
    )
    prompt_output = schemas.RagPromptStepOutputMetadata(
        prompt_version="naive-rag-v1",
        context_characters=120,
        used_source_count=1,
        sources=(
            schemas.RagPromptSourceMetadata(
                source_index=1,
                candidate_id=CANDIDATE_ID,
                document_id=DOCUMENT_ID,
                chunk_id=CHUNK_ID,
                included_characters=80,
                truncated=False,
            ),
        ),
    )
    final_input = schemas.RagFinalAnswerStepInputMetadata(
        prompt_version="naive-rag-v1",
        retrieval_run_id=RETRIEVAL_RUN_ID,
        used_source_count=1,
    )
    final_output = schemas.RagFinalAnswerStepOutputMetadata(
        rag_query_id=RAG_QUERY_ID,
        answer_message_id=MESSAGE_ID,
        llm_call_id=LLM_CALL_ID,
        source_count=1,
        answer_characters=42,
    )

    assert retrieve_input.model_dump(mode="json") == {
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "strategy": "naive_vector",
        "top_k": 3,
        "score_threshold": 0.5,
    }
    assert retrieve_output.model_dump(mode="json") == {
        "retrieval_run_id": str(RETRIEVAL_RUN_ID),
        "candidate_count": 1,
        "selected_count": 1,
    }
    assert prompt_input.model_dump(mode="json") == {
        "prompt_version": "naive-rag-v1",
        "retrieval_run_id": str(RETRIEVAL_RUN_ID),
        "candidate_count": 1,
    }
    assert prompt_output.model_dump(mode="json") == {
        "prompt_version": "naive-rag-v1",
        "context_characters": 120,
        "used_source_count": 1,
        "sources": [
            {
                "source_index": 1,
                "candidate_id": str(CANDIDATE_ID),
                "document_id": str(DOCUMENT_ID),
                "chunk_id": str(CHUNK_ID),
                "included_characters": 80,
                "truncated": False,
            }
        ],
    }
    assert final_input.model_dump(mode="json") == {
        "prompt_version": "naive-rag-v1",
        "retrieval_run_id": str(RETRIEVAL_RUN_ID),
        "used_source_count": 1,
    }
    assert final_output.model_dump(mode="json") == {
        "rag_query_id": str(RAG_QUERY_ID),
        "answer_message_id": str(MESSAGE_ID),
        "llm_call_id": str(LLM_CALL_ID),
        "source_count": 1,
        "answer_characters": 42,
    }


@pytest.mark.parametrize(
    ("schema_name", "payload"),
    [
        (
            "RagRetrievalRunCreate",
            {
                "trace_run_id": TRACE_RUN_ID,
                "knowledge_base_id": KNOWLEDGE_BASE_ID,
                "strategy_name": "naive_vector",
                "original_query": "Question",
                "top_k": 1,
                "candidate_count": 0,
                "selected_count": 1,
                "latency_ms": 0,
            },
        ),
        (
            "RagRetrievalCandidateCreate",
            {
                "retrieval_run_id": RETRIEVAL_RUN_ID,
                "document_id": DOCUMENT_ID,
                "chunk_id": CHUNK_ID,
                "rank": True,
                "final_rank": 1,
                "source": "dense",
                "dense_score": 0.9,
                "selected": True,
                "content_preview": "preview",
            },
        ),
        (
            "RagRetrievalCandidateCreate",
            {
                "retrieval_run_id": RETRIEVAL_RUN_ID,
                "document_id": DOCUMENT_ID,
                "chunk_id": CHUNK_ID,
                "rank": 1,
                "final_rank": 1,
                "source": "dense",
                "dense_score": float("nan"),
                "selected": True,
                "content_preview": "preview",
            },
        ),
        (
            "RagRetrievalCandidateCreate",
            {
                "retrieval_run_id": RETRIEVAL_RUN_ID,
                "document_id": DOCUMENT_ID,
                "chunk_id": CHUNK_ID,
                "rank": 1,
                "final_rank": 1,
                "source": "unknown",
                "dense_score": 0.9,
                "selected": True,
                "content_preview": "preview",
            },
        ),
        (
            "RagRetrievalCandidateCreate",
            {
                "retrieval_run_id": RETRIEVAL_RUN_ID,
                "document_id": DOCUMENT_ID,
                "chunk_id": CHUNK_ID,
                "rank": 1,
                "final_rank": 1,
                "source": "dense",
                "dense_score": 0.9,
                "selected": True,
                "content_preview": "x" * 501,
            },
        ),
        (
            "RagRetrieveStepInputMetadata",
            {
                "knowledge_base_id": KNOWLEDGE_BASE_ID,
                "strategy": "naive_vector",
                "top_k": 0,
            },
        ),
        (
            "RagPromptStepOutputMetadata",
            {
                "prompt_version": "naive-rag-v1",
                "context_characters": 1,
                "used_source_count": 1,
                "sources": [],
            },
        ),
        (
            "RagFinalAnswerStepOutputMetadata",
            {
                "rag_query_id": RAG_QUERY_ID,
                "answer_message_id": MESSAGE_ID,
                "llm_call_id": LLM_CALL_ID,
                "source_count": 0,
                "answer_characters": 0,
            },
        ),
    ],
)
def test_retrieval_schemas_reject_invalid_values(
    schemas: ModuleType,
    schema_name: str,
    payload: dict[str, object],
) -> None:
    schema = getattr(schemas, schema_name)

    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_prompt_sources_must_have_contiguous_order(
    schemas: ModuleType,
) -> None:
    with pytest.raises(ValidationError):
        schemas.RagPromptStepOutputMetadata(
            prompt_version="naive-rag-v1",
            context_characters=20,
            used_source_count=1,
            sources=(
                schemas.RagPromptSourceMetadata(
                    source_index=2,
                    candidate_id=CANDIDATE_ID,
                    document_id=DOCUMENT_ID,
                    chunk_id=CHUNK_ID,
                    included_characters=10,
                    truncated=False,
                ),
            ),
        )


def test_retrieval_schemas_reject_unknown_fields(schemas: ModuleType) -> None:
    with pytest.raises(ValidationError):
        schemas.RagRetrieveStepInputMetadata(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            strategy="naive_vector",
            top_k=3,
            score_threshold=None,
            raw_vector=[0.1, 0.2],
        )
