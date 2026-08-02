from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)


TraceProviderIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
TraceModelIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class TraceRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_type: TraceRunType
    conversation_id: UUID | None = None
    agent_run_id: UUID | None = None
    user_message_id: UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    input_text: str = Field(min_length=1)
    provider: TraceProviderIdentifier | None = None
    model: TraceModelIdentifier | None = None
    status: TraceStatus = TraceStatus.PENDING
    metadata_json: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("input_text")
    @classmethod
    def reject_blank_input_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input_text must not be blank")
        return value

    @model_validator(mode="after")
    def require_conversation_for_owned_correlations(self) -> Self:
        if self.conversation_id is None and (
            self.agent_run_id is not None or self.user_message_id is not None
        ):
            raise ValueError(
                "conversation_id is required for agent_run_id or user_message_id"
            )
        return self


class TraceRunRead(TraceRunCreate):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    output_text: str | None
    total_input_tokens: StrictInt | None = Field(default=None, ge=0)
    total_output_tokens: StrictInt | None = Field(default=None, ge=0)
    total_tokens: StrictInt | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    latency_ms: StrictInt | None = Field(default=None, ge=0)
    error_message: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class TraceStepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_run_id: UUID
    step_index: StrictInt = Field(gt=0)
    step_type: TraceStepType
    name: str = Field(min_length=1, max_length=255)
    status: TraceStatus = TraceStatus.PENDING
    input_json: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value


class TraceStepRead(TraceStepCreate):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    output_json: dict[str, JsonValue] | None
    error_message: str | None
    latency_ms: StrictInt | None = Field(default=None, ge=0)
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
