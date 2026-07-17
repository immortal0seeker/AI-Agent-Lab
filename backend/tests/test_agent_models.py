from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import AgentRun, Conversation, Message, ToolCall


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'agent-models.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_run(
    session: Session,
    *,
    conversation: Conversation | None = None,
) -> tuple[Conversation, Message, AgentRun]:
    conversation = conversation or Conversation()
    message = Message(conversation=conversation, role="user", content="Use a tool")
    run = AgentRun(
        conversation=conversation,
        user_message=message,
        goal="Answer with one safe tool call",
    )
    session.add(conversation)
    session.flush()
    return conversation, message, run


def create_tool_call(
    run: AgentRun,
    *,
    tool_call_id: str = "call-1",
    conversation_id: UUID | None = None,
) -> ToolCall:
    return ToolCall(
        agent_run=run,
        conversation_id=conversation_id or run.conversation_id,
        tool_call_id=tool_call_id,
        tool_name="echo",
        arguments_json={"message": "hello"},
        result_json={"success": True, "content": "hello"},
    )


def test_agent_models_persist_relationships_json_and_defaults(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, message, run = create_run(session)
    tool_call = create_tool_call(run)
    session.add(tool_call)
    session.commit()
    session.expire_all()

    loaded = session.scalar(select(AgentRun).where(AgentRun.id == run.id))

    assert loaded is not None
    assert isinstance(loaded.id, UUID)
    assert loaded.conversation_id == conversation.id
    assert loaded.user_message_id == message.id
    assert loaded.status == "created"
    assert loaded.created_at.tzinfo is None
    assert loaded.tool_calls[0].status == "pending"
    assert loaded.tool_calls[0].tool_call_id == "call-1"
    assert loaded.tool_calls[0].arguments_json == {"message": "hello"}
    assert loaded.tool_calls[0].result_json == {
        "success": True,
        "content": "hello",
    }


def test_tool_call_argument_defaults_are_isolated(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, _, run = create_run(session)
    first = ToolCall(
        agent_run=run,
        conversation_id=conversation.id,
        tool_call_id="call-1",
        tool_name="echo",
    )
    second = ToolCall(
        agent_run=run,
        conversation_id=conversation.id,
        tool_call_id="call-2",
        tool_name="echo",
    )
    session.add_all([first, second])
    session.commit()

    first.arguments_json["message"] = "first"

    assert second.arguments_json == {}
    assert first.arguments_json is not second.arguments_json


def test_deleting_conversation_cascades_agent_audit_rows(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, _, run = create_run(session)
    session.add(create_tool_call(run))
    session.commit()

    session.delete(conversation)
    session.commit()

    assert session.scalars(select(AgentRun)).all() == []
    assert session.scalars(select(ToolCall)).all() == []


def test_deleting_agent_run_cascades_tool_calls(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, _, run = create_run(session)
    session.add(create_tool_call(run))
    session.commit()

    session.delete(run)
    session.commit()

    assert session.scalars(select(ToolCall)).all() == []


def test_deleting_user_message_preserves_agent_audit_rows(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, message, run = create_run(session)
    tool_call = create_tool_call(run)
    session.add(tool_call)
    session.commit()
    run_id = run.id
    tool_call_id = tool_call.id

    session.delete(message)
    session.commit()

    preserved_run = session.get(AgentRun, run_id)
    assert preserved_run is not None
    assert preserved_run.user_message_id is None
    assert session.get(ToolCall, tool_call_id) is not None


def test_agent_run_rejects_invalid_status_and_negative_latency(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    session.add(
        AgentRun(
            conversation=conversation,
            goal="invalid status",
            status="unknown",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    conversation = Conversation()
    session.add(
        AgentRun(
            conversation=conversation,
            goal="invalid latency",
            latency_ms=-1,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_tool_call_rejects_invalid_status_and_negative_latency(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, _, run = create_run(session)
    invalid_status = create_tool_call(run)
    invalid_status.status = "unknown"
    session.add(invalid_status)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    conversation, _, run = create_run(session)
    invalid_latency = create_tool_call(run, tool_call_id="call-2")
    invalid_latency.latency_ms = -1
    session.add(invalid_latency)
    with pytest.raises(IntegrityError):
        session.commit()


def test_tool_call_id_is_unique_within_one_run(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, _, run = create_run(session)
    session.add_all([create_tool_call(run), create_tool_call(run)])

    with pytest.raises(IntegrityError):
        session.commit()


def test_tool_call_conversation_must_match_agent_run(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, _, run = create_run(session)
    other_conversation = Conversation()
    session.add(other_conversation)
    session.flush()
    mismatched = ToolCall(
        agent_run_id=run.id,
        conversation_id=other_conversation.id,
        tool_call_id="call-mismatch",
        tool_name="echo",
    )
    session.add(mismatched)

    with pytest.raises(IntegrityError):
        session.commit()
