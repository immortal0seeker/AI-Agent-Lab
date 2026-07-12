import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.providers.llm.base import (
    ChatMessage,
    ChatRequest,
    ProviderConfigurationError,
)
from app.providers.llm.factory import create_openai_compatible_provider


def test_settings_mask_openai_compatible_api_key() -> None:
    settings = Settings(
        OPENAI_COMPATIBLE_API_KEY="test-secret-key",
    )

    assert settings.openai_compatible_api_key is not None
    assert settings.openai_compatible_api_key.get_secret_value() == "test-secret-key"
    assert "test-secret-key" not in repr(settings)


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_factory_rejects_missing_api_key_with_readable_error(
    api_key: str | None,
) -> None:
    settings = Settings(
        OPENAI_COMPATIBLE_BASE_URL="https://provider.example/v1",
        OPENAI_COMPATIBLE_API_KEY=api_key,
        OPENAI_COMPATIBLE_MODEL="default-model",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="OPENAI_COMPATIBLE_API_KEY is required",
    ):
        create_openai_compatible_provider(settings)


def test_factory_creates_provider_from_settings() -> None:
    async def exercise() -> str:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://provider.example/v1/chat/completions"
            assert request.headers["Authorization"] == "Bearer test-secret-key"
            return httpx.Response(
                200,
                json={
                    "model": "configured-model",
                    "choices": [{"message": {"content": "configured answer"}}],
                },
            )

        settings = Settings(
            OPENAI_COMPATIBLE_BASE_URL="https://provider.example/v1",
            OPENAI_COMPATIBLE_API_KEY="test-secret-key",
            OPENAI_COMPATIBLE_MODEL="configured-model",
            OPENAI_COMPATIBLE_TIMEOUT_SECONDS=12.5,
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            provider = create_openai_compatible_provider(settings, client=client)
            response = await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )
        return response.content

    assert asyncio.run(exercise()) == "configured answer"
