import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


LLMToolName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]
LLMToolCallIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
NonBlankDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class LLMFunctionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: LLMToolName
    description: NonBlankDescription
    parameters: dict[str, Any]

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        copied = deepcopy(value)
        if copied.get("type") != "object":
            raise ValueError("tool parameters root must be an object")
        try:
            json.dumps(copied, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "tool parameters must be JSON serializable"
            ) from exc
        return copied


class LLMToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["function"] = "function"
    function: LLMFunctionDefinition


class LLMToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_call_id: LLMToolCallIdentifier
    tool_name: LLMToolName
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def copy_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        copied = deepcopy(value)
        try:
            json.dumps(copied, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "tool arguments must be JSON serializable"
            ) from exc
        return copied


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: tuple[LLMToolCall, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )
    tool_call_id: LLMToolCallIdentifier | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_message_shape(self) -> Self:
        if self.role in {"system", "user"}:
            if (
                self.content is None
                or self.tool_calls
                or self.tool_call_id is not None
            ):
                raise ValueError("text messages require content only")
            return self

        if self.role == "assistant":
            if self.tool_call_id is not None:
                raise ValueError(
                    "assistant messages must not include tool_call_id"
                )
            if not self.tool_calls and self.content is None:
                raise ValueError(
                    "assistant messages require content or tool calls"
                )
            tool_call_ids = [
                call.tool_call_id for call in self.tool_calls
            ]
            if len(tool_call_ids) != len(set(tool_call_ids)):
                raise ValueError("assistant tool call ids must be unique")
            return self

        if (
            self.content is None
            or self.tool_call_id is None
            or self.tool_calls
        ):
            raise ValueError(
                "tool messages require content and tool_call_id only"
            )
        return self


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    tools: tuple[LLMToolDefinition, ...] = ()


class TokenUsage(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class LLMResponse(BaseModel):
    id: str | None = None
    model: str
    content: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    tool_calls: tuple[LLMToolCall, ...] = ()

    @model_validator(mode="after")
    def validate_output(self) -> Self:
        if self.content is None and not self.tool_calls:
            raise ValueError("response requires content or tool calls")
        tool_call_ids = [call.tool_call_id for call in self.tool_calls]
        if len(tool_call_ids) != len(set(tool_call_ids)):
            raise ValueError("tool call ids must be unique")
        return self


class ChatChunk(BaseModel):
    id: str | None = None
    model: str | None = None
    content: str = ""
    finish_reason: str | None = None
    usage: TokenUsage | None = None


class LLMProviderError(RuntimeError):
    """LLM Provider 边界的基础异常。"""


class ProviderUnsupportedFeatureError(LLMProviderError):
    """Provider adapter 尚未支持请求的本地能力。"""


class ProviderConfigurationError(LLMProviderError):
    """Provider 配置缺失或无效。"""


class ProviderRequestError(LLMProviderError):
    """Provider HTTP 请求失败。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderAuthError(ProviderRequestError):
    """Provider 拒绝了服务端凭据。"""


class ProviderRateLimitError(ProviderRequestError):
    """Provider 已触发限流。"""


class ProviderTimeoutError(ProviderRequestError):
    """Provider 请求超时。"""


class ProviderBadRequestError(ProviderRequestError):
    """Provider 拒绝了请求。"""


class ProviderServerError(ProviderRequestError):
    """Provider 服务端失败。"""


class ProviderUnknownError(ProviderRequestError):
    """Provider 请求出现未分类故障。"""


class ProviderResponseError(LLMProviderError):
    """Provider 返回了无法解析的成功响应。"""


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise NotImplementedError
