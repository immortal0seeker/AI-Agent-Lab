import logging
from uuid import UUID

from app.core.logging import safe_stack_locations
from app.models import Document, DocumentChunk
from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingProviderResponseError,
)
from app.rag.vectorstores import (
    VectorPoint,
    VectorStore,
    VectorStoreDimensionMismatchError,
    VectorStoreError,
    VectorStoreInputError,
    VectorStoreResponseError,
    build_qdrant_payload,
)

logger = logging.getLogger(__name__)


async def ingest_document_vectors(
    *,
    document: Document,
    chunks: list[DocumentChunk],
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
) -> tuple[UUID, ...]:
    _validate_chunks(document, chunks)
    await vector_store.ensure_collection()
    result = await embedding_provider.embed_texts(
        [chunk.content for chunk in chunks]
    )
    if len(result.vectors) != len(chunks):
        raise EmbeddingProviderResponseError(
            "Embedding Provider returned an unexpected vector count."
        )
    if result.dimension != vector_store.dimension:
        raise VectorStoreDimensionMismatchError(
            "Embedding and Vector Store dimensions do not match."
        )

    points = [
        VectorPoint(
            id=chunk.id,
            vector=result.vectors[index],
            payload=build_qdrant_payload(document=document, chunk=chunk),
        )
        for index, chunk in enumerate(chunks)
    ]
    expected_ids = tuple(chunk.id for chunk in chunks)
    try:
        point_ids = await vector_store.upsert(points)
    except VectorStoreError:
        await _delete_document_vectors_safely(
            vector_store=vector_store,
            document=document,
        )
        raise
    if point_ids != expected_ids:
        await _delete_document_vectors_safely(
            vector_store=vector_store,
            document=document,
        )
        raise VectorStoreResponseError(
            "Vector Store returned unexpected point identifiers."
        )
    return point_ids


def _validate_chunks(
    document: Document,
    chunks: list[DocumentChunk],
) -> None:
    if not isinstance(document, Document):
        raise VectorStoreInputError(
            "Document vector ingestion requires a Document."
        )
    if not isinstance(chunks, list) or not chunks:
        raise VectorStoreInputError(
            "Document vector ingestion requires chunks."
        )
    for expected_index, chunk in enumerate(chunks):
        if not isinstance(chunk, DocumentChunk):
            raise VectorStoreInputError(
                "Document vector ingestion requires DocumentChunk items."
            )
        if (
            chunk.document_id != document.id
            or chunk.knowledge_base_id != document.knowledge_base_id
            or chunk.chunk_index != expected_index
        ):
            raise VectorStoreInputError(
                "Document chunks have invalid ownership or order."
            )


async def _delete_document_vectors_safely(
    *,
    vector_store: VectorStore,
    document: Document,
) -> None:
    try:
        await vector_store.delete_document_vectors(
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
        )
    except Exception as exc:
        logger.warning(
            "document_vector_compensation_failed",
            extra={
                "knowledge_base_id": str(document.knowledge_base_id),
                "document_id": str(document.id),
                "stack_locations": safe_stack_locations(exc),
            },
        )
