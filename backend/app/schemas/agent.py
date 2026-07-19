from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.schemas.tool import ToolCallStatus
from app.tools import ToolResult


NonEmptyIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
AgentRunStatus = Literal[
    "created",
    "running",
    "waiting_tool",
    "completed",
    "failed",
    "cancelled",
]


class AgentRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    provider: NonEmptyIdentifier = Field(max_length=100)
    model: NonEmptyIdentifier = Field(max_length=255)
    input: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    max_steps: int = Field(default=3, ge=1, le=10, strict=True)

    @field_validator("input")
    @classmethod
    def reject_blank_input(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input must not be blank")
        return value


class AgentRunRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    conversation_id: UUID
    user_message_id: UUID | None
    status: AgentRunStatus
    goal: str
    final_answer: str | None
    error: str | None
    started_at: datetime | None
    ended_at: datetime | None
    latency_ms: int | None = Field(ge=0)
    created_at: datetime


class ToolCallRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tool_call_id: str
    agent_run_id: UUID
    conversation_id: UUID
    tool_name: str
    arguments: dict[str, Any]
    result: ToolResult | None
    status: ToolCallStatus
    error: str | None
    started_at: datetime | None
    ended_at: datetime | None
    latency_ms: int | None = Field(ge=0)
    created_at: datetime


class AgentRunExecutionRead(AgentRunRead):
    tool_calls: list[ToolCallRead] = Field(default_factory=list)
