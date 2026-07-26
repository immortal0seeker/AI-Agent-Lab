from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import (
    Conversation,
    Document,
    DocumentChunk,
    KnowledgeBase,
    Message,
    RagQuery,
)
from app.schemas import (
    DocumentChunkCreate,
    DocumentChunkRead,
    DocumentCreate,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
    RagQueryCreate,
    RagQueryRead,
)


def document_payload() -> dict[str, object]:
    return {
        "knowledge_base_id": UUID(int=1),
        "filename": "guide.md",
        "original_filename": "Guide.md",
        "file_type": "md",
        "file_path": "uploads/kb/guide.md",
        "file_size": 128,
        "file_hash": "a" * 64,
    }


def chunk_payload() -> dict[str, object]:
    return {
        "document_id": UUID(int=2),
        "knowledge_base_id": UUID(int=1),
        "chunk_index": 0,
        "content": "Synthetic chunk",
        "token_count": 3,
        "char_count": 15,
    }


def test_knowledge_base_create_defaults() -> None:
    schema = KnowledgeBaseCreate(name="  Project docs  ")

    assert schema.name == "Project docs"
    assert schema.description is None
    assert schema.embedding_provider is None
    assert schema.embedding_model is None
    assert schema.vector_store == "qdrant"
    assert schema.vector_collection_name is None


def test_knowledge_base_update_tracks_only_supplied_fields() -> None:
    update = KnowledgeBaseUpdate(
        name="  Updated knowledge  ",
        description=None,
    )

    assert update.name == "Updated knowledge"
    assert update.description is None
    assert update.model_dump(exclude_unset=True) == {
        "name": "Updated knowledge",
        "description": None,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"name": "   "},
        {"vector_store": None},
        {"unknown": "value"},
    ],
)
def test_knowledge_base_update_rejects_invalid_payload(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        KnowledgeBaseUpdate.model_validate(payload)


def test_document_create_defaults_and_metadata() -> None:
    schema = DocumentCreate(
        **document_payload(),
        metadata={"source": "synthetic"},
    )

    assert schema.parse_status == "uploaded"
    assert schema.chunk_status == "pending"
    assert schema.embedding_status == "pending"
    assert schema.error_message is None
    assert schema.metadata == {"source": "synthetic"}


def test_mutable_schema_defaults_are_isolated() -> None:
    first_document = DocumentCreate(**document_payload())
    second_document = DocumentCreate(**document_payload())
    first_query = RagQueryCreate(
        knowledge_base_id=UUID(int=1),
        query="First query",
    )
    second_query = RagQueryCreate(
        knowledge_base_id=UUID(int=1),
        query="Second query",
    )

    first_document.metadata["source"] = "first"
    first_query.retrieved_chunks_json.append({"chunk_id": "first"})

    assert second_document.metadata == {}
    assert first_document.metadata is not second_document.metadata
    assert second_query.retrieved_chunks_json == []
    assert (
        first_query.retrieved_chunks_json
        is not second_query.retrieved_chunks_json
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "Project docs", "unexpected": "value"},
        {"name": "x" * 256},
        {"name": "Project docs", "vector_store": "x" * 101},
    ],
)
def test_knowledge_base_create_rejects_invalid_input(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        KnowledgeBaseCreate(**payload)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("filename", "x" * 256),
        ("original_filename", "x" * 256),
        ("file_type", "docx"),
        ("file_path", ""),
        ("file_size", -1),
        ("file_hash", "short"),
        ("file_hash", "g" * 64),
        ("parse_status", "unknown"),
        ("chunk_status", "unknown"),
        ("embedding_status", "unknown"),
    ],
)
def test_document_create_rejects_invalid_input(
    field_name: str,
    invalid_value: object,
) -> None:
    payload = document_payload()
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError):
        DocumentCreate(**payload)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("chunk_index", -1),
        ("content", "   "),
        ("token_count", -1),
        ("char_count", -1),
        ("heading", "x" * 513),
        ("page_number", 0),
        ("vector_id", "x" * 256),
    ],
)
def test_document_chunk_create_rejects_invalid_input(
    field_name: str,
    invalid_value: object,
) -> None:
    payload = chunk_payload()
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError):
        DocumentChunkCreate(**payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "knowledge_base_id": UUID(int=1),
            "query": "   ",
        },
        {
            "knowledge_base_id": UUID(int=1),
            "query": "Question",
            "latency_ms": -1,
        },
        {
            "knowledge_base_id": UUID(int=1),
            "query": "Question",
            "answer_message_id": UUID(int=2),
        },
        {
            "knowledge_base_id": UUID(int=1),
            "query": "Question",
            "unexpected": "value",
        },
    ],
)
def test_rag_query_create_rejects_invalid_input(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        RagQueryCreate(**payload)


def test_read_schemas_validate_orm_instances(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'knowledge-schemas.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Project docs")
    document = Document(
        knowledge_base=knowledge_base,
        filename="guide.md",
        original_filename="Guide.md",
        file_type="md",
        file_path="uploads/kb/guide.md",
        file_size=128,
        file_hash="a" * 64,
        metadata_json={"source": "synthetic"},
    )
    session.add_all([knowledge_base, conversation])
    session.flush()
    chunk = DocumentChunk(
        document=document,
        knowledge_base_id=knowledge_base.id,
        chunk_index=0,
        content="Synthetic chunk",
        token_count=3,
        char_count=15,
        metadata_json={"section": "intro"},
    )
    query = RagQuery(
        knowledge_base=knowledge_base,
        conversation=conversation,
        answer_message=answer,
        query="What is this?",
        retrieved_chunks_json=[{"chunk_id": "synthetic"}],
        latency_ms=12,
    )
    session.add_all([chunk, query])
    session.flush()

    knowledge_base_schema = KnowledgeBaseRead.model_validate(knowledge_base)
    document_schema = DocumentRead.model_validate(document)
    chunk_schema = DocumentChunkRead.model_validate(chunk)
    query_schema = RagQueryRead.model_validate(query)

    assert knowledge_base_schema.id == knowledge_base.id
    assert document_schema.knowledge_base_id == knowledge_base.id
    assert document_schema.metadata == {"source": "synthetic"}
    assert "metadata_json" not in document_schema.model_dump()
    assert chunk_schema.document_id == document.id
    assert chunk_schema.metadata == {"section": "intro"}
    assert query_schema.answer_message_id == answer.id
    assert query_schema.retrieved_chunks_json == [{"chunk_id": "synthetic"}]

    session.rollback()
    session.close()
    engine.dispose()
