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


def test_service_keeps_message_order_when_clock_values_are_equal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    monkeypatch.setattr(
        "app.services.conversation_service.utc_now",
        lambda: fixed_time,
    )
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    conversation = service.create_conversation(ConversationCreate())

    first = service.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="user",
            content="First",
        )
    )
    second = service.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="assistant",
            content="Second",
        )
    )

    assert second.created_at == first.created_at + timedelta(microseconds=1)
    assert service.list_messages(conversation.id) == [first, second]

    session.close()
    engine.dispose()


def test_service_lists_conversations_by_recent_activity(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    older = service.create_conversation(ConversationCreate(title="Older"))
    tied_a = service.create_conversation(ConversationCreate(title="Tied A"))
    tied_b = service.create_conversation(ConversationCreate(title="Tied B"))
    older.updated_at = datetime(2026, 1, 1, 12, 0, 0)
    tied_at = datetime(2026, 1, 2, 12, 0, 0)
    tied_a.updated_at = tied_at
    tied_b.updated_at = tied_at
    session.flush()

    conversations = service.list_conversations()

    expected_tied = sorted([tied_a, tied_b], key=lambda item: item.id)
    assert conversations == [*expected_tied, older]

    session.close()
    engine.dispose()


def test_service_records_successful_turn_metadata(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    conversation = service.create_conversation(ConversationCreate())
    previous_updated_at = conversation.updated_at

    service.record_successful_turn(
        conversation,
        provider="provider-b",
        model="model-b",
        title_source="  First   prompt with spacing  ",
    )

    assert conversation.title == "First prompt with spacing"
    assert conversation.default_provider == "provider-b"
    assert conversation.default_model == "model-b"
    assert conversation.updated_at > previous_updated_at

    session.close()
    engine.dispose()


def test_service_limits_generated_title_to_fifty_characters(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = ConversationService(session)
    conversation = service.create_conversation(ConversationCreate())
    normalized = "A long first prompt " + "x" * 80

    service.record_successful_turn(
        conversation,
        provider="provider-a",
        model="model-a",
        title_source=f"  A long   first prompt {('x' * 80)}  ",
    )

    assert conversation.title == normalized[:50]

    session.close()
    engine.dispose()
