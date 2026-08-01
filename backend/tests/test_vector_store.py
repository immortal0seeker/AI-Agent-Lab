import asyncio
from math import inf, nan
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.rag.vectorstores import (
    ChunkVectorPayload,
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
    VectorStoreConfigurationError,
    VectorStoreDimensionMismatchError,
    VectorStoreError,
    VectorStoreInputError,
    VectorStoreOperationError,
    VectorStoreResponseError,
)


KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000003")


def sample_payload() -> ChunkVectorPayload:
    return ChunkVectorPayload(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        chunk_id=CHUNK_ID,
        filename="README.md",
        chunk_index=0,
        content="AI Agent Lab overview",
        heading="Overview",
        page_number=None,
        metadata={"source_format": "md", "start_char": 0, "end_char": 21},
    )


class MockVectorStore(VectorStore):
    def __init__(self) -> None:
        self.points: dict[UUID, VectorPoint] = {}
        self.closed = False

    @property
    def collection_name(self) -> str:
        return "mock_chunks"

    @property
    def dimension(self) -> int:
        return 3

    async def ensure_collection(self) -> VectorCollectionStatus:
        return VectorCollectionStatus(
            collection_name=self.collection_name,
            dimension=self.dimension,
            distance="cosine",
            created=True,
        )

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        for point in points:
            self.points[point.id] = point
        return tuple(point.id for point in points)

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        return tuple(
            VectorSearchResult(
                point_id=point.id,
                score=0.9,
                payload=point.payload,
            )
            for point in self.points.values()
            if point.payload.knowledge_base_id == query.knowledge_base_id
        )[: query.limit]

    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        self.points = {
            point_id: point
            for point_id, point in self.points.items()
            if not (
                point.payload.knowledge_base_id == knowledge_base_id
                and point.payload.document_id == document_id
            )
        }

    async def close(self) -> None:
        self.closed = True


def test_vector_store_contract_is_replaceable() -> None:
    async def exercise() -> tuple[
        VectorCollectionStatus,
        tuple[UUID, ...],
        tuple[VectorSearchResult, ...],
        bool,
    ]:
        store = MockVectorStore()
        point = VectorPoint(
            id=CHUNK_ID,
            vector=(0.1, 0.2, 0.3),
            payload=sample_payload(),
        )
        status = await store.ensure_collection()
        point_ids = await store.upsert([point])
        results = await store.search(
            VectorSearchQuery(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                vector=(0.3, 0.2, 0.1),
                limit=5,
            )
        )
        await store.delete_document_vectors(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
        )
        assert store.points == {}
        await store.close()
        return status, point_ids, results, store.closed

    status, point_ids, results, closed = asyncio.run(exercise())

    assert status == VectorCollectionStatus(
        collection_name="mock_chunks",
        dimension=3,
        distance="cosine",
        created=True,
    )
    assert point_ids == (CHUNK_ID,)
    assert results == (
        VectorSearchResult(
            point_id=CHUNK_ID,
            score=0.9,
            payload=sample_payload(),
        ),
    )
    assert closed is True


def test_vector_point_normalizes_copies_and_freezes_vector() -> None:
    vector = [0, 1.5, 2]
    point = VectorPoint(
        id=CHUNK_ID,
        vector=vector,
        payload=sample_payload(),
    )
    vector[0] = 99

    assert point.vector == (0.0, 1.5, 2.0)
    with pytest.raises(ValidationError):
        point.vector = (1.0,)  # type: ignore[misc]


def test_vector_point_and_result_require_chunk_id_traceability() -> None:
    other_chunk_id = UUID("00000000-0000-0000-0000-000000000099")

    with pytest.raises(ValidationError, match="point id must match chunk id"):
        VectorPoint(
            id=other_chunk_id,
            vector=(0.1, 0.2, 0.3),
            payload=sample_payload(),
        )
    with pytest.raises(ValidationError, match="point id must match chunk id"):
        VectorSearchResult(
            point_id=other_chunk_id,
            score=0.9,
            payload=sample_payload(),
        )


@pytest.mark.parametrize(
    "vector",
    [
        (),
        (nan,),
        (inf,),
        (-inf,),
        (True,),
        ("1.0",),
    ],
)
def test_vector_point_rejects_invalid_vectors(vector: object) -> None:
    with pytest.raises(ValidationError):
        VectorPoint(id=CHUNK_ID, vector=vector, payload=sample_payload())


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("vector", ()),
        ("vector", (nan,)),
        ("vector", (True,)),
        ("limit", 0),
        ("limit", 101),
        ("limit", True),
        ("score_threshold", inf),
    ],
)
def test_vector_search_query_rejects_invalid_values(
    field_name: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "vector": (0.1, 0.2, 0.3),
        "limit": 5,
    }
    values[field_name] = value

    with pytest.raises(ValidationError):
        VectorSearchQuery.model_validate(values)


@pytest.mark.parametrize("score", [nan, inf, -inf, True, "0.9"])
def test_vector_search_result_rejects_invalid_scores(score: object) -> None:
    with pytest.raises(ValidationError):
        VectorSearchResult(
            point_id=CHUNK_ID,
            score=score,
            payload=sample_payload(),
        )


def test_vector_collection_status_rejects_invalid_contract_values() -> None:
    with pytest.raises(ValidationError):
        VectorCollectionStatus(
            collection_name=" ",
            dimension=0,
            distance="dot",  # type: ignore[arg-type]
            created=1,
        )


def test_vector_store_errors_stay_in_one_boundary() -> None:
    assert issubclass(VectorStoreConfigurationError, VectorStoreError)
    assert issubclass(VectorStoreInputError, VectorStoreError)
    assert issubclass(VectorStoreOperationError, VectorStoreError)
    assert issubclass(VectorStoreResponseError, VectorStoreError)
    assert issubclass(
        VectorStoreDimensionMismatchError,
        VectorStoreConfigurationError,
    )
