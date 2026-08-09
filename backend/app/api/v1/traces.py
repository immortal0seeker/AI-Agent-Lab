from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_trace_query_service
from app.schemas.trace import TraceRunRead, TraceStepRead
from app.schemas.trace_query import (
    RagRetrievalCandidateRead,
    RagRetrievalRunRead,
    TraceRunDetailRead,
    TraceRunSummaryRead,
)
from app.services.trace_query_service import (
    TraceDetail,
    TraceQueryService,
    TraceRetrievalDetail,
    TraceRunListItem,
)


router = APIRouter(prefix="/traces", tags=["traces"])


def to_trace_summary(item: TraceRunListItem) -> TraceRunSummaryRead:
    row = item.record
    return TraceRunSummaryRead(
        id=row.id,
        run_type=row.run_type,
        status=row.status,
        title=row.title,
        input_preview=item.input_preview,
        conversation_id=row.conversation_id,
        agent_run_id=row.agent_run_id,
        user_message_id=row.user_message_id,
        provider=row.provider,
        model=row.model,
        total_input_tokens=row.total_input_tokens,
        total_output_tokens=row.total_output_tokens,
        total_tokens=row.total_tokens,
        estimated_cost=row.estimated_cost,
        latency_ms=row.latency_ms,
        error_message=row.error_message,
        started_at=row.started_at,
        ended_at=row.ended_at,
        created_at=row.created_at,
    )


def to_retrieval_read(item: TraceRetrievalDetail) -> RagRetrievalRunRead:
    row = item.record
    return RagRetrievalRunRead(
        id=row.id,
        trace_run_id=row.trace_run_id,
        knowledge_base_id=row.knowledge_base_id,
        strategy_name=row.strategy_name,
        original_query=row.original_query,
        rewritten_query=row.rewritten_query,
        top_k=row.top_k,
        candidate_count=row.candidate_count,
        selected_count=row.selected_count,
        score_threshold=row.score_threshold,
        latency_ms=row.latency_ms,
        metadata_filter_json=row.metadata_filter_json,
        strategy_config_json=row.strategy_config_json,
        created_at=row.created_at,
        candidates=[
            RagRetrievalCandidateRead.model_validate(candidate)
            for candidate in item.candidates
        ],
    )


def to_trace_detail(detail: TraceDetail) -> TraceRunDetailRead:
    run = TraceRunRead.model_validate(detail.record)
    return TraceRunDetailRead(
        **run.model_dump(),
        steps=[TraceStepRead.model_validate(step) for step in detail.steps],
        retrieval_runs=[to_retrieval_read(item) for item in detail.retrievals],
    )


@router.get("", response_model=list[TraceRunSummaryRead])
def list_trace_runs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    service: TraceQueryService = Depends(get_trace_query_service),
) -> list[TraceRunSummaryRead]:
    return [
        to_trace_summary(item)
        for item in service.list_trace_runs(limit=limit)
    ]


@router.get("/{trace_run_id}", response_model=TraceRunDetailRead)
def get_trace_run_detail(
    trace_run_id: UUID,
    service: TraceQueryService = Depends(get_trace_query_service),
) -> TraceRunDetailRead:
    return to_trace_detail(service.get_trace_detail(trace_run_id))
