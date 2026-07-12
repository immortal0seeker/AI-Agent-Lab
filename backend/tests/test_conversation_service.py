from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService
from app.services.errors import ConversationNotFoundError


def create_test_session(tmp_path: Path) -> tuple[Session, Engine]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'conversations.db'}")
    Base.metadata.create_all(engine)
    return Session(engine), engine


def test_service_creates_and_gets_conversation(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)

    conversation = service.create_conversation(
        ConversationCreate(
            title="Test conversation",
            default_provider="provider-a",
            default_model="model-a",
        )
    )
    loaded = service.get_conversation(conversation.id)

    assert loaded is conversation
    assert loaded.title == "Test conversation"
    assert loaded.default_provider == "provider-a"
    assert loaded.default_model == "model-a"

    session.close()
    engine.dispose()


def test_service_appends_and_lists_messages_in_time_order(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    conversation = service.create_conversation(ConversationCreate())

    later = service.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="assistant",
            content="Second",
        )
    )
    earlier = service.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="user",
            content="First",
        )
    )
    earlier.created_at = datetime(2026, 1, 1)
    later.created_at = earlier.created_at + timedelta(seconds=1)
    session.flush()

    messages = service.list_messages(conversation.id)

    assert messages == [earlier, later]

    session.close()
    engine.dispose()


def test_service_rejects_unknown_conversation_lookup(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    missing_id = uuid4()

    with pytest.raises(
        ConversationNotFoundError,
        match=f"Conversation not found: {missing_id}",
    ):
        service.get_conversation(missing_id)

    session.close()
    engine.dispose()


def test_service_rejects_message_for_unknown_conversation(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    missing_id = uuid4()

    with pytest.raises(ConversationNotFoundError):
        service.append_message(
            MessageCreate(
                conversation_id=missing_id,
                role="user",
                content="Hello",
            )
        )

    session.close()
    engine.dispose()
