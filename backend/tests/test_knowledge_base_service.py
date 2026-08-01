from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import Document, KnowledgeBase
from app.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services import (
    KnowledgeBaseNotEmptyError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseService,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(
        f"sqlite:///{tmp_path / 'knowledge-base-service.db'}"
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def test_service_creates_gets_and_lists_knowledge_bases(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    older = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Older")
    )
    tied_a = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Tied A")
    )
    tied_b = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Tied B")
    )
    older.created_at = datetime(2026, 7, 24)
    tied_at = datetime(2026, 7, 25)
    tied_a.created_at = tied_at
    tied_b.created_at = tied_at
    session.flush()

    assert service.get_knowledge_base(older.id) is older
    expected_tied = sorted([tied_a, tied_b], key=lambda item: item.id)
    assert service.list_knowledge_bases() == [*expected_tied, older]


def test_service_partially_updates_and_clears_nullable_fields(
    db: tuple[Session, Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    row = service.create_knowledge_base(
        KnowledgeBaseCreate(
            name="Original",
            description="Clear me",
            embedding_provider="mock",
            embedding_model="embed-v1",
        )
    )
    previous_updated_at = row.updated_at
    monkeypatch.setattr(
        "app.services.knowledge_base_service.utc_now",
        lambda: previous_updated_at,
    )

    updated = service.update_knowledge_base(
        row.id,
        KnowledgeBaseUpdate(name="Updated", description=None),
    )

    assert updated is row
    assert updated.name == "Updated"
    assert updated.description is None
    assert updated.embedding_provider == "mock"
    assert updated.embedding_model == "embed-v1"
    assert updated.updated_at > previous_updated_at


def test_service_deletes_knowledge_base(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    row = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Delete me")
    )
    knowledge_base_id = row.id

    service.delete_knowledge_base(knowledge_base_id)

    with pytest.raises(KnowledgeBaseNotFoundError):
        service.get_knowledge_base(knowledge_base_id)


def test_service_rejects_deleting_nonempty_knowledge_base(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    knowledge_base = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Keep documents")
    )
    document = Document(
        knowledge_base_id=knowledge_base.id,
        filename="synthetic.txt",
        original_filename="synthetic.txt",
        file_type="txt",
        file_path=f"{knowledge_base.id}/{uuid4()}.txt",
        file_size=9,
        file_hash="a" * 64,
    )
    session.add(document)
    session.flush()

    with pytest.raises(KnowledgeBaseNotEmptyError):
        service.delete_knowledge_base(knowledge_base.id)

    assert session.get(KnowledgeBase, knowledge_base.id) is not None
    assert session.get(Document, document.id) is not None


@pytest.mark.parametrize("operation", ["get", "update", "delete"])
def test_service_rejects_unknown_knowledge_base(
    db: tuple[Session, Engine],
    operation: str,
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    missing_id = uuid4()

    with pytest.raises(
        KnowledgeBaseNotFoundError,
        match=f"Knowledge base not found: {missing_id}",
    ):
        if operation == "get":
            service.get_knowledge_base(missing_id)
        elif operation == "update":
            service.update_knowledge_base(
                missing_id,
                KnowledgeBaseUpdate(name="Missing"),
            )
        else:
            service.delete_knowledge_base(missing_id)
