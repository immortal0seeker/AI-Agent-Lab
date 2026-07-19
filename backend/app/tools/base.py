import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


ToolName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: ToolName
    success: bool
    content: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_error_state(self) -> Self:
        if self.success and self.error is not None:
            raise ValueError("successful tool results must not include an error")
        if not self.success:
            if self.error is None or not self.error.strip():
                raise ValueError("failed tool results require a non-blank error")
            self.error = self.error.strip()
        return self


class ToolError(RuntimeError):
    """Tool 边界的基础异常。"""


class Tool(ABC):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters_schema: Mapping[str, Any],
        permission_level: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._name = self._normalize_tool_name(name)
        self._description = self._normalize_text(description, "description")
        self._permission_level = self._normalize_text(
            permission_level,
            "permission_level",
        )
        if not isinstance(parameters_schema, Mapping):
            raise TypeError("parameters_schema must be a mapping")
        if isinstance(timeout_seconds, bool) or not isinstance(
            timeout_seconds,
            (int, float),
        ):
            raise TypeError("timeout_seconds must be a number")
        if not math.isfinite(timeout_seconds):
            raise ValueError("timeout_seconds must be finite")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._parameters_schema = deepcopy(dict(parameters_schema))
        self._timeout_seconds = float(timeout_seconds)

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def permission_level(self) -> str:
        return self._permission_level

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return deepcopy(self._parameters_schema)

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @classmethod
    def _normalize_tool_name(cls, value: str) -> str:
        normalized = cls._normalize_text(value, "name", max_length=64)
        if _TOOL_NAME_PATTERN.fullmatch(normalized) is None:
            raise ValueError(
                "name must contain only letters, numbers, underscores, and hyphens"
            )
        return normalized

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
        *,
        max_length: int | None = None,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be blank")
        if max_length is not None and len(normalized) > max_length:
            raise ValueError(f"{field_name} must be at most {max_length} characters")
        return normalized

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        raise NotImplementedError
