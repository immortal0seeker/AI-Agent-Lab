import asyncio
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.agents import AgentRunNotFoundError, SimpleAgentRequest
from app.db.base import Base
from app.db.session import create_db_engine
from app.models import AgentRun, Conversation, ToolCall
from app.schemas.agent import AgentRunCreate
from app.services.agent_service import AgentService


@pytest.fixture
def agent_session(tmp_path: Path) -> Iterator[Session]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'agent-service.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


def create_agent_run(session: Session) -> AgentRun:
    conversation = Conversation(title="Agent service test")
    run = AgentRun(
        conversation=conversation,
        status="completed",
        goal="Inspect the workspace",
        final_answer="Done",
    )
    session.add(run)
    session.flush()
    return run


def test_agent_service_gets_existing_run(agent_session: Session) -> None:
    run = create_agent_run(agent_session)

    loaded = AgentService(agent_session).get_agent_run(run.id)

    assert loaded is run


def test_agent_service_rejects_unknown_run(agent_session: Session) -> None:
    missing_id = uuid4()

    with pytest.raises(AgentRunNotFoundError) as exc_info:
        AgentService(agent_session).get_agent_run(missing_id)

    assert exc_info.value.run_id == missing_id


def test_agent_service_lists_tool_calls_deterministically(
    agent_session: Session,
) -> None:
    run = create_agent_run(agent_session)
    created_at = datetime(2026, 7, 19, 12, 0, 0)
    later_id = UUID(int=2)
    earlier_id = UUID(int=1)
    agent_session.add_all(
        [
            ToolCall(
                id=later_id,
                tool_call_id="call-later",
                agent_run_id=run.id,
                conversation_id=run.conversation_id,
                tool_name="list_dir",
                arguments_json={"path": "."},
                status="success",
                created_at=created_at,
            ),
            ToolCall(
                id=earlier_id,
                tool_call_id="call-earlier",
                agent_run_id=run.id,
                conversation_id=run.conversation_id,
                tool_name="read_file",
                arguments_json={"path": "README.md"},
                status="success",
                created_at=created_at,
            ),
        ]
    )
    agent_session.flush()

    rows = AgentService(agent_session).list_tool_calls(run.id)

    assert [row.id for row in rows] == [earlier_id, later_id]


def test_agent_service_lists_empty_calls_for_existing_run(
    agent_session: Session,
) -> None:
    run = create_agent_run(agent_session)

    assert AgentService(agent_session).list_tool_calls(run.id) == []


def test_agent_service_rejects_unknown_run_when_listing_calls(
    agent_session: Session,
) -> None:
    missing_id = uuid4()

    with pytest.raises(AgentRunNotFoundError):
        AgentService(agent_session).list_tool_calls(missing_id)


def test_agent_service_converts_api_input_for_simple_agent(
    agent_session: Session,
) -> None:
    expected_result = object()

    class RecordingRunner:
        request: SimpleAgentRequest | None = None

        async def run(self, request: SimpleAgentRequest) -> Any:
            self.request = request
            return expected_result

    runner = RecordingRunner()
    data = AgentRunCreate(
        provider="mock",
        model="tools-model",
        input="Inspect the workspace",
        temperature=0.2,
        max_tokens=256,
        max_steps=4,
    )

    result = asyncio.run(
        AgentService(agent_session).run(data, runner=runner)
    )

    assert result is expected_result
    assert runner.request == SimpleAgentRequest(
        provider="mock",
        model="tools-model",
        content="Inspect the workspace",
        temperature=0.2,
        max_tokens=256,
        max_steps=4,
    )
