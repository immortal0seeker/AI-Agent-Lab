import asyncio
import json

import httpx
import pytest

from app.core.config import Settings
from app.providers.embedding import EmbeddingProviderConfigurationError
from app.providers.embedding.factory import (
    create_openai_compatible_embedding_provider,
)


def configured_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "OPENAI_COMPATIBLE_EMBEDDING_BASE_URL": "https://provider.example/v1",
        "OPENAI_COMPATIBLE_EMBEDDING_API_KEY": "synthetic-secret",
        "OPENAI_COMPATIBLE_EMBEDDING_MODEL": "configured-model",
        "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION": 3,
        "OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS": 12.5,
    }
    values.update(overrides)
    return Settings(**values)


def test_settings_mask_openai_compatible_embedding_api_key() -> None:
    settings = configured_settings()

    assert settings.openai_compatible_embedding_api_key is not None
    assert (
        settings.openai_compatible_embedding_api_key.get_secret_value()
        == "synthetic-secret"
    )
    assert "synthetic-secret" not in repr(settings)
    assert "synthetic-secret" not in str(settings)


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_factory_rejects_missing_api_key_with_readable_error(
    api_key: str | None,
) -> None:
    settings = configured_settings(
        OPENAI_COMPATIBLE_EMBEDDING_API_KEY=api_key
    )

    with pytest.raises(
        EmbeddingProviderConfigurationError,
        match="OPENAI_COMPATIBLE_EMBEDDING_API_KEY is required",
    ):
        create_openai_compatible_embedding_provider(settings)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        (
            "OPENAI_COMPATIBLE_EMBEDDING_BASE_URL",
            " ",
            "OPENAI_COMPATIBLE_EMBEDDING_BASE_URL is required",
        ),
        (
            "OPENAI_COMPATIBLE_EMBEDDING_MODEL",
            " ",
            "OPENAI_COMPATIBLE_EMBEDDING_MODEL is required",
        ),
        (
            "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION",
            None,
            "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION is required",
        ),
    ],
)
def test_factory_rejects_missing_required_configuration(
    field_name: str,
    value: object,
    message: str,
) -> None:
    settings = configured_settings(**{field_name: value})

    with pytest.raises(EmbeddingProviderConfigurationError, match=message):
        create_openai_compatible_embedding_provider(settings)


def test_factory_creates_provider_from_embedding_settings() -> None:
    async def exercise() -> tuple[str, object]:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://provider.example/v1/embeddings"
            assert request.headers["Authorization"] == "Bearer synthetic-secret"
            assert request.extensions["timeout"]["read"] == 12.5
            assert json.loads(request.content) == {
                "model": "configured-model",
                "input": ["question"],
                "dimensions": 3,
                "encoding_format": "float",
            }
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [
                        {
                            "object": "embedding",
                            "embedding": [0.1, 0.2, 0.3],
                            "index": 0,
                        }
                    ],
                    "model": "resolved-model",
                    "usage": {"prompt_tokens": 2, "total_tokens": 2},
                },
            )

        settings = configured_settings()
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = create_openai_compatible_embedding_provider(
                settings,
                client=client,
            )
            result = await provider.embed_query("question")
            return provider.name, result

    provider_name, result = asyncio.run(exercise())

    assert provider_name == "openai_compatible"
    assert result.model == "resolved-model"
    assert result.dimension == 3
