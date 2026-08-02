import asyncio
from uuid import UUID, uuid4

import pytest

from app.models import Document, DocumentChunk
from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingProviderResponseError,
    EmbeddingResult,
    EmbeddingUsage,
)
from app.rag.ingestion_pipeline import ingest_document_vectors
from app.rag.vectorstores import (
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
    VectorStoreDimensionMismatchError,
    VectorStoreInputError,
    VectorStoreOperationError,
    VectorStoreResponseError,
)


class DeterministicEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        vectors: tuple[tuple[float, ...], ...],
    ) -> None:
        super().__init__(name="deterministic")
        self._vectors = vectors
        self.received_texts: list[str] | None = None

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        self.received_texts = list(texts)
        return EmbeddingResult(
            model="synthetic-embedding",
            vectors=self._vectors,
            usage=EmbeddingUsage(
                input_tokens=len(texts),
                total_tokens=len(texts),
            ),
        )

    async def embed_query(self, query: str) -> EmbeddingResult:
        return await self.embed_texts([query])


class RecordingVectorStore(VectorStore):
    def __init__(
        self,
        *,
        dimension: int = 3,
        returned_ids: tuple[UUID, ...] | None = None,
        fail_upsert_after_write: bool = False,
    ) -> None:
        self._dimension = dimension
        self._returned_ids = returned_ids
        self._fail_upsert_after_write = fail_upsert_after_write
        self.ensure_calls = 0
        self.upserted_points: list[VectorPoint] = []
        self.deleted_documents: list[tuple[UUID, UUID]] = []

    @property
    def collection_name(self) -> str:
        return "synthetic_chunks"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def ensure_collection(self) -> VectorCollectionStatus:
        self.ensure_calls += 1
        return VectorCollectionStatus(
            collection_name=self.collection_name,
            dimension=self.dimension,
            distance="cosine",
            created=False,
        )

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        self.upserted_points = list(points)
        if self._fail_upsert_after_write:
            raise VectorStoreOperationError("synthetic upsert failure")
        if self._returned_ids is not None:
            return self._returned_ids
        return tuple(point.id for point in points)

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        return ()

    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        self.deleted_documents.append((knowledge_base_id, document_id))
        self.upserted_points = []

    async def close(self) -> None:
        return None


def build_document_and_chunks() -> tuple[Document, list[DocumentChunk]]:
    knowledge_base_id = uuid4()
    document_id = uuid4()
    document = Document(
        id=document_id,
        knowledge_base_id=knowledge_base_id,
        filename="guide.md",
        original_filename="guide.md",
        file_type="md",
        file_path=f"{knowledge_base_id}/{document_id}.md",
        file_size=20,
        file_hash="a" * 64,
        metadata_json={},
    )
    chunks = [
        DocumentChunk(
            id=uuid4(),
            document_id=document_id,
            knowledge_base_id=knowledge_base_id,
            chunk_index=index,
            content=content,
            token_count=2,
            char_count=len(content),
            heading="Intro" if index == 0 else None,
            page_number=None,
            metadata_json={"start_char": index * 10},
        )
        for index, content in enumerate(["first chunk", "second chunk"])
    ]
    return document, chunks


def test_ingestion_pipeline_embeds_and_upserts_complete_chunk_points() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(
        ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
    )
    store = RecordingVectorStore()

    point_ids = asyncio.run(
        ingest_document_vectors(
            document=document,
            chunks=chunks,
            embedding_provider=provider,
            vector_store=store,
        )
    )

    assert store.ensure_calls == 1
    assert provider.received_texts == ["first chunk", "second chunk"]
    assert point_ids == tuple(chunk.id for chunk in chunks)
    assert [point.id for point in store.upserted_points] == list(point_ids)
    assert [point.vector for point in store.upserted_points] == [
        (0.1, 0.2, 0.3),
        (0.4, 0.5, 0.6),
    ]
    first_payload = store.upserted_points[0].payload
    assert first_payload.knowledge_base_id == document.knowledge_base_id
    assert first_payload.document_id == document.id
    assert first_payload.chunk_id == chunks[0].id
    assert first_payload.embedding_provider == "deterministic"
    assert first_payload.embedding_model == "synthetic-embedding"
    assert first_payload.filename == "guide.md"
    assert first_payload.content == "first chunk"
    assert first_payload.heading == "Intro"
    assert first_payload.metadata == {"start_char": 0}


def test_ingestion_pipeline_rejects_empty_chunks_before_external_calls() -> None:
    document, _ = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(((0.1, 0.2, 0.3),))
    store = RecordingVectorStore()

    with pytest.raises(VectorStoreInputError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=[],
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.ensure_calls == 0
    assert provider.received_texts is None


def test_ingestion_pipeline_rejects_mismatched_ownership() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(
        ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
    )
    store = RecordingVectorStore()
    chunks[0].knowledge_base_id = uuid4()

    with pytest.raises(VectorStoreInputError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=chunks,
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.ensure_calls == 0
    assert provider.received_texts is None


def test_ingestion_pipeline_rejects_unstable_chunk_order() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(
        ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
    )
    store = RecordingVectorStore()

    with pytest.raises(VectorStoreInputError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=list(reversed(chunks)),
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.ensure_calls == 0
    assert provider.received_texts is None


def test_ingestion_pipeline_rejects_embedding_result_count() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(((0.1, 0.2, 0.3),))
    store = RecordingVectorStore()

    with pytest.raises(EmbeddingProviderResponseError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=chunks,
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.upserted_points == []


def test_ingestion_pipeline_rejects_vector_store_dimension_mismatch() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(
        ((0.1, 0.2), (0.3, 0.4))
    )
    store = RecordingVectorStore(dimension=3)

    with pytest.raises(VectorStoreDimensionMismatchError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=chunks,
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.upserted_points == []


def test_ingestion_pipeline_compensates_untrusted_upsert_ids() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(
        ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
    )
    store = RecordingVectorStore(
        returned_ids=(chunks[1].id, chunks[0].id)
    )

    with pytest.raises(VectorStoreResponseError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=chunks,
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.deleted_documents == [
        (document.knowledge_base_id, document.id)
    ]
    assert store.upserted_points == []


def test_ingestion_pipeline_compensates_uncertain_upsert_failure() -> None:
    document, chunks = build_document_and_chunks()
    provider = DeterministicEmbeddingProvider(
        ((0.1, 0.2, 0.3), (0.4, 0.5, 0.6))
    )
    store = RecordingVectorStore(fail_upsert_after_write=True)

    with pytest.raises(VectorStoreOperationError):
        asyncio.run(
            ingest_document_vectors(
                document=document,
                chunks=chunks,
                embedding_provider=provider,
                vector_store=store,
            )
        )

    assert store.deleted_documents == [
        (document.knowledge_base_id, document.id)
    ]
    assert store.upserted_points == []
