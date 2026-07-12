import asyncio
from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError

from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatMessage,
    ChatRequest,
    LLMResponse,
    TokenUsage,
)


class MockLLMProvider(BaseLLMProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        return LLMResponse(
            id="mock-response",
            model=request.model or "mock-model",
            content="mock answer",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=3, output_tokens=2, total_tokens=5),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        yield ChatChunk(
            id="mock-response",
            model=request.model or "mock-model",
            content="mock",
        )


def test_provider_contract_supports_chat_and_stream() -> None:
    async def exercise_provider() -> tuple[LLMResponse, list[ChatChunk]]:
        provider = MockLLMProvider()
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="hello")],
            model="test-model",
        )

        response = await provider.chat(request)
        chunks = [chunk async for chunk in provider.stream_chat(request)]
        return response, chunks

    response, chunks = asyncio.run(exercise_provider())

    assert response.model == "test-model"
    assert response.content == "mock answer"
    assert response.usage == TokenUsage(
        input_tokens=3,
        output_tokens=2,
        total_tokens=5,
    )
    assert [chunk.content for chunk in chunks] == ["mock"]


@pytest.mark.parametrize("temperature", [-0.1, 2.1])
def test_chat_request_rejects_temperature_outside_supported_range(
    temperature: float,
) -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hello")],
            temperature=temperature,
        )


def test_chat_request_rejects_non_positive_max_tokens() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hello")],
            max_tokens=0,
        )


def test_chat_request_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])
