from datetime import datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.providers.llm.base import TokenUsage
from app.schemas.message import MessageRead


RetrievalFilename = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
RetrievalHeading = Annotated[str, StringConstraints(max_length=512)]
EmbeddingProviderIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
EmbeddingModelIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
RagIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    document_id: UUID
    chunk_id: UUID
    embedding_provider: EmbeddingProviderIdentifier
    embedding_model: EmbeddingModelIdentifier
    filename: RetrievalFilename
    chunk_index: StrictInt = Field(ge=0)
    content: str
    score: FiniteFloat
    heading: RetrievalHeading | None = None
    page_number: StrictInt | None = Field(default=None, gt=0)
    metadata: dict[str, JsonValue]

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("content must not be blank")
        return value

    @field_validator("score", mode="before")
    @classmethod
    def reject_coerced_score(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("score must be a number")
        return value


class RagSource(RetrievalResult):
    source_index: StrictInt = Field(gt=0)


class RagRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    query: str = Field(min_length=1, max_length=20_000)
    top_k: StrictInt = Field(default=5, ge=1, le=100)
    score_threshold: FiniteFloat | None = None

    @field_validator("query")
    @classmethod
    def reject_blank_retrieval_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value

    @field_validator("score_threshold", mode="before")
    @classmethod
    def reject_coerced_score_threshold(cls, value: object) -> object:
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError("score_threshold must be a number")
        return value


class RagChatRequest(RagRetrievalRequest):
    conversation_id: UUID
    provider: RagIdentifier = Field(max_length=100)
    model: RagIdentifier = Field(max_length=255)
    temperature: FiniteFloat = Field(default=0.2, ge=0, le=2)
    max_tokens: StrictInt | None = Field(default=None, gt=0)

    @field_validator("temperature", mode="before")
    @classmethod
    def reject_coerced_temperature(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("temperature must be a number")
        return value


class RagRetrievalMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: Literal["naive_vector"] = "naive_vector"
    knowledge_base_id: UUID
    top_k: StrictInt = Field(ge=1, le=100)
    score_threshold: FiniteFloat | None = None
    result_count: StrictInt = Field(ge=0, le=100)


class RagAnswerMetadata(RagRetrievalMetadata):
    used_source_count: StrictInt = Field(ge=0, le=100)
    context_characters: StrictInt = Field(ge=0, le=1_000_000)


class RagQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rag_query_id: UUID
    results: tuple[RetrievalResult, ...]
    metadata: RagRetrievalMetadata


class RagChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conversation_id: UUID
    rag_query_id: UUID
    user_message: MessageRead
    assistant_message: MessageRead
    answer: str
    sources: tuple[RagSource, ...]
    metadata: RagAnswerMetadata
    provider: RagIdentifier = Field(max_length=100)
    model: RagIdentifier = Field(max_length=255)
    usage: TokenUsage | None = None
    llm_call_id: UUID

    @field_validator("answer")
    @classmethod
    def reject_blank_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("answer must not be blank")
        return value


class RagQueryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    knowledge_base_id: UUID
    query: str
    top_k: StrictInt = Field(default=5, ge=1, le=100)
    retrieved_chunks_json: list[dict[str, Any]] = Field(default_factory=list)
    answer_message_id: UUID | None = None
    latency_ms: int | None = Field(default=None, ge=0)

    @field_validator("query")
    @classmethod
    def reject_blank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value

    @model_validator(mode="after")
    def require_conversation_for_answer(self) -> Self:
        if self.answer_message_id is not None and self.conversation_id is None:
            raise ValueError("answer_message_id requires conversation_id")
        return self


class RagQueryRead(RagQueryCreate):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    created_at: datetime
