from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LLMCallCreate(BaseModel):
    conversation_id: UUID
    message_id: UUID | None = None
    provider: str = Field(max_length=100)
    model: str = Field(max_length=255)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: Decimal | None = None
    latency_ms: int | None = None
    status: str = Field(default="pending", max_length=32)
    error_message: str | None = None


class LLMCallRead(LLMCallCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
