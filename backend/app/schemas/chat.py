from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.providers.llm.base import TokenUsage
from app.schemas.message import MessageRead


NonEmptyIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ChatCompletionRequest(BaseModel):
    conversation_id: UUID | None = None
    provider: NonEmptyIdentifier = Field(max_length=100)
    model: NonEmptyIdentifier = Field(max_length=255)
    content: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class ChatCompletionResponse(BaseModel):
    conversation_id: UUID
    user_message: MessageRead
    assistant_message: MessageRead
    provider: str
    model: str
    usage: TokenUsage | None = None
    llm_call_id: UUID


class ChatStreamDeltaResponse(BaseModel):
    content: str
