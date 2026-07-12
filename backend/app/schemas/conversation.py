from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)
    default_provider: str | None = Field(default=None, max_length=100)
    default_model: str | None = Field(default=None, max_length=255)


class ConversationRead(ConversationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
