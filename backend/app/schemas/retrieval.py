from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)


RetrievalStrategyName = Literal["naive_vector"]
RetrievalCandidateSource = Literal[
    "dense",
    "sparse",
    "hybrid",
    "parent",
    "rerank",
]
PromptVersion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class RagRetrievalRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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
    score_threshold: FiniteFloat | None = None
    latency_ms: StrictInt = Field(ge=0)
    metadata_filter_json: dict[str, JsonValue] = Field(default_factory=dict)
    strategy_config_json: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("original_query", "rewritten_query")
    @classmethod
    def reject_blank_query(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("query must not be blank")
        return value

    @field_validator("score_threshold", mode="before")
    @classmethod
    def reject_coerced_threshold(cls, value: object) -> object:
        return _reject_coerced_number(value)

    @model_validator(mode="after")
    def validate_selected_count(self) -> Self:
        if self.selected_count > self.candidate_count:
            raise ValueError("selected_count must not exceed candidate_count")
        return self


class RagRetrievalCandidateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    retrieval_run_id: UUID
    document_id: UUID
    chunk_id: UUID
    rank: StrictInt = Field(gt=0, le=100)
    final_rank: StrictInt | None = Field(default=None, gt=0, le=100)
    source: RetrievalCandidateSource
    dense_score: FiniteFloat | None = None
    sparse_score: FiniteFloat | None = None
    fused_score: FiniteFloat | None = None
    rerank_score: FiniteFloat | None = None
    selected: StrictBool
    content_preview: str = Field(min_length=1, max_length=500)
    metadata_json: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator(
        "dense_score",
        "sparse_score",
        "fused_score",
        "rerank_score",
        mode="before",
    )
    @classmethod
    def reject_coerced_scores(cls, value: object) -> object:
        return _reject_coerced_number(value)

    @field_validator("content_preview")
    @classmethod
    def reject_blank_preview(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content_preview must not be blank")
        return value


class RagRetrieveStepInputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    strategy: RetrievalStrategyName
    top_k: StrictInt = Field(ge=1, le=100)
    score_threshold: FiniteFloat | None = None

    @field_validator("score_threshold", mode="before")
    @classmethod
    def reject_coerced_threshold(cls, value: object) -> object:
        return _reject_coerced_number(value)


class RagRetrieveStepOutputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    retrieval_run_id: UUID
    candidate_count: StrictInt = Field(ge=0, le=100)
    selected_count: StrictInt = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_selected_count(self) -> Self:
        if self.selected_count > self.candidate_count:
            raise ValueError("selected_count must not exceed candidate_count")
        return self


class RagPromptStepInputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_version: PromptVersion
    retrieval_run_id: UUID
    candidate_count: StrictInt = Field(ge=0, le=100)


class RagPromptSourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_index: StrictInt = Field(gt=0, le=100)
    candidate_id: UUID
    document_id: UUID
    chunk_id: UUID
    included_characters: StrictInt = Field(ge=0, le=1_000_000)
    truncated: StrictBool


class RagPromptStepOutputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_version: PromptVersion
    context_characters: StrictInt = Field(ge=0, le=1_000_000)
    used_source_count: StrictInt = Field(ge=0, le=100)
    sources: tuple[RagPromptSourceMetadata, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def validate_source_order(self) -> Self:
        if self.used_source_count != len(self.sources):
            raise ValueError("used_source_count must match sources")
        if [item.source_index for item in self.sources] != list(
            range(1, len(self.sources) + 1)
        ):
            raise ValueError("prompt sources must be contiguous and ordered")
        return self


class RagFinalAnswerStepInputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_version: PromptVersion
    retrieval_run_id: UUID
    used_source_count: StrictInt = Field(ge=0, le=100)


class RagFinalAnswerStepOutputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rag_query_id: UUID
    answer_message_id: UUID
    llm_call_id: UUID
    source_count: StrictInt = Field(ge=0, le=100)
    answer_characters: StrictInt = Field(gt=0, le=20_000_000)


def _reject_coerced_number(value: object) -> object:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, (int, float))
    ):
        raise ValueError("value must be a number")
    return value
