from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    conversation_id: UUID
    role: str = Field(max_length=32)
    content: str
    model: str | None = Field(default=None, max_length=255)
    provider: str | None = Field(default=None, max_length=100)


class MessageRead(MessageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
