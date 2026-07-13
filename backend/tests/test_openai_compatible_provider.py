import asyncio
import json

import httpx
import pytest

from app.providers.llm.base import (
    ChatMessage,
    ChatRequest,
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderServerError,
    ProviderTimeoutError,
    ProviderUnknownError,
    TokenUsage,
)
from app.providers.llm.openai_compatible import OpenAICompatibleProvider


def test_chat_maps_request_response_and_usage() -> None:
    async def exercise() -> tuple[dict[str, object], object]:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            captured["payload"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-123",
                    "model": "resolved-model",
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": "hello"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 4,
                        "completion_tokens": 2,
                        "total_tokens": 6,
                    },
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1/",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            response = await provider.chat(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="hi")],
                    model="request-model",
                    temperature=0.2,
                    max_tokens=50,
                )
            )
        return captured, response

    captured, response = asyncio.run(exercise())

    assert captured == {
        "url": "https://provider.example/v1/chat/completions",
        "authorization": "Bearer test-secret-key",
        "payload": {
            "model": "request-model",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.2,
            "max_tokens": 50,
            "stream": False,
        },
    }
    assert response.id == "chatcmpl-123"
    assert response.model == "resolved-model"
    assert response.content == "hello"
    assert response.finish_reason == "stop"
    assert response.usage == TokenUsage(
        input_tokens=4,
        output_tokens=2,
        total_tokens=6,
    )


def test_chat_uses_default_model_and_omits_unset_max_tokens() -> None:
    async def exercise() -> dict[str, object]:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "model": "default-model",
                    "choices": [{"message": {"content": "answer"}}],
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )
        return captured

    payload = asyncio.run(exercise())

    assert payload["model"] == "default-model"
    assert "max_tokens" not in payload


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (400, ProviderBadRequestError),
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (408, ProviderTimeoutError),
        (429, ProviderRateLimitError),
        (500, ProviderServerError),
        (504, ProviderTimeoutError),
    ],
)
def test_chat_classifies_http_errors_without_upstream_text(
    status_code: int,
    expected_error: type[ProviderRequestError],
) -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code,
                json={"error": {"message": "secret upstream diagnostic"}},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )

    with pytest.raises(expected_error) as exc_info:
        asyncio.run(exercise())

    assert exc_info.value.status_code == status_code
    assert "secret upstream diagnostic" not in str(exc_info.value)
    assert "test-secret-key" not in str(exc_info.value)


def test_chat_does_not_propagate_api_key_echoed_by_provider_error() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "credential test-secret-key is not accepted"
                    }
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )

    with pytest.raises(ProviderBadRequestError) as exc_info:
        asyncio.run(exercise())

    assert "credential" not in str(exc_info.value)
    assert "test-secret-key" not in str(exc_info.value)


def test_chat_rejects_malformed_success_response() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": []})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )

    with pytest.raises(ProviderResponseError, match="response format"):
        asyncio.run(exercise())


def test_chat_translates_transport_error() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection failed", request=request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )

    with pytest.raises(ProviderUnknownError, match="Provider request failed"):
        asyncio.run(exercise())


def test_chat_translates_timeout_error() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("private timeout detail", request=request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )

    with pytest.raises(ProviderTimeoutError) as exc_info:
        asyncio.run(exercise())

    assert "private timeout detail" not in str(exc_info.value)
    assert "test-secret-key" not in str(exc_info.value)


def test_stream_chat_classifies_http_error_without_upstream_text() -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={"error": {"message": "private rate limit detail"}},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            async for _ in provider.stream_chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            ):
                pass

    with pytest.raises(ProviderRateLimitError) as exc_info:
        asyncio.run(exercise())

    assert "private rate limit detail" not in str(exc_info.value)
    assert "test-secret-key" not in str(exc_info.value)


def test_stream_chat_parses_sse_chunks_and_done_marker() -> None:
    async def exercise() -> tuple[dict[str, object], list[object]]:
        captured: dict[str, object] = {}
        events = [
            {
                "id": "chatcmpl-stream",
                "model": "stream-model",
                "choices": [
                    {"delta": {"content": "Hel"}, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-stream",
                "model": "stream-model",
                "choices": [
                    {"delta": {"content": "lo"}, "finish_reason": None}
                ],
            },
            {
                "id": "chatcmpl-stream",
                "model": "stream-model",
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                },
            },
        ]
        body = "\n\n".join(
            [*(f"data: {json.dumps(event)}" for event in events), "data: [DONE]"]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(
                200,
                text=body,
                headers={"Content-Type": "text/event-stream"},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="stream-model",
                client=client,
            )
            chunks = [
                chunk
                async for chunk in provider.stream_chat(
                    ChatRequest(
                        messages=[ChatMessage(role="user", content="hi")]
                    )
                )
            ]
        return captured, chunks

    payload, chunks = asyncio.run(exercise())

    assert payload["stream"] is True
    assert [chunk.content for chunk in chunks] == ["Hel", "lo", ""]
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage == TokenUsage(
        input_tokens=3,
        output_tokens=2,
        total_tokens=5,
    )
