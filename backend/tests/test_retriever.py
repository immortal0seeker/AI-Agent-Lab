import asyncio
from math import inf, nan
from uuid import UUID

import pytest

from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingProviderResponseError,
    EmbeddingResult,
    EmbeddingUsage,
)
from app.rag.retriever import (
    Retriever,
    RetrieverInputError,
    RetrieverResponseError,
)
from app.rag.vectorstores import (
    ChunkVectorPayload,
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
    VectorStoreError,
    VectorStoreOperationError,
)
from app.schemas import RetrievalResult


KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_KNOWLEDGE_BASE_ID = UUID(
    "00000000-0000-0000-0000-000000000099"
)
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000003")
SECOND_CHUNK_ID = UUID("00000000-0000-0000-0000-000000000004")


class RecordingEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        result: EmbeddingResult | None = None,
        fail_with: EmbeddingProviderError | None = None,
    ) -> None:
        super().__init__(name="recording")
        self.result = result or make_embedding_result()
        self.fail_with = fail_with
        self.queries: list[str] = []

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        raise AssertionError("Retriever must use embed_query")

    async def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
        if self.fail_with is not None:
            raise self.fail_with
        return self.result


class RecordingVectorStore(VectorStore):
    def __init__(
        self,
        *,
        results: tuple[VectorSearchResult, ...] = (),
        dimension: int = 3,
        fail_with: VectorStoreError | None = None,
    ) -> None:
        self.results = results
        self._dimension = dimension
        self.fail_with = fail_with
        self.search_queries: list[VectorSearchQuery] = []

    @property
    def collection_name(self) -> str:
        return "recording_chunks"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def ensure_collection(self) -> VectorCollectionStatus:
        raise AssertionError("Retriever must not ensure the collection")

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        raise AssertionError("Retriever must not upsert points")

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        self.search_queries.append(query)
        if self.fail_with is not None:
            raise self.fail_with
        return self.results

    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        raise AssertionError("Retriever must not delete points")

    async def close(self) -> None:
        raise AssertionError("Retriever does not own the VectorStore lifecycle")


def make_embedding_result(
    *,
    vectors: tuple[tuple[float, ...], ...] = ((0.1, 0.2, 0.3),),
) -> EmbeddingResult:
    return EmbeddingResult(
        model="synthetic-query-embedding",
        vectors=vectors,
        usage=EmbeddingUsage(input_tokens=2, total_tokens=2),
    )


def make_search_result(
    *,
    chunk_id: UUID = CHUNK_ID,
    knowledge_base_id: UUID = KNOWLEDGE_BASE_ID,
    chunk_index: int = 0,
    content: str = "Retriever overview",
    score: float = 0.91,
    embedding_provider: str = "recording",
    embedding_model: str = "synthetic-query-embedding",
) -> VectorSearchResult:
    return VectorSearchResult(
        point_id=chunk_id,
        score=score,
        payload=ChunkVectorPayload(
            knowledge_base_id=knowledge_base_id,
            document_id=DOCUMENT_ID,
            chunk_id=chunk_id,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            filename="guide.md",
            chunk_index=chunk_index,
            content=content,
            heading="Overview" if chunk_index == 0 else None,
            page_number=None,
            metadata={
                "source_format": "md",
                "line_range": [chunk_index + 1, chunk_index + 2],
            },
        ),
    )


def make_retriever(
    provider: RecordingEmbeddingProvider,
    store: RecordingVectorStore,
) -> Retriever:
    return Retriever(embedding_provider=provider, vector_store=store)


def test_retrieve_embeds_query_and_maps_ordered_sources() -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore(
        results=(
            make_search_result(),
            make_search_result(
                chunk_id=SECOND_CHUNK_ID,
                chunk_index=1,
                content="Second source",
                score=0.82,
            ),
        )
    )

    results = asyncio.run(
        make_retriever(provider, store).retrieve(
            query="How does retrieval work?",
            knowledge_base_id=KNOWLEDGE_BASE_ID,
        )
    )

    assert provider.queries == ["How does retrieval work?"]
    assert store.search_queries == [
        VectorSearchQuery(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            embedding_provider="recording",
            embedding_model="synthetic-query-embedding",
            vector=(0.1, 0.2, 0.3),
            limit=5,
            score_threshold=None,
        )
    ]
    assert results == (
        RetrievalResult(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            chunk_id=CHUNK_ID,
            embedding_provider="recording",
            embedding_model="synthetic-query-embedding",
            filename="guide.md",
            chunk_index=0,
            content="Retriever overview",
            score=0.91,
            heading="Overview",
            page_number=None,
            metadata={"source_format": "md", "line_range": [1, 2]},
        ),
        RetrievalResult(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            chunk_id=SECOND_CHUNK_ID,
            embedding_provider="recording",
            embedding_model="synthetic-query-embedding",
            filename="guide.md",
            chunk_index=1,
            content="Second source",
            score=0.82,
            heading=None,
            page_number=None,
            metadata={"source_format": "md", "line_range": [2, 3]},
        ),
    )


def test_retrieve_forwards_custom_limit_and_threshold_for_zero_hits() -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    results = asyncio.run(
        make_retriever(provider, store).retrieve(
            query="No matching source",
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            top_k=2,
            score_threshold=0.75,
        )
    )

    assert results == ()
    assert store.search_queries == [
        VectorSearchQuery(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            embedding_provider="recording",
            embedding_model="synthetic-query-embedding",
            vector=(0.1, 0.2, 0.3),
            limit=2,
            score_threshold=0.75,
        )
    ]


@pytest.mark.parametrize("query", [None, 7, "", " \n\t "])
def test_retrieve_rejects_invalid_query_before_external_calls(
    query: object,
) -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    with pytest.raises(RetrieverInputError, match="query"):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query=query,  # type: ignore[arg-type]
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )

    assert provider.queries == []
    assert store.search_queries == []


@pytest.mark.parametrize("knowledge_base_id", [None, str(KNOWLEDGE_BASE_ID)])
def test_retrieve_rejects_invalid_knowledge_base_id_before_embedding(
    knowledge_base_id: object,
) -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    with pytest.raises(RetrieverInputError, match="Knowledge Base"):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=knowledge_base_id,  # type: ignore[arg-type]
            )
        )

    assert provider.queries == []
    assert store.search_queries == []


@pytest.mark.parametrize("top_k", [True, 5.0, "5", 0, 101])
def test_retrieve_rejects_invalid_top_k_before_embedding(
    top_k: object,
) -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    with pytest.raises(RetrieverInputError, match="top_k"):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                top_k=top_k,  # type: ignore[arg-type]
            )
        )

    assert provider.queries == []
    assert store.search_queries == []


@pytest.mark.parametrize(
    "score_threshold",
    [True, "0.5", nan, inf, -inf, 10**400],
)
def test_retrieve_rejects_invalid_threshold_before_embedding(
    score_threshold: object,
) -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore()

    with pytest.raises(RetrieverInputError, match="score_threshold"):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                score_threshold=score_threshold,  # type: ignore[arg-type]
            )
        )

    assert provider.queries == []
    assert store.search_queries == []


def test_retrieve_rejects_multiple_query_vectors_before_search() -> None:
    provider = RecordingEmbeddingProvider(
        result=make_embedding_result(
            vectors=((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
        )
    )
    store = RecordingVectorStore()

    with pytest.raises(
        RetrieverResponseError,
        match="query embedding response is invalid",
    ):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="private question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )

    assert store.search_queries == []


def test_retrieve_rejects_query_vector_dimension_mismatch() -> None:
    provider = RecordingEmbeddingProvider(
        result=make_embedding_result(vectors=((0.1, 0.2),))
    )
    store = RecordingVectorStore(dimension=3)

    with pytest.raises(
        RetrieverResponseError,
        match="query embedding response is invalid",
    ):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="private question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )

    assert store.search_queries == []


def test_retrieve_rejects_result_outside_requested_knowledge_base() -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore(
        results=(
            make_search_result(
                knowledge_base_id=OTHER_KNOWLEDGE_BASE_ID
            ),
        )
    )

    with pytest.raises(
        RetrieverResponseError,
        match="vector search response is invalid",
    ):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="private question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )


@pytest.mark.parametrize(
    "result_overrides",
    [
        {"embedding_provider": "other-provider"},
        {"embedding_model": "other-model"},
    ],
)
def test_retrieve_rejects_result_outside_query_embedding_identity(
    result_overrides: dict[str, str],
) -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore(
        results=(make_search_result(**result_overrides),)
    )

    with pytest.raises(
        RetrieverResponseError,
        match="vector search response is invalid",
    ):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="private question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )


def test_retrieve_rejects_more_results_than_requested_top_k() -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore(
        results=(
            make_search_result(),
            make_search_result(
                chunk_id=SECOND_CHUNK_ID,
                chunk_index=1,
            ),
        )
    )

    with pytest.raises(
        RetrieverResponseError,
        match="vector search response is invalid",
    ):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                top_k=1,
            )
        )


def test_retrieve_rejects_result_below_requested_threshold() -> None:
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore(
        results=(make_search_result(score=0.79),)
    )

    with pytest.raises(
        RetrieverResponseError,
        match="vector search response is invalid",
    ):
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                score_threshold=0.8,
            )
        )


def test_retrieve_preserves_embedding_provider_error() -> None:
    error = EmbeddingProviderResponseError("Synthetic provider failure.")
    provider = RecordingEmbeddingProvider(fail_with=error)
    store = RecordingVectorStore()

    with pytest.raises(EmbeddingProviderResponseError) as raised:
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )

    assert raised.value is error
    assert store.search_queries == []


def test_retrieve_preserves_vector_store_error() -> None:
    error = VectorStoreOperationError("Synthetic vector failure.")
    provider = RecordingEmbeddingProvider()
    store = RecordingVectorStore(fail_with=error)

    with pytest.raises(VectorStoreOperationError) as raised:
        asyncio.run(
            make_retriever(provider, store).retrieve(
                query="question",
                knowledge_base_id=KNOWLEDGE_BASE_ID,
            )
        )

    assert raised.value is error


def test_retrieve_copies_nested_source_metadata() -> None:
    provider = RecordingEmbeddingProvider()
    source = make_search_result()
    source.payload.metadata["nested"] = {"line": 1}
    store = RecordingVectorStore(results=(source,))

    results = asyncio.run(
        make_retriever(provider, store).retrieve(
            query="question",
            knowledge_base_id=KNOWLEDGE_BASE_ID,
        )
    )
    nested = results[0].metadata["nested"]
    assert isinstance(nested, dict)
    nested["line"] = 99

    assert source.payload.metadata["nested"] == {"line": 1}
