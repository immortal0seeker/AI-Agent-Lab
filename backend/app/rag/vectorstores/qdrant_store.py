from uuid import UUID

from pydantic import ValidationError
from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings
from app.rag.vectorstores.base import (
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
    VectorStoreConfigurationError,
    VectorStoreDimensionMismatchError,
    VectorStoreInputError,
    VectorStoreOperationError,
    VectorStoreResponseError,
)
from app.rag.vectorstores.payload import ChunkVectorPayload


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        *,
        client: AsyncQdrantClient,
        collection_name: str,
        dimension: int,
        owns_client: bool = False,
    ) -> None:
        self._collection_name = _validate_collection_name(collection_name)
        if (
            isinstance(dimension, bool)
            or not isinstance(dimension, int)
            or dimension <= 0
            or dimension > 65_536
        ):
            raise VectorStoreConfigurationError(
                "Vector Store dimension must be between 1 and 65536."
            )
        self._client = client
        self._dimension = dimension
        self._owns_client = owns_client

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def ensure_collection(self) -> VectorCollectionStatus:
        try:
            exists = await self._client.collection_exists(
                collection_name=self.collection_name
            )
            created = not exists
            if not exists:
                await self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
            info = await self._client.get_collection(
                collection_name=self.collection_name
            )
        except Exception:
            raise VectorStoreOperationError(
                "Qdrant collection check failed."
            ) from None

        self._validate_collection_info(info)
        return VectorCollectionStatus(
            collection_name=self.collection_name,
            dimension=self.dimension,
            distance="cosine",
            created=created,
        )

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        if not isinstance(points, list) or not points:
            raise VectorStoreInputError("Vector points must not be empty.")
        for point in points:
            if not isinstance(point, VectorPoint):
                raise VectorStoreInputError(
                    "Vector points must use the VectorPoint contract."
                )
            self._validate_vector_dimension(point.vector)
        qdrant_points = [
            models.PointStruct(
                id=str(point.id),
                vector=list(point.vector),
                payload=point.payload.to_qdrant_payload(),
            )
            for point in points
        ]
        try:
            result = await self._client.upsert(
                collection_name=self.collection_name,
                points=qdrant_points,
                wait=True,
            )
        except Exception:
            raise VectorStoreOperationError(
                "Qdrant vector upsert failed."
            ) from None
        self._validate_write_response(result, operation="upsert")
        return tuple(point.id for point in points)

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        if not isinstance(query, VectorSearchQuery):
            raise VectorStoreInputError(
                "Vector search must use the VectorSearchQuery contract."
            )
        self._validate_vector_dimension(query.vector)
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="knowledge_base_id",
                    match=models.MatchValue(
                        value=str(query.knowledge_base_id)
                    ),
                )
            ]
        )
        try:
            response = await self._client.query_points(
                collection_name=self.collection_name,
                query=list(query.vector),
                query_filter=query_filter,
                limit=query.limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=query.score_threshold,
            )
        except Exception:
            raise VectorStoreOperationError(
                "Qdrant vector search failed."
            ) from None
        return self._parse_search_response(
            response,
            knowledge_base_id=query.knowledge_base_id,
        )

    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        if not isinstance(knowledge_base_id, UUID) or not isinstance(
            document_id, UUID
        ):
            raise VectorStoreInputError(
                "Knowledge Base and Document identifiers must be UUIDs."
            )
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="knowledge_base_id",
                        match=models.MatchValue(
                            value=str(knowledge_base_id)
                        ),
                    ),
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=str(document_id)),
                    ),
                ]
            )
        )
        try:
            result = await self._client.delete(
                collection_name=self.collection_name,
                points_selector=selector,
                wait=True,
            )
        except Exception:
            raise VectorStoreOperationError(
                "Qdrant vector delete failed."
            ) from None
        self._validate_write_response(result, operation="delete")

    async def close(self) -> None:
        if not self._owns_client:
            return
        try:
            await self._client.close()
        except Exception:
            raise VectorStoreOperationError(
                "Qdrant client close failed."
            ) from None

    def _validate_collection_info(self, info: object) -> None:
        try:
            vectors_config = info.config.params.vectors  # type: ignore[union-attr]
        except (AttributeError, TypeError):
            raise VectorStoreResponseError(
                "Qdrant collection response is invalid."
            ) from None
        if isinstance(vectors_config, dict):
            raise VectorStoreConfigurationError(
                "Qdrant collection must use one default dense vector."
            )
        size = getattr(vectors_config, "size", None)
        if isinstance(size, bool) or not isinstance(size, int):
            raise VectorStoreResponseError(
                "Qdrant collection response is invalid."
            )
        if size != self.dimension:
            raise VectorStoreDimensionMismatchError(
                "Qdrant collection dimension mismatch: "
                f"expected {self.dimension}, received {size}."
            )
        distance = getattr(vectors_config, "distance", None)
        distance_value = getattr(distance, "value", distance)
        if distance_value != models.Distance.COSINE.value:
            raise VectorStoreConfigurationError(
                "Qdrant collection must use cosine distance."
            )

    def _validate_vector_dimension(self, vector: tuple[float, ...]) -> None:
        received = len(vector)
        if received != self.dimension:
            raise VectorStoreDimensionMismatchError(
                "Vector dimension mismatch: "
                f"expected {self.dimension}, received {received}."
            )

    def _validate_write_response(
        self,
        response: object,
        *,
        operation: str,
    ) -> None:
        status = getattr(response, "status", None)
        status_value = getattr(status, "value", status)
        if status_value != "completed":
            raise VectorStoreResponseError(
                f"Qdrant vector {operation} response is invalid."
            ) from None

    def _parse_search_response(
        self,
        response: object,
        *,
        knowledge_base_id: UUID,
    ) -> tuple[VectorSearchResult, ...]:
        points = getattr(response, "points", None)
        if not isinstance(points, list):
            raise VectorStoreResponseError(
                "Qdrant search response is invalid."
            )
        try:
            results = tuple(
                VectorSearchResult(
                    point_id=point.id,
                    score=point.score,
                    payload=ChunkVectorPayload.model_validate(point.payload),
                )
                for point in points
            )
            if any(
                result.payload.knowledge_base_id != knowledge_base_id
                for result in results
            ):
                raise ValueError("knowledge base filter mismatch")
            return results
        except (AttributeError, TypeError, ValueError, ValidationError):
            raise VectorStoreResponseError(
                "Qdrant search response is invalid."
            ) from None


def create_qdrant_vector_store(
    settings: Settings,
    *,
    collection_name: str | None = None,
    client: AsyncQdrantClient | None = None,
) -> QdrantVectorStore:
    dimension = settings.openai_compatible_embedding_dimension
    if dimension is None:
        raise VectorStoreConfigurationError(
            "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION is required "
            "to initialize the Vector Store."
        )
    owns_client = client is None
    if client is None:
        try:
            client = AsyncQdrantClient(
                url=settings.qdrant_url,
                timeout=settings.qdrant_timeout_seconds,
                prefer_grpc=False,
            )
        except Exception:
            raise VectorStoreConfigurationError(
                "Qdrant client configuration is invalid."
            ) from None
    return QdrantVectorStore(
        client=client,
        collection_name=(
            settings.qdrant_collection_name
            if collection_name is None
            else collection_name
        ),
        dimension=dimension,
        owns_client=owns_client,
    )


def _validate_collection_name(value: object) -> str:
    if not isinstance(value, str):
        raise VectorStoreConfigurationError(
            "Qdrant collection name is invalid."
        )
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > 255
        or any(
            not (
                character.isascii()
                and (character.isalnum() or character in "._-")
            )
            for character in normalized
        )
    ):
        raise VectorStoreConfigurationError(
            "Qdrant collection name is invalid."
        )
    return normalized
