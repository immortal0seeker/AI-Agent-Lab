import httpx

from app.core.config import Settings
from app.providers.embedding.base import (
    EmbeddingProvider,
    EmbeddingProviderConfigurationError,
)
from app.providers.embedding.openai_compatible_embedding import (
    OpenAICompatibleEmbeddingProvider,
)
from app.providers.embedding.registry import EmbeddingProviderNotFoundError


def create_embedding_provider(
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> EmbeddingProvider:
    if settings.embedding_provider != "openai_compatible":
        raise EmbeddingProviderNotFoundError(
            f"Embedding Provider not found: {settings.embedding_provider}"
        )
    return create_openai_compatible_embedding_provider(
        settings,
        client=client,
    )


def create_openai_compatible_embedding_provider(
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
) -> OpenAICompatibleEmbeddingProvider:
    secret = settings.openai_compatible_embedding_api_key
    api_key = secret.get_secret_value().strip() if secret is not None else ""
    if not api_key:
        raise EmbeddingProviderConfigurationError(
            "OPENAI_COMPATIBLE_EMBEDDING_API_KEY is required "
            "to initialize the provider"
        )

    dimension = settings.openai_compatible_embedding_dimension
    if dimension is None:
        raise EmbeddingProviderConfigurationError(
            "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION is required "
            "to initialize the provider"
        )

    return OpenAICompatibleEmbeddingProvider(
        base_url=settings.openai_compatible_embedding_base_url,
        api_key=api_key,
        default_model=settings.openai_compatible_embedding_model,
        expected_dimension=dimension,
        timeout_seconds=(
            settings.openai_compatible_embedding_timeout_seconds
        ),
        client=client,
    )
