import asyncio
from math import inf, nan

import pytest
from pydantic import ValidationError

from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingResult,
    EmbeddingUsage,
)


class MockEmbeddingProvider(EmbeddingProvider):
    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            model="mock-embedding",
            vectors=tuple(
                (float(index), float(len(text)))
                for index, text in enumerate(texts)
            ),
            usage=EmbeddingUsage(
                input_tokens=len(texts),
                total_tokens=len(texts),
            ),
        )

    async def embed_query(self, query: str) -> EmbeddingResult:
        return EmbeddingResult(
            model="mock-embedding",
            vectors=((0.5, float(len(query))),),
            usage=EmbeddingUsage(input_tokens=1, total_tokens=1),
        )


def test_provider_contract_supports_batch_and_query_embedding() -> None:
    async def exercise_provider() -> tuple[EmbeddingResult, EmbeddingResult]:
        provider = MockEmbeddingProvider(name=" mock ")
        batch = await provider.embed_texts(["a", "three"])
        query = await provider.embed_query("question")
        assert provider.name == "mock"
        return batch, query

    batch, query = asyncio.run(exercise_provider())

    assert batch.vectors == ((0.0, 1.0), (1.0, 5.0))
    assert batch.usage == EmbeddingUsage(input_tokens=2, total_tokens=2)
    assert batch.dimension == 2
    assert query.vectors == ((0.5, 8.0),)
    assert query.usage == EmbeddingUsage(input_tokens=1, total_tokens=1)


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_provider_rejects_invalid_name(name: str) -> None:
    with pytest.raises(ValueError):
        MockEmbeddingProvider(name=name)


def test_provider_rejects_non_string_name() -> None:
    with pytest.raises(TypeError, match="name must be a string"):
        MockEmbeddingProvider(name=1)  # type: ignore[arg-type]


def test_provider_name_is_read_only() -> None:
    provider = MockEmbeddingProvider(name="mock")

    with pytest.raises(AttributeError):
        provider.name = "changed"  # type: ignore[misc]

    assert provider.name == "mock"


def test_embedding_result_normalizes_and_freezes_values() -> None:
    vectors = [[0, 1.5], [2.0, 3]]
    result = EmbeddingResult(
        model=" model ",
        vectors=vectors,
        usage={"input_tokens": 3, "total_tokens": 3},
    )
    vectors[0][0] = 99

    assert result.model == "model"
    assert result.vectors == ((0.0, 1.5), (2.0, 3.0))
    assert result.dimension == 2
    with pytest.raises(ValidationError):
        result.model = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "vectors",
    [
        (),
        ((),),
        ((1.0, 2.0), (3.0,)),
        ((nan, 1.0),),
        ((inf, 1.0),),
        ((-inf, 1.0),),
        ((True, 1.0),),
        (("1.0", 2.0),),
    ],
)
def test_embedding_result_rejects_invalid_vector_shape_and_values(
    vectors: object,
) -> None:
    with pytest.raises(ValidationError):
        EmbeddingResult(
            model="mock-model",
            vectors=vectors,
            usage=EmbeddingUsage(input_tokens=1, total_tokens=1),
        )


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": -1, "total_tokens": 0},
        {"input_tokens": 2, "total_tokens": 1},
        {"input_tokens": True, "total_tokens": True},
        {"input_tokens": 1.0, "total_tokens": 1.0},
    ],
)
def test_embedding_usage_rejects_invalid_counts(
    usage: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        EmbeddingUsage.model_validate(usage)


def test_embedding_result_rejects_blank_model() -> None:
    with pytest.raises(ValidationError):
        EmbeddingResult(
            model="   ",
            vectors=((1.0,),),
            usage=EmbeddingUsage(input_tokens=1, total_tokens=1),
        )


def test_embedding_provider_error_stays_in_provider_boundary() -> None:
    assert issubclass(EmbeddingProviderError, RuntimeError)
