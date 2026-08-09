from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from app.observability.trace_types import TraceRunType, TraceStatus
from app.schemas.retrieval import RetrievalCandidateSource, RetrievalStrategyName
from app.schemas.trace import (
    TraceModelIdentifier,
    TraceProviderIdentifier,
    TraceRunRead,
    TraceStepRead,
)


class TraceRunSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    run_type: TraceRunType
    status: TraceStatus
    title: str | None
    input_preview: str = Field(min_length=1, max_length=160)
    conversation_id: UUID | None
    agent_run_id: UUID | None
    user_message_id: UUID | None
    provider: TraceProviderIdentifier | None
    model: TraceModelIdentifier | None
    total_input_tokens: StrictInt | None = Field(default=None, ge=0)
    total_output_tokens: StrictInt | None = Field(default=None, ge=0)
    total_tokens: StrictInt | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    latency_ms: StrictInt | None = Field(default=None, ge=0)
    error_message: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    @field_validator("input_preview")
    @classmethod
    def reject_blank_preview(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input_preview must not be blank")
        return value


class RagRetrievalCandidateRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    retrieval_run_id: UUID
    chunk_id: UUID
    document_id: UUID
    rank: StrictInt = Field(gt=0, le=100)
    final_rank: StrictInt | None = Field(default=None, gt=0, le=100)
    source: RetrievalCandidateSource
    dense_score: FiniteFloat | None = None
    sparse_score: FiniteFloat | None = None
    fused_score: FiniteFloat | None = None
    rerank_score: FiniteFloat | None = None
    selected: StrictBool
    content_preview: str = Field(min_length=1, max_length=500)
    metadata_json: dict[str, JsonValue]
    created_at: datetime

    @field_validator("content_preview")
    @classmethod
    def reject_blank_preview(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content_preview must not be blank")
        return value


class RagRetrievalRunRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    trace_run_id: UUID
    knowledge_base_id: UUID
    strategy_name: RetrievalStrategyName
    original_query: str = Field(min_length=1, max_length=20_000)
    rewritten_query: str | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
    )
    top_k: StrictInt = Field(ge=1, le=100)
    candidate_count: StrictInt = Field(ge=0, le=100)
    selected_count: StrictInt = Field(ge=0, le=100)
    score_threshold: FiniteFloat | None
    latency_ms: StrictInt = Field(ge=0)
    metadata_filter_json: dict[str, JsonValue]
    strategy_config_json: dict[str, JsonValue]
    created_at: datetime
    candidates: list[RagRetrievalCandidateRead]

    @field_validator("original_query", "rewritten_query")
    @classmethod
    def reject_blank_query(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("query must not be blank")
        return value

    @model_validator(mode="after")
    def validate_selected_count(self) -> Self:
        if self.selected_count > self.candidate_count:
            raise ValueError("selected_count must not exceed candidate_count")
        return self


class TraceRunDetailRead(TraceRunRead):
    steps: list[TraceStepRead]
    retrieval_runs: list[RagRetrievalRunRead]
