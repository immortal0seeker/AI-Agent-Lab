import httpx

from app.core.config import Settings
from app.providers.llm.base import ProviderConfigurationError
from app.providers.llm.openai_compatible import OpenAICompatibleProvider


def create_openai_compatible_provider(
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> OpenAICompatibleProvider:
    secret = settings.openai_compatible_api_key
    api_key = secret.get_secret_value().strip() if secret is not None else ""
    if not api_key:
        raise ProviderConfigurationError(
            "OPENAI_COMPATIBLE_API_KEY is required to initialize the provider"
        )

    return OpenAICompatibleProvider(
        base_url=settings.openai_compatible_base_url,
        api_key=api_key,
        default_model=settings.openai_compatible_model,
        timeout_seconds=settings.openai_compatible_timeout_seconds,
        client=client,
    )
