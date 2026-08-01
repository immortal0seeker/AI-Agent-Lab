from app.providers.embedding.base import (
    EmbeddingProvider,
    EmbeddingProviderError,
)


class EmbeddingProviderRegistryError(EmbeddingProviderError):
    """Embedding Provider 注册与选择边界的基础异常。"""


class DuplicateEmbeddingProviderError(EmbeddingProviderRegistryError):
    pass


class EmbeddingProviderNotFoundError(EmbeddingProviderRegistryError):
    pass


class EmbeddingProviderRegistry:
    def __init__(self) -> None:
        self._providers_by_name: dict[str, EmbeddingProvider] = {}

    def register_provider(self, provider: EmbeddingProvider) -> None:
        if not isinstance(provider, EmbeddingProvider):
            raise TypeError("provider must be an EmbeddingProvider instance")
        if provider.name in self._providers_by_name:
            raise DuplicateEmbeddingProviderError(
                f"Duplicate Embedding Provider registration: {provider.name}"
            )
        self._providers_by_name[provider.name] = provider

    def get_provider(self, name: str) -> EmbeddingProvider:
        if not isinstance(name, str):
            raise TypeError("provider name must be a string")
        try:
            return self._providers_by_name[name]
        except KeyError as exc:
            raise EmbeddingProviderNotFoundError(
                f"Embedding Provider not found: {name}"
            ) from exc

    def list_providers(self) -> list[EmbeddingProvider]:
        return list(self._providers_by_name.values())
