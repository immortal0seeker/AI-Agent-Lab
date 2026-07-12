from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)


class TokenUsage(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class LLMResponse(BaseModel):
    id: str | None = None
    model: str
    content: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None


class ChatChunk(BaseModel):
    id: str | None = None
    model: str | None = None
    content: str = ""
    finish_reason: str | None = None
    usage: TokenUsage | None = None


class LLMProviderError(RuntimeError):
    """LLM Provider 边界的基础异常。"""


class ProviderConfigurationError(LLMProviderError):
    """Provider 配置缺失或无效。"""


class ProviderRequestError(LLMProviderError):
    """Provider HTTP 请求失败。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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
