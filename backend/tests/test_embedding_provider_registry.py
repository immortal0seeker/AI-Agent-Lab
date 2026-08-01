import pytest

from app.providers.embedding import (
    DuplicateEmbeddingProviderError,
    EmbeddingProvider,
    EmbeddingProviderNotFoundError,
    EmbeddingProviderRegistry,
    EmbeddingProviderRegistryError,
    EmbeddingResult,
    EmbeddingUsage,
)


class MockEmbeddingProvider(EmbeddingProvider):
    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            model="mock-model",
            vectors=tuple((float(index),) for index, _ in enumerate(texts)),
            usage=EmbeddingUsage(
                input_tokens=len(texts),
                total_tokens=len(texts),
            ),
        )

    async def embed_query(self, query: str) -> EmbeddingResult:
        return EmbeddingResult(
            model="mock-model",
            vectors=((1.0,),),
            usage=EmbeddingUsage(input_tokens=1, total_tokens=1),
        )


def build_provider(name: str) -> MockEmbeddingProvider:
    return MockEmbeddingProvider(name=name)


def test_registry_selects_configured_provider_and_preserves_order() -> None:
    first = build_provider("first")
    second = build_provider("second")
    registry = EmbeddingProviderRegistry()

    registry.register_provider(first)
    registry.register_provider(second)

    configured_name = "first"
    assert registry.get_provider(configured_name) is first
    assert registry.list_providers() == [first, second]


def test_registry_list_is_a_defensive_copy() -> None:
    provider = build_provider("mock")
    registry = EmbeddingProviderRegistry()
    registry.register_provider(provider)

    listed = registry.list_providers()
    listed.clear()

    assert registry.list_providers() == [provider]


def test_registry_rejects_duplicate_without_changing_state() -> None:
    original = build_provider("mock")
    registry = EmbeddingProviderRegistry()
    registry.register_provider(original)

    with pytest.raises(DuplicateEmbeddingProviderError, match="mock"):
        registry.register_provider(build_provider("mock"))

    assert registry.list_providers() == [original]
    assert registry.get_provider("mock") is original


def test_registry_rejects_non_provider_instance() -> None:
    with pytest.raises(TypeError, match="EmbeddingProvider instance"):
        EmbeddingProviderRegistry().register_provider(
            object()  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("configured_name", ["missing", "first ", "FIRST"])
def test_registry_lookup_is_exact_and_missing_name_raises(
    configured_name: str,
) -> None:
    registry = EmbeddingProviderRegistry()
    registry.register_provider(build_provider("first"))

    with pytest.raises(
        EmbeddingProviderNotFoundError,
        match=configured_name,
    ):
        registry.get_provider(configured_name)


def test_registry_lookup_rejects_non_string_name() -> None:
    with pytest.raises(TypeError, match="provider name must be a string"):
        EmbeddingProviderRegistry().get_provider(1)  # type: ignore[arg-type]


def test_registry_errors_stay_in_provider_boundary() -> None:
    assert issubclass(
        DuplicateEmbeddingProviderError,
        EmbeddingProviderRegistryError,
    )
    assert issubclass(
        EmbeddingProviderNotFoundError,
        EmbeddingProviderRegistryError,
    )
