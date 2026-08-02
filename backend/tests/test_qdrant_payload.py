from math import nan
from uuid import UUID

import pytest

from app.models import Document, DocumentChunk
from app.rag.vectorstores import (
    VectorStoreInputError,
    build_qdrant_payload,
)


KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000003")


def sample_document() -> Document:
    return Document(
        id=DOCUMENT_ID,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        filename="README.md",
    )


def sample_chunk(*, metadata: dict[object, object] | None = None) -> DocumentChunk:
    return DocumentChunk(
        id=CHUNK_ID,
        document_id=DOCUMENT_ID,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        chunk_index=0,
        content="AI Agent Lab overview",
        token_count=6,
        char_count=21,
        heading="Overview",
        page_number=None,
        metadata_json=(
            {
                "source_format": "md",
                "start_char": 0,
                "end_char": 21,
            }
            if metadata is None
            else metadata
        ),
    )


def test_payload_builder_preserves_plan4_source_fields() -> None:
    payload = build_qdrant_payload(
        document=sample_document(),
        chunk=sample_chunk(),
        embedding_provider="openai_compatible",
        embedding_model="text-embedding-3-small",
    )

    assert payload.to_qdrant_payload() == {
        "knowledge_base_id": "00000000-0000-0000-0000-000000000001",
        "document_id": "00000000-0000-0000-0000-000000000002",
        "chunk_id": "00000000-0000-0000-0000-000000000003",
        "embedding_provider": "openai_compatible",
        "embedding_model": "text-embedding-3-small",
        "filename": "README.md",
        "chunk_index": 0,
        "content": "AI Agent Lab overview",
        "heading": "Overview",
        "page_number": None,
        "metadata": {
            "source_format": "md",
            "start_char": 0,
            "end_char": 21,
        },
    }


def test_payload_builder_copies_metadata_and_serialized_output() -> None:
    metadata: dict[object, object] = {
        "source_format": "pdf",
        "nested": {"page_label": "1"},
    }
    payload = build_qdrant_payload(
        document=sample_document(),
        chunk=sample_chunk(metadata=metadata),
        embedding_provider="openai_compatible",
        embedding_model="text-embedding-3-small",
    )
    metadata["source_format"] = "changed"
    serialized = payload.to_qdrant_payload()
    serialized["metadata"]["source_format"] = "mutated"  # type: ignore[index]

    assert payload.to_qdrant_payload()["metadata"] == {
        "source_format": "pdf",
        "nested": {"page_label": "1"},
    }


@pytest.mark.parametrize(
    ("document_id", "knowledge_base_id"),
    [
        (UUID("00000000-0000-0000-0000-000000000099"), KNOWLEDGE_BASE_ID),
        (DOCUMENT_ID, UUID("00000000-0000-0000-0000-000000000099")),
    ],
)
def test_payload_builder_rejects_ownership_mismatch(
    document_id: UUID,
    knowledge_base_id: UUID,
) -> None:
    chunk = sample_chunk()
    chunk.document_id = document_id
    chunk.knowledge_base_id = knowledge_base_id

    with pytest.raises(
        VectorStoreInputError,
        match="Document and chunk ownership must match",
    ):
        build_qdrant_payload(
            document=sample_document(),
            chunk=chunk,
            embedding_provider="openai_compatible",
            embedding_model="text-embedding-3-small",
        )


@pytest.mark.parametrize(
    "metadata",
    [
        {1: "not-a-string-key"},
        {"score": nan},
        {"object": object()},
    ],
)
def test_payload_builder_rejects_non_json_metadata(
    metadata: dict[object, object],
) -> None:
    with pytest.raises(
        VectorStoreInputError,
        match="Chunk metadata must be a JSON-safe object",
    ):
        build_qdrant_payload(
            document=sample_document(),
            chunk=sample_chunk(metadata=metadata),
            embedding_provider="openai_compatible",
            embedding_model="text-embedding-3-small",
        )


def test_payload_builder_normalizes_json_arrays() -> None:
    payload = build_qdrant_payload(
        document=sample_document(),
        chunk=sample_chunk(metadata={"line_range": (1, 4)}),
        embedding_provider="openai_compatible",
        embedding_model="text-embedding-3-small",
    )

    assert payload.to_qdrant_payload()["metadata"] == {
        "line_range": [1, 4]
    }
