from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import Conversation, LLMCall, Message


def test_conversation_create_defaults() -> None:
    from app.schemas import ConversationCreate

    schema = ConversationCreate()

    assert schema.title == "New conversation"
    assert schema.default_provider is None
    assert schema.default_model is None


def test_message_create_rejects_invalid_conversation_id() -> None:
    from app.schemas import MessageCreate

    with pytest.raises(ValidationError):
        MessageCreate(
            conversation_id="not-a-uuid",
            role="user",
            content="Hello",
        )


def test_llm_call_create_requires_provider_and_model() -> None:
    from app.schemas import LLMCallCreate

    with pytest.raises(ValidationError):
        LLMCallCreate(conversation_id=UUID(int=1))


def test_schema_string_limits_match_database_columns() -> None:
    from app.schemas import ConversationCreate, LLMCallCreate, MessageCreate

    with pytest.raises(ValidationError):
        ConversationCreate(title="x" * 256)

    with pytest.raises(ValidationError):
        MessageCreate(
            conversation_id=UUID(int=1),
            role="x" * 33,
            content="Hello",
        )

    with pytest.raises(ValidationError):
        LLMCallCreate(
            conversation_id=UUID(int=1),
            provider="x" * 101,
            model="test-model",
        )


def test_read_schemas_validate_orm_instances(tmp_path: Path) -> None:
    from app.schemas import ConversationRead, LLMCallRead, MessageRead

    engine = create_db_engine(f"sqlite:///{tmp_path / 'schemas.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)

    conversation = Conversation()
    message = Message(conversation=conversation, role="user", content="Hello")
    llm_call = LLMCall(
        conversation=conversation,
        message=message,
        provider="test-provider",
        model="test-model",
    )
    session.add(conversation)
    session.flush()

    conversation_schema = ConversationRead.model_validate(conversation)
    message_schema = MessageRead.model_validate(message)
    llm_call_schema = LLMCallRead.model_validate(llm_call)

    assert conversation_schema.id == conversation.id
    assert message_schema.conversation_id == conversation.id
    assert llm_call_schema.message_id == message.id
    assert llm_call_schema.status == "pending"

    session.rollback()
    session.close()
    engine.dispose()
