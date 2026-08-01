import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from app.providers.embedding import (
    EmbeddingDimensionMismatchError,
    EmbeddingProviderAuthError,
    EmbeddingProviderBadRequestError,
    EmbeddingProviderConfigurationError,
    EmbeddingProviderInputError,
    EmbeddingProviderRateLimitError,
    EmbeddingProviderResponseError,
    EmbeddingProviderServerError,
    EmbeddingProviderTimeoutError,
    EmbeddingProviderUnknownError,
    EmbeddingUsage,
    OpenAICompatibleEmbeddingProvider,
)


def embedding_response(
    *,
    data: list[dict[str, object]] | None = None,
    model: object = "response-model",
    usage: object = None,
) -> dict[str, object]:
    return {
        "object": "list",
        "data": data
        if data is not None
        else [
            {
                "object": "embedding",
                "embedding": [0.1, 0.2, 0.3],
                "index": 0,
            }
        ],
        "model": model,
        "usage": usage
        if usage is not None
        else {
            "prompt_tokens": 3,
            "total_tokens": 3,
        },
    }


def build_provider(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    dimension: int = 3,
) -> tuple[OpenAICompatibleEmbeddingProvider, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://provider.example/v1/",
        api_key="synthetic-secret",
        default_model="configured-model",
        expected_dimension=dimension,
        timeout_seconds=12.5,
        client=client,
    )
    return provider, client


def test_embed_texts_maps_batch_request_and_orders_response_by_index() -> None:
    async def exercise() -> tuple[object, bool]:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert request.url == "https://provider.example/v1/embeddings"
            assert request.headers["Authorization"] == "Bearer synthetic-secret"
            assert request.headers["Content-Type"] == "application/json"
            assert request.extensions["timeout"]["read"] == 12.5
            assert request.read()
            assert request.content
            assert request.headers["Content-Length"]
            assert len(request.url.params) == 0
            assert json.loads(request.content) == {
                "model": "configured-model",
                "input": ["first", "second"],
                "dimensions": 3,
                "encoding_format": "float",
            }
            return httpx.Response(
                200,
                json=embedding_response(
                    data=[
                        {
                            "object": "embedding",
                            "embedding": [1.1, 1.2, 1.3],
                            "index": 1,
                        },
                        {
                            "object": "embedding",
                            "embedding": [0.1, 0.2, 0.3],
                            "index": 0,
                        },
                    ],
                    model="resolved-model",
                    usage={"prompt_tokens": 7, "total_tokens": 7},
                ),
            )

        provider, client = build_provider(handler)
        try:
            result = await provider.embed_texts(["first", "second"])
            return result, client.is_closed
        finally:
            await client.aclose()

    result, client_was_closed = asyncio.run(exercise())

    assert result.model == "resolved-model"
    assert result.vectors == ((0.1, 0.2, 0.3), (1.1, 1.2, 1.3))
    assert result.dimension == 3
    assert result.usage == EmbeddingUsage(input_tokens=7, total_tokens=7)
    assert client_was_closed is False


def test_embed_query_uses_single_item_batch() -> None:
    async def exercise() -> object:
        def handler(request: httpx.Request) -> httpx.Response:
            assert json.loads(request.content)["input"] == ["question"]
            return httpx.Response(200, json=embedding_response())

        provider, client = build_provider(handler)
        try:
            return await provider.embed_query("question")
        finally:
            await client.aclose()

    result = asyncio.run(exercise())

    assert result.vectors == ((0.1, 0.2, 0.3),)


@pytest.mark.parametrize(
    ("method_name", "value"),
    [
        ("embed_texts", []),
        ("embed_texts", ["valid", "   "]),
        ("embed_query", ""),
        ("embed_query", "   "),
    ],
)
def test_provider_rejects_empty_embedding_inputs(
    method_name: str,
    value: object,
) -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("invalid input must fail before HTTP")

        provider, client = build_provider(handler)
        try:
            method = getattr(provider, method_name)
            with pytest.raises(EmbeddingProviderInputError, match="must not"):
                await method(value)
        finally:
            await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, EmbeddingProviderAuthError),
        (429, EmbeddingProviderRateLimitError),
        (408, EmbeddingProviderTimeoutError),
        (422, EmbeddingProviderBadRequestError),
        (503, EmbeddingProviderServerError),
        (302, EmbeddingProviderUnknownError),
    ],
)
def test_provider_classifies_http_errors_without_leaking_response(
    status_code: int,
    error_type: type[Exception],
) -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code,
                json={"error": {"message": "remote-secret-body"}},
            )

        provider, client = build_provider(handler)
        try:
            with pytest.raises(error_type) as exc_info:
                await provider.embed_query("private-input")
            assert getattr(exc_info.value, "status_code") == status_code
            message = str(exc_info.value)
            assert "remote-secret-body" not in message
            assert "synthetic-secret" not in message
            assert "private-input" not in message
        finally:
            await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("error_kind", "expected_type"),
    [
        ("timeout", EmbeddingProviderTimeoutError),
        ("connection", EmbeddingProviderUnknownError),
    ],
)
def test_provider_normalizes_network_errors(
    error_kind: str,
    expected_type: type[Exception],
) -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if error_kind == "timeout":
                raise httpx.ReadTimeout("slow provider", request=request)
            raise httpx.ConnectError(
                "private hostname failed",
                request=request,
            )

        provider, client = build_provider(handler)
        try:
            with pytest.raises(expected_type) as exc_info:
                await provider.embed_query("private-input")
            assert "private hostname" not in str(exc_info.value)
            assert "private-input" not in str(exc_info.value)
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_provider_rejects_non_json_success_response() -> None:
    async def exercise() -> None:
        provider, client = build_provider(
            lambda request: httpx.Response(200, content=b"not-json")
        )
        try:
            with pytest.raises(
                EmbeddingProviderResponseError,
                match="expected JSON",
            ) as exc_info:
                await provider.embed_query("question")
            assert exc_info.value.__cause__ is None
            assert exc_info.value.__suppress_context__ is True
        finally:
            await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "payload",
    [
        embedding_response(data=[]),
        embedding_response(
            data=[
                {"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0},
                {"object": "embedding", "embedding": [1.1, 1.2, 1.3], "index": 0},
            ]
        ),
        embedding_response(
            data=[
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, "not-a-number"],
                    "index": 0,
                }
            ]
        ),
        embedding_response(usage={"prompt_tokens": True, "total_tokens": True}),
        embedding_response(model="   "),
    ],
)
def test_provider_rejects_malformed_success_response(
    payload: dict[str, object],
) -> None:
    async def exercise() -> None:
        provider, client = build_provider(
            lambda request: httpx.Response(200, json=payload)
        )
        try:
            with pytest.raises(
                EmbeddingProviderResponseError,
                match="response format is invalid",
            ) as exc_info:
                await provider.embed_query("question")
            assert exc_info.value.__cause__ is None
            assert exc_info.value.__suppress_context__ is True
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_provider_rejects_response_count_mismatch() -> None:
    async def exercise() -> None:
        provider, client = build_provider(
            lambda request: httpx.Response(200, json=embedding_response())
        )
        try:
            with pytest.raises(
                EmbeddingProviderResponseError,
                match="response format is invalid",
            ):
                await provider.embed_texts(["first", "second"])
        finally:
            await client.aclose()

    asyncio.run(exercise())


def test_provider_rejects_configured_dimension_mismatch_readably() -> None:
    async def exercise() -> None:
        provider, client = build_provider(
            lambda request: httpx.Response(200, json=embedding_response()),
            dimension=2,
        )
        try:
            with pytest.raises(
                EmbeddingDimensionMismatchError,
                match="expected 2, received 3",
            ) as exc_info:
                await provider.embed_query("private-input")
            message = str(exc_info.value)
            assert "synthetic-secret" not in message
            assert "private-input" not in message
            assert "0.1" not in message
        finally:
            await client.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("base_url", " ", "BASE_URL"),
        ("api_key", " ", "API_KEY"),
        ("default_model", " ", "MODEL"),
        ("expected_dimension", 0, "DIMENSION"),
        ("timeout_seconds", 0, "TIMEOUT_SECONDS"),
    ],
)
def test_provider_rejects_invalid_direct_configuration(
    field_name: str,
    value: object,
    message: str,
) -> None:
    kwargs: dict[str, object] = {
        "base_url": "https://provider.example/v1",
        "api_key": "synthetic-secret",
        "default_model": "configured-model",
        "expected_dimension": 3,
        "timeout_seconds": 30.0,
    }
    kwargs[field_name] = value

    with pytest.raises(EmbeddingProviderConfigurationError, match=message):
        OpenAICompatibleEmbeddingProvider(**kwargs)  # type: ignore[arg-type]
