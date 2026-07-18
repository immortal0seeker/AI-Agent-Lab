import asyncio
from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError

from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatMessage,
    ChatRequest,
    LLMFunctionDefinition,
    LLMProviderError,
    LLMResponse,
    LLMToolCall,
    LLMToolDefinition,
    ProviderUnsupportedFeatureError,
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


def build_tool_definition() -> LLMToolDefinition:
    return LLMToolDefinition(
        function=LLMFunctionDefinition(
            name="read_file",
            description="Read a workspace text file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        )
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


def test_provider_contract_accepts_tools_and_returns_tool_calls() -> None:
    async def exercise_provider() -> tuple[ChatRequest, LLMResponse]:
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="read README")],
            tools=(build_tool_definition(),),
        )
        response = LLMResponse(
            model="mock-model",
            content=None,
            finish_reason="tool_calls",
            tool_calls=(
                LLMToolCall(
                    tool_call_id="call_1",
                    tool_name="read_file",
                    arguments={"path": "README.md"},
                ),
            ),
        )
        return request, response

    request, response = asyncio.run(exercise_provider())

    assert request.tools[0].function.name == "read_file"
    assert response.content is None
    assert response.tool_calls[0].arguments == {"path": "README.md"}


def test_provider_contract_defaults_to_text_only() -> None:
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="hello")]
    )
    response = LLMResponse(model="mock-model", content="answer")

    assert request.tools == ()
    assert response.tool_calls == ()


def test_llm_response_requires_content_or_tool_calls() -> None:
    with pytest.raises(ValidationError, match="content or tool calls"):
        LLMResponse(model="mock-model", content=None)


def test_llm_response_rejects_duplicate_tool_call_ids() -> None:
    with pytest.raises(ValidationError, match="tool call ids must be unique"):
        LLMResponse(
            model="mock-model",
            content=None,
            tool_calls=(
                LLMToolCall(
                    tool_call_id="call_1",
                    tool_name="read_file",
                    arguments={"path": "README.md"},
                ),
                LLMToolCall(
                    tool_call_id="call_1",
                    tool_name="list_dir",
                    arguments={"path": "."},
                ),
            ),
        )


@pytest.mark.parametrize("name", ["read file", "读取文件", "x" * 65])
def test_llm_tool_definition_rejects_invalid_function_names(name: str) -> None:
    with pytest.raises(ValidationError):
        LLMFunctionDefinition(
            name=name,
            description="Invalid function name",
            parameters={"type": "object"},
        )


@pytest.mark.parametrize(
    "parameters",
    [
        {"type": "string"},
        {"type": "object", "default": object()},
        {"type": "object", "default": float("nan")},
    ],
)
def test_llm_tool_definition_rejects_invalid_parameters(
    parameters: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        LLMFunctionDefinition(
            name="read_file",
            description="Read a workspace text file",
            parameters=parameters,
        )


def test_llm_tool_values_copy_mutable_inputs() -> None:
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
    }
    arguments = {"path": "README.md", "options": {"encoding": "utf-8"}}

    definition = LLMFunctionDefinition(
        name="read_file",
        description="Read a workspace text file",
        parameters=parameters,
    )
    tool_call = LLMToolCall(
        tool_call_id="call_1",
        tool_name="read_file",
        arguments=arguments,
    )
    parameters["properties"]["path"]["type"] = "integer"  # type: ignore[index]
    arguments["options"]["encoding"] = "utf-16"  # type: ignore[index]

    assert definition.parameters["properties"]["path"]["type"] == "string"
    assert tool_call.arguments["options"]["encoding"] == "utf-8"


def test_unsupported_feature_error_stays_in_provider_boundary() -> None:
    assert issubclass(ProviderUnsupportedFeatureError, LLMProviderError)


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
