import asyncio
from dataclasses import dataclass
from math import inf
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.rag.vectorstores import (
    ChunkVectorPayload,
    QdrantVectorStore,
    VectorPoint,
    VectorSearchQuery,
    VectorStoreConfigurationError,
    VectorStoreDimensionMismatchError,
    VectorStoreInputError,
    VectorStoreOperationError,
    VectorStoreResponseError,
    create_qdrant_vector_store,
)


KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_KNOWLEDGE_BASE_ID = UUID(
    "00000000-0000-0000-0000-000000000009"
)
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000003")


def sample_payload(
    *,
    knowledge_base_id: UUID = KNOWLEDGE_BASE_ID,
    embedding_provider: str = "openai_compatible",
    embedding_model: str = "text-embedding-3-small",
) -> ChunkVectorPayload:
    return ChunkVectorPayload(
        knowledge_base_id=knowledge_base_id,
        document_id=DOCUMENT_ID,
        chunk_id=CHUNK_ID,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        filename="README.md",
        chunk_index=0,
        content="AI Agent Lab overview",
        heading="Overview",
        page_number=None,
        metadata={"source_format": "md"},
    )


def sample_point() -> VectorPoint:
    return VectorPoint(
        id=CHUNK_ID,
        vector=(0.1, 0.2, 0.3),
        payload=sample_payload(),
    )


@dataclass
class FakeVectorConfig:
    size: int
    distance: object


@dataclass
class FakeScoredPoint:
    id: object
    version: int
    score: object
    payload: object
    vector: object = None
    shard_key: object = None
    order_value: object = None


@dataclass
class FakeQueryResponse:
    points: list[FakeScoredPoint]


class FakeAsyncQdrantClient:
    def __init__(
        self,
        *,
        exists: bool = False,
        vectors_config: object | None = None,
        query_response: object | None = None,
    ) -> None:
        self.exists = exists
        self.vectors_config = vectors_config
        self.query_response = query_response or FakeQueryResponse(points=[])
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_method: str | None = None
        self.upsert_status: object = "completed"
        self.delete_status: object = "completed"
        self.concurrent_create_config: object | None = None
        self.closed = False

    async def collection_exists(self, **kwargs: Any) -> bool:
        self._record("collection_exists", kwargs)
        return self.exists

    async def create_collection(self, **kwargs: Any) -> bool:
        self._record("create_collection", kwargs)
        if self.concurrent_create_config is not None:
            self.exists = True
            self.vectors_config = self.concurrent_create_config
            raise RuntimeError("collection was created concurrently")
        self.exists = True
        self.vectors_config = kwargs["vectors_config"]
        return True

    async def get_collection(self, **kwargs: Any) -> object:
        self._record("get_collection", kwargs)
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(vectors=self.vectors_config)
            )
        )

    async def upsert(self, **kwargs: Any) -> object:
        self._record("upsert", kwargs)
        return SimpleNamespace(status=self.upsert_status)

    async def query_points(self, **kwargs: Any) -> object:
        self._record("query_points", kwargs)
        return self.query_response

    async def delete(self, **kwargs: Any) -> object:
        self._record("delete", kwargs)
        return SimpleNamespace(status=self.delete_status)

    async def close(self) -> None:
        self._record("close", {})
        self.closed = True

    def _record(self, method: str, kwargs: dict[str, Any]) -> None:
        if self.fail_method == method:
            raise RuntimeError(
                "http://private-qdrant.invalid leaked-response-body"
            )
        self.calls.append((method, kwargs))

    def call(self, method: str) -> dict[str, Any]:
        return next(kwargs for name, kwargs in self.calls if name == method)


def make_store(
    client: FakeAsyncQdrantClient,
    *,
    owns_client: bool = False,
) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=client,  # type: ignore[arg-type]
        collection_name="ai_agent_lab_chunks",
        dimension=3,
        owns_client=owns_client,
    )


def test_ensure_collection_creates_and_rechecks_cosine_config() -> None:
    async def exercise() -> tuple[object, FakeAsyncQdrantClient]:
        client = FakeAsyncQdrantClient()
        status = await make_store(client).ensure_collection()
        return status, client

    status, client = asyncio.run(exercise())

    create = client.call("create_collection")
    assert create["collection_name"] == "ai_agent_lab_chunks"
    assert create["vectors_config"].size == 3
    assert create["vectors_config"].distance.value == "Cosine"
    assert [name for name, _ in client.calls] == [
        "collection_exists",
        "create_collection",
        "get_collection",
    ]
    assert status.collection_name == "ai_agent_lab_chunks"
    assert status.dimension == 3
    assert status.distance == "cosine"
    assert status.created is True


def test_ensure_collection_accepts_matching_existing_collection() -> None:
    client = FakeAsyncQdrantClient(
        exists=True,
        vectors_config=FakeVectorConfig(size=3, distance="Cosine"),
    )

    status = asyncio.run(make_store(client).ensure_collection())

    assert status.created is False
    assert not any(name == "create_collection" for name, _ in client.calls)


def test_ensure_collection_recovers_compatible_concurrent_creation() -> None:
    client = FakeAsyncQdrantClient()
    client.concurrent_create_config = FakeVectorConfig(
        size=3,
        distance="Cosine",
    )

    status = asyncio.run(make_store(client).ensure_collection())

    assert status.created is False
    assert [name for name, _ in client.calls] == [
        "collection_exists",
        "create_collection",
        "get_collection",
    ]


def test_ensure_collection_rejects_incompatible_concurrent_creation() -> None:
    client = FakeAsyncQdrantClient()
    client.concurrent_create_config = FakeVectorConfig(
        size=4,
        distance="Cosine",
    )

    with pytest.raises(VectorStoreDimensionMismatchError):
        asyncio.run(make_store(client).ensure_collection())


@pytest.mark.parametrize(
    ("vectors_config", "error_type"),
    [
        (
            FakeVectorConfig(size=4, distance="Cosine"),
            VectorStoreDimensionMismatchError,
        ),
        (
            FakeVectorConfig(size=3, distance="Dot"),
            VectorStoreConfigurationError,
        ),
        (
            {"dense": FakeVectorConfig(size=3, distance="Cosine")},
            VectorStoreConfigurationError,
        ),
    ],
)
def test_ensure_collection_rejects_incompatible_existing_config(
    vectors_config: object,
    error_type: type[VectorStoreConfigurationError],
) -> None:
    client = FakeAsyncQdrantClient(
        exists=True,
        vectors_config=vectors_config,
    )

    with pytest.raises(error_type):
        asyncio.run(make_store(client).ensure_collection())


def test_upsert_maps_validated_points_and_waits_for_completion() -> None:
    async def exercise() -> tuple[tuple[UUID, ...], FakeAsyncQdrantClient]:
        client = FakeAsyncQdrantClient()
        point_ids = await make_store(client).upsert([sample_point()])
        return point_ids, client

    point_ids, client = asyncio.run(exercise())

    upsert = client.call("upsert")
    assert upsert["collection_name"] == "ai_agent_lab_chunks"
    assert upsert["wait"] is True
    assert len(upsert["points"]) == 1
    qdrant_point = upsert["points"][0]
    assert type(qdrant_point).__name__ == "PointStruct"
    assert qdrant_point.id == str(CHUNK_ID)
    assert qdrant_point.vector == [0.1, 0.2, 0.3]
    assert qdrant_point.payload == sample_payload().to_qdrant_payload()
    assert point_ids == (CHUNK_ID,)


def test_upsert_rejects_empty_or_wrong_dimension_before_network() -> None:
    client = FakeAsyncQdrantClient()
    store = make_store(client)

    with pytest.raises(VectorStoreInputError, match="must not be empty"):
        asyncio.run(store.upsert([]))
    wrong_dimension = sample_point().model_copy(update={"vector": (0.1,)})
    with pytest.raises(VectorStoreDimensionMismatchError):
        asyncio.run(store.upsert([wrong_dimension]))

    assert client.calls == []


@pytest.mark.parametrize(
    ("operation", "status"),
    [
        ("upsert", "acknowledged"),
        ("upsert", None),
        ("delete", "acknowledged"),
        ("delete", object()),
    ],
)
def test_write_operations_reject_non_completed_responses(
    operation: str,
    status: object,
) -> None:
    client = FakeAsyncQdrantClient()
    if operation == "upsert":
        client.upsert_status = status
    else:
        client.delete_status = status
    store = make_store(client)

    async def exercise() -> None:
        if operation == "upsert":
            await store.upsert([sample_point()])
        else:
            await store.delete_document_vectors(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                document_id=DOCUMENT_ID,
            )

    with pytest.raises(
        VectorStoreResponseError,
        match=f"Qdrant vector {operation} response is invalid",
    ) as raised:
        asyncio.run(exercise())

    assert raised.value.__cause__ is None


def test_search_filters_knowledge_base_and_maps_complete_payload() -> None:
    response = FakeQueryResponse(
        points=[
            FakeScoredPoint(
                id=str(CHUNK_ID),
                version=1,
                score=0.91,
                payload=sample_payload().to_qdrant_payload(),
            )
        ]
    )
    client = FakeAsyncQdrantClient(query_response=response)
    query = VectorSearchQuery(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        embedding_provider="openai_compatible",
        embedding_model="text-embedding-3-small",
        vector=(0.3, 0.2, 0.1),
        limit=4,
        score_threshold=0.25,
    )

    results = asyncio.run(make_store(client).search(query))

    request = client.call("query_points")
    assert request["collection_name"] == "ai_agent_lab_chunks"
    assert request["query"] == [0.3, 0.2, 0.1]
    assert request["limit"] == 4
    assert request["score_threshold"] == 0.25
    assert request["with_payload"] is True
    assert request["with_vectors"] is False
    assert request["query_filter"].model_dump(mode="json") == {
        "should": None,
        "min_should": None,
        "must": [
            {
                "key": "knowledge_base_id",
                "match": {
                    "value": str(KNOWLEDGE_BASE_ID),
                },
                "range": None,
                "geo_bounding_box": None,
                "geo_radius": None,
                "geo_polygon": None,
                "values_count": None,
                "is_empty": None,
                "is_null": None,
            },
            {
                "key": "embedding_provider",
                "match": {"value": "openai_compatible"},
                "range": None,
                "geo_bounding_box": None,
                "geo_radius": None,
                "geo_polygon": None,
                "values_count": None,
                "is_empty": None,
                "is_null": None,
            },
            {
                "key": "embedding_model",
                "match": {"value": "text-embedding-3-small"},
                "range": None,
                "geo_bounding_box": None,
                "geo_radius": None,
                "geo_polygon": None,
                "values_count": None,
                "is_empty": None,
                "is_null": None,
            }
        ],
        "must_not": None,
    }
    assert results[0].point_id == CHUNK_ID
    assert results[0].score == 0.91
    assert results[0].payload == sample_payload()


@pytest.mark.parametrize(
    ("point_id", "score", "payload"),
    [
        ("not-a-uuid", 0.9, sample_payload().to_qdrant_payload()),
        (str(CHUNK_ID), inf, sample_payload().to_qdrant_payload()),
        (str(CHUNK_ID), 0.9, {"chunk_id": str(CHUNK_ID)}),
        (str(CHUNK_ID), 0.9, None),
    ],
)
def test_search_rejects_malformed_qdrant_results(
    point_id: object,
    score: object,
    payload: object,
) -> None:
    client = FakeAsyncQdrantClient(
        query_response=FakeQueryResponse(
            points=[
                FakeScoredPoint(
                    id=point_id,
                    version=1,
                    score=score,
                    payload=payload,
                )
            ]
        )
    )

    with pytest.raises(
        VectorStoreResponseError,
        match="Qdrant search response is invalid",
    ) as raised:
        asyncio.run(
            make_store(client).search(
                VectorSearchQuery(
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    embedding_provider="openai_compatible",
                    embedding_model="text-embedding-3-small",
                    vector=(0.1, 0.2, 0.3),
                )
            )
        )

    assert raised.value.__cause__ is None


def test_search_rejects_result_outside_requested_knowledge_base() -> None:
    client = FakeAsyncQdrantClient(
        query_response=FakeQueryResponse(
            points=[
                FakeScoredPoint(
                    id=str(CHUNK_ID),
                    version=1,
                    score=0.9,
                    payload=sample_payload(
                        knowledge_base_id=OTHER_KNOWLEDGE_BASE_ID
                    ).to_qdrant_payload(),
                )
            ]
        )
    )

    with pytest.raises(
        VectorStoreResponseError,
        match="Qdrant search response is invalid",
    ):
        asyncio.run(
            make_store(client).search(
                VectorSearchQuery(
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    embedding_provider="openai_compatible",
                    embedding_model="text-embedding-3-small",
                    vector=(0.1, 0.2, 0.3),
                )
            )
        )


@pytest.mark.parametrize(
    ("payload_overrides"),
    [
        {"embedding_provider": "other-provider"},
        {"embedding_model": "other-model"},
    ],
)
def test_search_rejects_result_outside_requested_embedding_identity(
    payload_overrides: dict[str, str],
) -> None:
    client = FakeAsyncQdrantClient(
        query_response=FakeQueryResponse(
            points=[
                FakeScoredPoint(
                    id=str(CHUNK_ID),
                    version=1,
                    score=0.9,
                    payload=sample_payload(
                        **payload_overrides,
                    ).to_qdrant_payload(),
                )
            ]
        )
    )

    with pytest.raises(
        VectorStoreResponseError,
        match="Qdrant search response is invalid",
    ):
        asyncio.run(
            make_store(client).search(
                VectorSearchQuery(
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    embedding_provider="openai_compatible",
                    embedding_model="text-embedding-3-small",
                    vector=(0.1, 0.2, 0.3),
                )
            )
        )


def test_delete_document_vectors_uses_both_ownership_filters() -> None:
    client = FakeAsyncQdrantClient()

    asyncio.run(
        make_store(client).delete_document_vectors(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
        )
    )

    request = client.call("delete")
    assert request["collection_name"] == "ai_agent_lab_chunks"
    assert request["wait"] is True
    conditions = request["points_selector"].filter.must
    assert [(item.key, item.match.value) for item in conditions] == [
        ("knowledge_base_id", str(KNOWLEDGE_BASE_ID)),
        ("document_id", str(DOCUMENT_ID)),
    ]


@pytest.mark.parametrize(
    ("method", "operation"),
    [
        ("collection_exists", "collection check"),
        ("upsert", "vector upsert"),
        ("query_points", "vector search"),
        ("delete", "vector delete"),
    ],
)
def test_qdrant_errors_are_safe_and_do_not_chain_source_exception(
    method: str,
    operation: str,
) -> None:
    client = FakeAsyncQdrantClient(
        vectors_config=FakeVectorConfig(size=3, distance="Cosine")
    )
    client.fail_method = method
    store = make_store(client)

    async def exercise() -> None:
        if method == "collection_exists":
            await store.ensure_collection()
        elif method == "upsert":
            await store.upsert([sample_point()])
        elif method == "query_points":
            await store.search(
                VectorSearchQuery(
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    embedding_provider="openai_compatible",
                    embedding_model="text-embedding-3-small",
                    vector=(0.1, 0.2, 0.3),
                )
            )
        else:
            await store.delete_document_vectors(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                document_id=DOCUMENT_ID,
            )

    with pytest.raises(
        VectorStoreOperationError,
        match=f"Qdrant {operation} failed",
    ) as raised:
        asyncio.run(exercise())

    assert "private-qdrant" not in str(raised.value)
    assert "leaked-response-body" not in str(raised.value)
    assert raised.value.__cause__ is None


def test_close_only_closes_owned_client() -> None:
    async def exercise() -> tuple[bool, bool]:
        injected = FakeAsyncQdrantClient()
        owned = FakeAsyncQdrantClient()
        await make_store(injected).close()
        await make_store(owned, owns_client=True).close()
        return injected.closed, owned.closed

    injected_closed, owned_closed = asyncio.run(exercise())

    assert injected_closed is False
    assert owned_closed is True


def configured_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION_NAME": "configured_chunks",
        "QDRANT_TIMEOUT_SECONDS": 12,
        "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION": 3,
    }
    values.update(overrides)
    return Settings(**values)


def test_factory_builds_store_from_lazy_settings_with_injected_client() -> None:
    client = FakeAsyncQdrantClient()

    store = create_qdrant_vector_store(
        configured_settings(),
        client=client,  # type: ignore[arg-type]
    )

    assert store.collection_name == "configured_chunks"
    assert store.dimension == 3
    asyncio.run(store.close())
    assert client.closed is False


def test_factory_rejects_missing_embedding_dimension() -> None:
    with pytest.raises(
        VectorStoreConfigurationError,
        match="OPENAI_COMPATIBLE_EMBEDDING_DIMENSION is required",
    ):
        create_qdrant_vector_store(
            configured_settings(
                OPENAI_COMPATIBLE_EMBEDDING_DIMENSION=None
            ),
            client=FakeAsyncQdrantClient(),  # type: ignore[arg-type]
        )
