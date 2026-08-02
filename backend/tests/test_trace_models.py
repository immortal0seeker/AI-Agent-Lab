from collections.abc import Iterator
from decimal import Decimal
import importlib
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import AgentRun, Conversation, Message


def load_trace_models() -> tuple[Any, Any]:
    try:
        module = importlib.import_module("app.models.trace")
    except ModuleNotFoundError:
        pytest.fail("Trace ORM models are not implemented", pytrace=False)
    return module.TraceRun, module.TraceStep


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine, Any, Any]]:
    trace_run, trace_step = load_trace_models()
    engine = create_db_engine(f"sqlite:///{tmp_path / 'trace-models.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine, trace_run, trace_step
    finally:
        session.close()
        engine.dispose()


def create_operational_records(
    session: Session,
) -> tuple[Conversation, Message, AgentRun]:
    conversation = Conversation(title="Trace ownership")
    message = Message(
        conversation=conversation,
        role="user",
        content="Use one safe tool",
    )
    agent_run = AgentRun(
        conversation=conversation,
        user_message=message,
        goal="Use one safe tool",
    )
    session.add(conversation)
    session.flush()
    return conversation, message, agent_run


def create_trace_run(
    session: Session,
    trace_run: Any,
    *,
    conversation: Conversation | None = None,
    message: Message | None = None,
    agent_run: AgentRun | None = None,
) -> Any:
    run = trace_run(
        run_type="agent",
        conversation_id=conversation.id if conversation is not None else None,
        user_message_id=message.id if message is not None else None,
        agent_run_id=agent_run.id if agent_run is not None else None,
        input_text="Use one safe tool",
    )
    session.add(run)
    return run


def test_trace_models_are_exported() -> None:
    trace_run, trace_step = load_trace_models()
    models = importlib.import_module("app.models")

    assert models.TraceRun is trace_run
    assert models.TraceStep is trace_step


def test_trace_models_persist_relationships_order_and_defaults(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, trace_step = db
    conversation, message, agent_run = create_operational_records(session)
    run = create_trace_run(
        session,
        trace_run,
        conversation=conversation,
        message=message,
        agent_run=agent_run,
    )
    run.steps.extend(
        [
            trace_step(
                step_index=2,
                step_type="llm_call",
                name="Call model",
            ),
            trace_step(
                step_index=1,
                step_type="build_context",
                name="Build context",
            ),
        ]
    )
    session.commit()
    run_id = run.id
    session.expire_all()

    loaded = session.scalar(select(trace_run).where(trace_run.id == run_id))

    assert loaded is not None
    assert isinstance(loaded.id, UUID)
    assert loaded.status == "pending"
    assert loaded.created_at.tzinfo is None
    assert loaded.conversation.id == conversation.id
    assert loaded.user_message.id == message.id
    assert loaded.agent_run.id == agent_run.id
    assert [step.step_index for step in loaded.steps] == [1, 2]
    assert [step.status for step in loaded.steps] == ["pending", "pending"]
    assert loaded.metadata_json == {}
    assert loaded.steps[0].input_json == {}


def test_trace_json_defaults_are_isolated(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, trace_step = db
    first_run = trace_run(run_type="chat", input_text="first")
    second_run = trace_run(run_type="chat", input_text="second")
    first_step = trace_step(
        trace_run=first_run,
        step_index=1,
        step_type="build_context",
        name="Build first context",
    )
    second_step = trace_step(
        trace_run=second_run,
        step_index=1,
        step_type="build_context",
        name="Build second context",
    )
    session.add_all([first_run, second_run])
    session.flush()

    first_run.metadata_json["source"] = "first"
    first_step.input_json["query"] = "first"

    assert second_run.metadata_json == {}
    assert second_step.input_json == {}
    assert first_run.metadata_json is not second_run.metadata_json
    assert first_step.input_json is not second_step.input_json


def test_deleting_trace_run_cascades_steps(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, trace_step = db
    run = trace_run(run_type="chat", input_text="hello")
    step = trace_step(
        trace_run=run,
        step_index=1,
        step_type="llm_call",
        name="Call model",
    )
    session.add(run)
    session.commit()
    step_id = step.id

    session.delete(run)
    session.commit()

    assert session.get(trace_step, step_id) is None


def test_deleting_message_preserves_trace_and_conversation_link(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, _ = db
    conversation, message, agent_run = create_operational_records(session)
    run = create_trace_run(
        session,
        trace_run,
        conversation=conversation,
        message=message,
        agent_run=agent_run,
    )
    session.commit()
    run_id = run.id
    conversation_id = conversation.id

    session.delete(message)
    session.commit()
    session.expire_all()

    preserved = session.get(trace_run, run_id)
    assert preserved is not None
    assert preserved.conversation_id == conversation_id
    assert preserved.user_message_id is None


def test_deleting_agent_run_preserves_trace_and_conversation_link(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, _ = db
    conversation, message, agent_run = create_operational_records(session)
    run = create_trace_run(
        session,
        trace_run,
        conversation=conversation,
        message=message,
        agent_run=agent_run,
    )
    session.commit()
    run_id = run.id
    conversation_id = conversation.id

    session.delete(agent_run)
    session.commit()
    session.expire_all()

    preserved = session.get(trace_run, run_id)
    assert preserved is not None
    assert preserved.conversation_id == conversation_id
    assert preserved.agent_run_id is None


def test_deleting_conversation_preserves_trace_and_steps(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, trace_step = db
    conversation, message, agent_run = create_operational_records(session)
    run = create_trace_run(
        session,
        trace_run,
        conversation=conversation,
        message=message,
        agent_run=agent_run,
    )
    step = trace_step(
        trace_run=run,
        step_index=1,
        step_type="tool_call",
        name="Call tool",
    )
    session.add(step)
    session.commit()
    run_id = run.id
    step_id = step.id

    session.delete(conversation)
    session.commit()
    session.expire_all()

    preserved = session.get(trace_run, run_id)
    assert preserved is not None
    assert preserved.conversation_id is None
    assert preserved.user_message_id is None
    assert preserved.agent_run_id is None
    assert session.get(trace_step, step_id) is not None


@pytest.mark.parametrize("correlation", ["user_message", "agent_run"])
def test_trace_correlation_must_match_conversation(
    db: tuple[Session, Engine, Any, Any],
    correlation: str,
) -> None:
    session, _, trace_run, _ = db
    first, _, _ = create_operational_records(session)
    _, second_message, second_agent_run = create_operational_records(session)
    run = trace_run(
        run_type="agent",
        conversation_id=first.id,
        input_text="invalid ownership",
        user_message_id=(second_message.id if correlation == "user_message" else None),
        agent_run_id=(second_agent_run.id if correlation == "agent_run" else None),
    )
    session.add(run)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("correlation", ["user_message_id", "agent_run_id"])
def test_trace_owned_correlation_requires_conversation_in_orm(
    db: tuple[Session, Engine, Any, Any],
    correlation: str,
) -> None:
    session, _, trace_run, _ = db
    _, message, agent_run = create_operational_records(session)
    run = trace_run(
        run_type="agent",
        input_text="missing conversation",
        **{
            correlation: (
                message.id if correlation == "user_message_id" else agent_run.id
            )
        },
    )
    session.add(run)

    with pytest.raises(ValueError, match="conversation_id"):
        session.commit()


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("run_type", "unknown"),
        ("status", "unknown"),
        ("input_text", "   "),
        ("total_input_tokens", -1),
        ("total_output_tokens", -1),
        ("total_tokens", -1),
        ("estimated_cost", Decimal("-0.00000001")),
        ("latency_ms", -1),
    ],
)
def test_trace_run_rejects_invalid_persisted_values(
    db: tuple[Session, Engine, Any, Any],
    field: str,
    invalid: object,
) -> None:
    session, _, trace_run, _ = db
    values: dict[str, object] = {
        "run_type": "chat",
        "input_text": "invalid persisted value",
    }
    values[field] = invalid
    session.add(trace_run(**values))

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("step_index", 0),
        ("step_type", "unknown"),
        ("status", "unknown"),
        ("name", "   "),
        ("latency_ms", -1),
    ],
)
def test_trace_step_rejects_invalid_persisted_values(
    db: tuple[Session, Engine, Any, Any],
    field: str,
    invalid: object,
) -> None:
    session, _, trace_run, trace_step = db
    run = trace_run(run_type="chat", input_text="invalid step")
    values: dict[str, object] = {
        "trace_run": run,
        "step_index": 1,
        "step_type": "llm_call",
        "name": "Call model",
    }
    values[field] = invalid
    session.add(trace_step(**values))

    with pytest.raises(IntegrityError):
        session.commit()


def test_trace_step_index_is_unique_within_run(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, trace_run, trace_step = db
    run = trace_run(run_type="chat", input_text="duplicate step position")
    run.steps.extend(
        [
            trace_step(
                step_index=1,
                step_type="build_context",
                name="First",
            ),
            trace_step(
                step_index=1,
                step_type="llm_call",
                name="Duplicate",
            ),
        ]
    )
    session.add(run)

    with pytest.raises(IntegrityError):
        session.commit()
