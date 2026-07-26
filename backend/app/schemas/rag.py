from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


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
