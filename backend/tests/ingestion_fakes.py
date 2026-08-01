from uuid import UUID

from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingResult,
    EmbeddingUsage,
)
from app.rag.vectorstores import (
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
    VectorStoreError,
)


class DeterministicEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        fail_with: EmbeddingProviderError | None = None,
    ) -> None:
        super().__init__(name="deterministic")
        self.fail_with = fail_with
        self.received_batches: list[list[str]] = []

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        self.received_batches.append(list(texts))
        if self.fail_with is not None:
            raise self.fail_with
        return EmbeddingResult(
            model="synthetic-embedding",
            vectors=tuple(
                (float(index + 1), float(len(text)), 0.5)
                for index, text in enumerate(texts)
            ),
            usage=EmbeddingUsage(
                input_tokens=len(texts),
                total_tokens=len(texts),
            ),
        )

    async def embed_query(self, query: str) -> EmbeddingResult:
        return await self.embed_texts([query])


class InMemoryVectorStore(VectorStore):
    def __init__(
        self,
        *,
        fail_upsert_with: VectorStoreError | None = None,
    ) -> None:
        self.fail_upsert_with = fail_upsert_with
        self.points: dict[UUID, VectorPoint] = {}
        self.deleted_documents: list[tuple[UUID, UUID]] = []
        self.ensure_calls = 0
        self.closed = False

    @property
    def collection_name(self) -> str:
        return "synthetic_chunks"

    @property
    def dimension(self) -> int:
        return 3

    async def ensure_collection(self) -> VectorCollectionStatus:
        self.ensure_calls += 1
        return VectorCollectionStatus(
            collection_name=self.collection_name,
            dimension=self.dimension,
            distance="cosine",
            created=False,
        )

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        self.points.update({point.id: point for point in points})
        if self.fail_upsert_with is not None:
            raise self.fail_upsert_with
        return tuple(point.id for point in points)

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        return tuple(
            VectorSearchResult(
                point_id=point.id,
                score=1.0,
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
        self.deleted_documents.append((knowledge_base_id, document_id))
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
