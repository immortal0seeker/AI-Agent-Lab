from datetime import datetime
from typing import Annotated, Any, Self
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


RetrievalFilename = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
RetrievalHeading = Annotated[str, StringConstraints(max_length=512)]


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    document_id: UUID
    chunk_id: UUID
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


class RagQueryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    knowledge_base_id: UUID
    query: str
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
