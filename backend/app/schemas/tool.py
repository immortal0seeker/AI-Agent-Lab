from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.tools import ToolResult


ToolCallStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "timeout",
    "blocked",
]
ToolCallIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
ToolIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: ToolCallIdentifier
    tool_name: ToolIdentifier
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: ToolCallIdentifier
    tool_name: ToolIdentifier
    status: ToolCallStatus
    result: ToolResult | None = None

    @model_validator(mode="after")
    def validate_result_state(self) -> Self:
        if self.status in {"pending", "running"}:
            if self.result is not None:
                raise ValueError("non-terminal tool calls must not include a result")
            return self
        if self.result is None:
            raise ValueError("terminal tool calls require a result")
        if self.result.tool_name != self.tool_name:
            raise ValueError("tool call and result names must match")
        if (self.status == "success") != self.result.success:
            raise ValueError("tool call status and result success must agree")
        return self
