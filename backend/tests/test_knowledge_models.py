from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
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


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'knowledge-models.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_document(
    knowledge_base: KnowledgeBase,
    *,
    suffix: str = "a",
) -> Document:
    return Document(
        knowledge_base=knowledge_base,
        filename=f"{suffix}.md",
        original_filename=f"{suffix.upper()}.md",
        file_type="md",
        file_path=f"uploads/kb/{suffix}.md",
        file_size=128,
        file_hash=suffix * 64,
    )


def create_chunk(
    document: Document,
    knowledge_base_id: UUID,
    *,
    chunk_index: int = 0,
) -> DocumentChunk:
    return DocumentChunk(
        document=document,
        knowledge_base_id=knowledge_base_id,
        chunk_index=chunk_index,
        content="Synthetic chunk",
        token_count=3,
        char_count=15,
    )


def test_knowledge_models_persist_graph_defaults_and_json(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Project docs")
    document = create_document(knowledge_base)
    session.add_all([knowledge_base, conversation])
    session.flush()

    chunk = create_chunk(document, knowledge_base.id)
    chunk.metadata_json = {"section": "intro"}
    query = RagQuery(
        knowledge_base=knowledge_base,
        conversation=conversation,
        answer_message=answer,
        query="What is this?",
        top_k=7,
        retrieved_chunks_json=[{"chunk_id": "synthetic"}],
    )
    session.add_all([chunk, query])
    session.commit()
    session.expire_all()

    loaded = session.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base.id)
    )

    assert loaded is not None
    assert isinstance(loaded.id, UUID)
    assert loaded.vector_store == "qdrant"
    assert loaded.created_at.tzinfo is None
    assert loaded.documents[0].parse_status == "uploaded"
    assert loaded.documents[0].chunk_status == "pending"
    assert loaded.documents[0].embedding_status == "pending"
    assert loaded.documents[0].metadata_json == {}
    assert loaded.documents[0].chunks == [chunk]
    assert chunk.metadata_json == {"section": "intro"}
    assert loaded.rag_queries == [query]
    assert query.answer_message_id == answer.id
    assert query.top_k == 7
    assert query.retrieved_chunks_json == [{"chunk_id": "synthetic"}]


def test_json_defaults_are_isolated(db: tuple[Session, Engine]) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Defaults")
    first = create_document(knowledge_base, suffix="a")
    second = create_document(knowledge_base, suffix="b")
    first_query = RagQuery(
        knowledge_base=knowledge_base,
        query="First query",
    )
    second_query = RagQuery(
        knowledge_base=knowledge_base,
        query="Second query",
    )
    session.add(knowledge_base)
    session.flush()

    first.metadata_json["source"] = "first"
    first_query.retrieved_chunks_json.append({"chunk_id": "first"})

    assert second.metadata_json == {}
    assert first.metadata_json is not second.metadata_json
    assert second_query.retrieved_chunks_json == []
    assert (
        first_query.retrieved_chunks_json
        is not second_query.retrieved_chunks_json
    )
    assert first_query.top_k == 5
    assert second_query.top_k == 5


@pytest.mark.parametrize("top_k", [0, 101])
def test_rag_query_rejects_top_k_outside_supported_range(
    db: tuple[Session, Engine],
    top_k: int,
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Invalid query Top-K")
    session.add(
        RagQuery(
            knowledge_base=knowledge_base,
            query="Question",
            top_k=top_k,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_knowledge_base_with_document_is_restricted(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Delete me")
    document = create_document(knowledge_base)
    session.add(knowledge_base)
    session.flush()
    document.chunks.append(create_chunk(document, knowledge_base.id))
    session.commit()

    with pytest.raises(IntegrityError):
        session.execute(
            delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base.id)
        )
        session.commit()
    session.rollback()

    assert session.get(KnowledgeBase, knowledge_base.id) is not None
    assert session.get(Document, document.id) is not None
    assert session.scalars(select(DocumentChunk)).all() != []


def test_document_hash_is_unique_within_knowledge_base(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Duplicate documents")
    session.add_all(
        [
            create_document(knowledge_base, suffix="a"),
            create_document(knowledge_base, suffix="a"),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_document_hash_may_repeat_across_knowledge_bases(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    first = KnowledgeBase(name="First documents")
    second = KnowledgeBase(name="Second documents")
    session.add_all(
        [
            create_document(first, suffix="a"),
            create_document(second, suffix="a"),
        ]
    )

    session.commit()

    assert len(session.scalars(select(Document)).all()) == 2


def test_knowledge_base_rejects_blank_name(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    session.add(KnowledgeBase(name="   "))

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("parse_status", "unknown"),
        ("chunk_status", "unknown"),
        ("embedding_status", "unknown"),
        ("file_size", -1),
        ("file_hash", "short"),
        ("file_type", "docx"),
    ],
)
def test_document_rejects_invalid_lifecycle_data(
    db: tuple[Session, Engine],
    field_name: str,
    invalid_value: object,
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Invalid document")
    document = create_document(knowledge_base)
    setattr(document, field_name, invalid_value)
    session.add(knowledge_base)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("chunk_index", -1),
        ("token_count", -1),
        ("char_count", -1),
        ("page_number", 0),
    ],
)
def test_chunk_rejects_invalid_numeric_data(
    db: tuple[Session, Engine],
    field_name: str,
    invalid_value: int,
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Invalid chunk")
    document = create_document(knowledge_base)
    session.add(knowledge_base)
    session.flush()
    chunk = create_chunk(document, knowledge_base.id)
    setattr(chunk, field_name, invalid_value)
    session.add(chunk)

    with pytest.raises(IntegrityError):
        session.commit()


def test_chunk_index_is_unique_within_document(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Duplicate chunks")
    document = create_document(knowledge_base)
    session.add(knowledge_base)
    session.flush()
    session.add_all(
        [
            create_chunk(document, knowledge_base.id),
            create_chunk(document, knowledge_base.id),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_chunk_rejects_cross_knowledge_base(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    first = KnowledgeBase(name="First")
    second = KnowledgeBase(name="Second")
    document = create_document(first)
    session.add_all([first, second])
    session.flush()
    session.add(
        DocumentChunk(
            document_id=document.id,
            knowledge_base_id=second.id,
            chunk_index=0,
            content="Wrong owner",
            token_count=2,
            char_count=11,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_rag_query_answer_requires_conversation(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Queries")
    session.add_all([conversation, knowledge_base])
    session.flush()
    session.add(
        RagQuery(
            knowledge_base_id=knowledge_base.id,
            answer_message_id=answer.id,
            query="Missing conversation",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_rag_query_answer_message_must_match_conversation(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    first = Conversation()
    second = Conversation()
    answer = Message(
        conversation=second,
        role="assistant",
        content="Other conversation",
    )
    knowledge_base = KnowledgeBase(name="Queries")
    session.add_all([first, second, knowledge_base])
    session.flush()
    session.add(
        RagQuery(
            knowledge_base_id=knowledge_base.id,
            conversation_id=first.id,
            answer_message_id=answer.id,
            query="Mismatch",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_answer_message_preserves_rag_query(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Queries")
    query = RagQuery(
        knowledge_base=knowledge_base,
        conversation=conversation,
        answer_message=answer,
        query="Preserve query",
    )
    session.add_all([conversation, knowledge_base])
    session.commit()
    query_id = query.id

    session.delete(answer)
    session.commit()

    preserved = session.get(RagQuery, query_id)
    assert preserved is not None
    assert preserved.answer_message_id is None


def test_raw_deleting_answer_message_preserves_rag_query(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Raw delete queries")
    query = RagQuery(
        knowledge_base=knowledge_base,
        conversation=conversation,
        answer_message=answer,
        query="Preserve raw query",
    )
    session.add_all([conversation, knowledge_base])
    session.commit()
    conversation_id = conversation.id
    answer_id = answer.id
    query_id = query.id
    session.expunge_all()

    session.execute(delete(Message).where(Message.id == answer_id))
    session.commit()
    session.expire_all()

    preserved = session.get(RagQuery, query_id)
    assert preserved is not None
    assert preserved.conversation_id == conversation_id
    assert preserved.answer_message_id is None


def test_deleting_conversation_cascades_rag_query(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Queries")
    query = RagQuery(
        knowledge_base=knowledge_base,
        conversation=conversation,
        answer_message=answer,
        query="Delete with conversation",
    )
    session.add_all([conversation, knowledge_base])
    session.commit()
    conversation_id = conversation.id
    knowledge_base_id = knowledge_base.id
    query_id = query.id
    session.expunge_all()

    stored_conversation = session.get(Conversation, conversation_id)
    assert stored_conversation is not None
    session.delete(stored_conversation)
    session.commit()

    assert session.get(RagQuery, query_id) is None
    assert session.get(KnowledgeBase, knowledge_base_id) is not None
