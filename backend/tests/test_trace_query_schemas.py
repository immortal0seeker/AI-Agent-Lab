from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.trace import TraceStepRead
from app.schemas.trace_query import (
    RagRetrievalCandidateRead,
    RagRetrievalRunRead,
    TraceRunDetailRead,
    TraceRunSummaryRead,
)


TRACE_ID = UUID(int=1)
STEP_ID = UUID(int=2)
RETRIEVAL_ID = UUID(int=3)
CANDIDATE_ID = UUID(int=4)
KNOWLEDGE_BASE_ID = UUID(int=5)
DOCUMENT_ID = UUID(int=6)
CHUNK_ID = UUID(int=7)
CONVERSATION_ID = UUID(int=8)
USER_MESSAGE_ID = UUID(int=9)
NOW = datetime(2026, 8, 9, 12, 0, 0)


def make_candidate(**overrides: object) -> RagRetrievalCandidateRead:
    values: dict[str, object] = {
        "id": CANDIDATE_ID,
        "retrieval_run_id": RETRIEVAL_ID,
        "chunk_id": CHUNK_ID,
        "document_id": DOCUMENT_ID,
        "rank": 1,
        "final_rank": 1,
        "source": "dense",
        "dense_score": 0.91,
        "sparse_score": None,
        "fused_score": None,
        "rerank_score": None,
        "selected": True,
        "content_preview": "Architecture source",
        "metadata_json": {"filename": "architecture.md"},
        "created_at": NOW,
    }
    values.update(overrides)
    return RagRetrievalCandidateRead(**values)


def make_retrieval(**overrides: object) -> RagRetrievalRunRead:
    values: dict[str, object] = {
        "id": RETRIEVAL_ID,
        "trace_run_id": TRACE_ID,
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "strategy_name": "naive_vector",
        "original_query": "Where is the design?",
        "rewritten_query": None,
        "top_k": 5,
        "candidate_count": 1,
        "selected_count": 1,
        "score_threshold": 0.5,
        "latency_ms": 12,
        "metadata_filter_json": {"embedding_model": "mock-embedding"},
        "strategy_config_json": {},
        "created_at": NOW,
        "candidates": [make_candidate()],
    }
    values.update(overrides)
    return RagRetrievalRunRead(**values)


def test_trace_detail_schema_serializes_nested_public_contract() -> None:
    step = TraceStepRead(
        id=STEP_ID,
        trace_run_id=TRACE_ID,
        step_index=1,
        step_type="rag_retrieve",
        name="Retrieve knowledge base",
        status="completed",
        input_json={"top_k": 5},
        output_json={"retrieval_run_id": str(RETRIEVAL_ID)},
        error_message=None,
        latency_ms=12,
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
    )
    detail = TraceRunDetailRead(
        id=TRACE_ID,
        run_type="rag_chat",
        conversation_id=CONVERSATION_ID,
        agent_run_id=None,
        user_message_id=USER_MESSAGE_ID,
        title=None,
        status="completed",
        input_text="Where is the design?",
        output_text="The design is in the architecture document.",
        provider="mock",
        model="mock-chat",
        total_input_tokens=7,
        total_output_tokens=5,
        total_tokens=12,
        estimated_cost=Decimal("0.00000700"),
        latency_ms=18,
        error_message=None,
        metadata_json={"prompt_version": "naive-rag-v1"},
        started_at=NOW,
        ended_at=NOW,
        created_at=NOW,
        steps=[step],
        retrieval_runs=[make_retrieval()],
    )

    payload = detail.model_dump(mode="json")

    assert payload["id"] == str(TRACE_ID)
    assert payload["created_at"] == "2026-08-09T12:00:00"
    assert payload["steps"][0]["step_index"] == 1
    assert payload["retrieval_runs"][0]["candidates"][0]["rank"] == 1
    assert payload["estimated_cost"] == "0.00000700"


def test_trace_summary_accepts_unicode_preview_at_160_characters() -> None:
    preview = "界" * 160

    summary = TraceRunSummaryRead(
        id=TRACE_ID,
        run_type="rag_chat",
        status="completed",
        title=None,
        input_preview=preview,
        conversation_id=None,
        agent_run_id=None,
        user_message_id=None,
        provider=None,
        model=None,
        total_input_tokens=None,
        total_output_tokens=None,
        total_tokens=None,
        estimated_cost=None,
        latency_ms=0,
        error_message=None,
        started_at=None,
        ended_at=None,
        created_at=NOW,
    )

    assert summary.input_preview == preview


@pytest.mark.parametrize(
    ("schema_factory", "overrides"),
    [
        (make_candidate, {"rank": 0}),
        (make_candidate, {"final_rank": 0}),
        (make_candidate, {"latency_ms": 1}),
        (make_candidate, {"dense_score": float("nan")}),
        (make_candidate, {"content_preview": "   "}),
        (make_candidate, {"metadata_json": {"unsafe": object()}}),
        (make_retrieval, {"top_k": 0}),
        (make_retrieval, {"selected_count": 2}),
        (make_retrieval, {"latency_ms": -1}),
    ],
)
def test_trace_query_schemas_reject_invalid_public_values(
    schema_factory: object,
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema_factory(**overrides)  # type: ignore[operator]


def test_trace_summary_rejects_preview_over_160_characters_and_unknown_fields() -> None:
    common: dict[str, object] = {
        "id": TRACE_ID,
        "run_type": "rag_chat",
        "status": "completed",
        "title": None,
        "input_preview": "界" * 161,
        "conversation_id": None,
        "agent_run_id": None,
        "user_message_id": None,
        "provider": None,
        "model": None,
        "total_input_tokens": None,
        "total_output_tokens": None,
        "total_tokens": None,
        "estimated_cost": None,
        "latency_ms": 0,
        "error_message": None,
        "started_at": None,
        "ended_at": None,
        "created_at": NOW,
    }
    with pytest.raises(ValidationError):
        TraceRunSummaryRead(**common)

    common["input_preview"] = "valid"
    common["unknown"] = True
    with pytest.raises(ValidationError):
        TraceRunSummaryRead(**common)

