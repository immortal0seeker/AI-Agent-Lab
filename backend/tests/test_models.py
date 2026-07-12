from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine


def create_test_session(tmp_path: Path) -> tuple[Session, Engine]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'models.db'}")
    Base.metadata.create_all(engine)
    return Session(engine), engine


def test_models_create_and_load_relationships(tmp_path: Path) -> None:
    from app.models import Conversation, LLMCall, Message

    session, engine = create_test_session(tmp_path)
    conversation = Conversation()
    message = Message(conversation=conversation, role="user", content="Hello")
    llm_call = LLMCall(
        conversation=conversation,
        message=message,
        provider="test-provider",
        model="test-model",
    )
    session.add(conversation)
    session.commit()

    loaded = session.scalar(select(Conversation).where(Conversation.id == conversation.id))

    assert loaded is not None
    assert isinstance(loaded.id, UUID)
    assert loaded.title == "New conversation"
    assert loaded.messages == [message]
    assert loaded.llm_calls == [llm_call]
    assert llm_call.status == "pending"

    session.close()
    engine.dispose()


def test_deleting_conversation_cascades_to_children(tmp_path: Path) -> None:
    from app.models import Conversation, LLMCall, Message

    session, engine = create_test_session(tmp_path)
    conversation = Conversation()
    message = Message(conversation=conversation, role="user", content="Hello")
    llm_call = LLMCall(
        conversation=conversation,
        message=message,
        provider="test-provider",
        model="test-model",
    )
    session.add(conversation)
    session.commit()

    session.delete(conversation)
    session.commit()

    assert session.scalars(select(Message)).all() == []
    assert session.scalars(select(LLMCall)).all() == []

    session.close()
    engine.dispose()


def test_deleting_message_preserves_llm_call(tmp_path: Path) -> None:
    from app.models import Conversation, LLMCall, Message

    session, engine = create_test_session(tmp_path)
    conversation = Conversation()
    message = Message(conversation=conversation, role="assistant", content="Hi")
    llm_call = LLMCall(
        conversation=conversation,
        message=message,
        provider="test-provider",
        model="test-model",
    )
    session.add(conversation)
    session.commit()
    llm_call_id = llm_call.id

    session.delete(message)
    session.commit()

    preserved_call = session.get(LLMCall, llm_call_id)
    assert preserved_call is not None
    assert preserved_call.message_id is None

    session.close()
    engine.dispose()
