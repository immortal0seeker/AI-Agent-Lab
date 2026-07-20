import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.agents import (
    AgentModelNotFoundError,
    AgentModelToolsUnsupportedError,
    AgentProviderUnavailableError,
    AgentRunNotFoundError,
)
from app.api.dependencies import (
    get_db_session,
    get_llm_providers,
    get_model_registry,
    get_tool_registry,
)
from app.api.errors import error_spec_for_exception
from app.db.base import Base
from app.db.session import create_db_engine
from app.main import app
from app.models import AgentRun, Conversation, Message, ToolCall
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatRequest,
    LLMResponse,
    LLMToolCall,
    ProviderConfigurationError,
    ProviderTimeoutError,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.schemas.agent import (
    AgentRunCreate,
    AgentRunExecutionRead,
    AgentRunRead,
    ToolCallRead,
)
from app.tools import ToolRegistry, ToolResult
from app.tools.builtin import register_builtin_tools


class DirectAnswerProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            id="agent-api-response",
            model="resolved-tools-model",
            content="Agent API answer",
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise NotImplementedError


class ToolRoundProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return LLMResponse(
                id="agent-tool-request",
                model="resolved-tools-model",
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call-read-notes",
                        tool_name="read_file",
                        arguments={"path": "notes.txt"},
                    ),
                ),
            )
        return LLMResponse(
            id="agent-tool-answer",
            model="resolved-tools-model",
            content="The notes describe a temporary workspace.",
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise NotImplementedError


class BlockedReadProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return LLMResponse(
                id="agent-blocked-read-request",
                model="resolved-tools-model",
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call-blocked-envrc",
                        tool_name="read_file",
                        arguments={"path": ".envrc"},
                    ),
                ),
            )
        return LLMResponse(
            id="agent-blocked-read-answer",
            model="resolved-tools-model",
            content="The protected file was not read.",
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise NotImplementedError


class TimeoutAgentProvider(DirectAnswerProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        raise ProviderTimeoutError(
            "private-provider-timeout-diagnostic",
            status_code=504,
        )


class LastStepToolProvider(DirectAnswerProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            id="agent-last-step-tool",
            model="resolved-tools-model",
            tool_calls=(
                LLMToolCall(
                    tool_call_id="call-not-executed",
                    tool_name="read_file",
                    arguments={"path": "README.md"},
                ),
            ),
        )


@pytest.fixture
def agent_api_context(tmp_path: Path) -> Any:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'agent-api.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider = DirectAnswerProvider()
    providers: dict[str, BaseLLMProvider] = {"mock": provider}
    registry = ModelRegistry(
        [
            ModelInfo(
                provider="mock",
                model="tools-model",
                display_name="Tools Model",
                supports_tools=True,
            )
        ]
    )

    async def override_db_session() -> AsyncIterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_llm_providers] = lambda: providers
    app.dependency_overrides[get_model_registry] = lambda: registry

    with TestClient(app) as client:
        yield client, factory, provider, providers, registry

    app.dependency_overrides.clear()
    engine.dispose()


def test_agent_run_create_schema_uses_agent_defaults_and_trims_ids() -> None:
    request = AgentRunCreate(
        provider=" mock ",
        model=" tools-model ",
        input="Read the workspace",
    )

    assert request.provider == "mock"
    assert request.model == "tools-model"
    assert request.temperature == 0.7
    assert request.max_tokens is None
    assert request.max_steps == 3


@pytest.mark.parametrize("max_steps", [True, 1.5, 0, 11])
def test_agent_run_create_schema_rejects_invalid_max_steps(
    max_steps: object,
) -> None:
    with pytest.raises(ValidationError):
        AgentRunCreate(
            provider="mock",
            model="tools-model",
            input="Read the workspace",
            max_steps=max_steps,
        )


@pytest.mark.parametrize("max_steps", [1, 10])
def test_agent_run_create_schema_accepts_boundary_max_steps(
    max_steps: int,
) -> None:
    request = AgentRunCreate(
        provider="mock",
        model="tools-model",
        input="Read the workspace",
        max_steps=max_steps,
    )

    assert request.max_steps == max_steps


@pytest.mark.parametrize(
    "payload",
    [
        {
            "provider": "mock",
            "model": "tools-model",
            "input": "   ",
        },
        {
            "provider": "mock",
            "model": "tools-model",
            "input": "Read the workspace",
            "content": "must not be accepted as an alias",
        },
    ],
)
def test_agent_run_create_schema_rejects_blank_or_unknown_input(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AgentRunCreate.model_validate(payload)


def test_agent_read_schemas_use_public_error_and_tool_result_fields() -> None:
    now = datetime(2026, 7, 19, 12, 0, 0)
    run_id = uuid4()
    conversation_id = uuid4()
    user_message_id = uuid4()
    tool_call = ToolCallRead(
        id=uuid4(),
        tool_call_id="call-1",
        sequence_index=1,
        agent_run_id=run_id,
        conversation_id=conversation_id,
        tool_name="read_file",
        arguments={"path": "README.md"},
        result=ToolResult(
            tool_name="read_file",
            success=True,
            content="workspace content",
        ),
        status="success",
        error=None,
        started_at=now,
        ended_at=now,
        latency_ms=0,
        created_at=now,
    )
    run = AgentRunRead(
        id=run_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        status="completed",
        goal="Read the workspace",
        final_answer="Done",
        error=None,
        started_at=now,
        ended_at=now,
        latency_ms=0,
        created_at=now,
    )
    response = AgentRunExecutionRead(
        **run.model_dump(),
        tool_calls=[tool_call],
    )

    payload = response.model_dump(mode="json")
    assert payload["error"] is None
    assert payload["tool_calls"][0]["arguments"] == {
        "path": "README.md"
    }
    assert payload["tool_calls"][0]["sequence_index"] == 1
    assert payload["tool_calls"][0]["result"]["success"] is True
    assert "arguments_json" not in payload["tool_calls"][0]
    assert "result_json" not in payload["tool_calls"][0]
    assert "error_message" not in payload["tool_calls"][0]


def test_agent_dependency_creates_fresh_builtin_tool_registry() -> None:
    first = get_tool_registry()
    second = get_tool_registry()

    assert first is not second
    assert [tool.name for tool in first.list_tools()] == [
        "read_file",
        "list_dir",
    ]
    assert [tool.name for tool in second.list_tools()] == [
        "read_file",
        "list_dir",
    ]


@pytest.mark.parametrize(
    ("exception", "status_code", "code", "message"),
    [
        (
            AgentModelNotFoundError("private-provider", "private-model"),
            400,
            "model_not_found",
            "The requested model is not available",
        ),
        (
            AgentModelToolsUnsupportedError(
                "private-provider",
                "private-model",
            ),
            400,
            "model_tools_unsupported",
            "The requested model does not support tools",
        ),
        (
            AgentProviderUnavailableError("private-provider"),
            503,
            "provider_unavailable",
            "The requested provider is unavailable",
        ),
        (
            AgentRunNotFoundError(uuid4()),
            404,
            "agent_run_not_found",
            "Agent run not found",
        ),
    ],
)
def test_agent_error_mapping_is_stable_and_safe(
    exception: Exception,
    status_code: int,
    code: str,
    message: str,
) -> None:
    spec = error_spec_for_exception(exception)

    assert spec.status_code == status_code
    assert spec.code == code
    assert spec.message == message
    assert "private" not in spec.message


def test_agent_openapi_exposes_only_plural_run_routes(
    agent_api_context: Any,
) -> None:
    client, _, _, _, _ = agent_api_context

    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/agents/runs" in paths
    assert "/api/v1/agents/runs/{run_id}" in paths
    assert "/api/v1/agents/runs/{run_id}/tool-calls" in paths
    assert "/api/v1/agent/runs" not in paths


def test_agent_api_direct_answer_returns_201_and_persists_run(
    agent_api_context: Any,
) -> None:
    client, factory, provider, _, _ = agent_api_context

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
            "temperature": 0.2,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["goal"] == "Inspect the workspace"
    assert body["final_answer"] == "Agent API answer"
    assert body["error"] is None
    assert body["tool_calls"] == []
    assert provider.requests[0].temperature == 0.2
    assert provider.requests[0].messages[-1].content == "Inspect the workspace"

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 1
        assert session.scalar(select(func.count()).select_from(Message)) == 2
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 1
        assert session.scalar(select(func.count()).select_from(ToolCall)) == 0
        stored = session.scalar(select(AgentRun))
        assert stored is not None
        assert str(stored.id) == body["id"]
        assert stored.status == "completed"
        assert stored.final_answer == "Agent API answer"


def test_agent_api_tool_round_returns_persists_and_queries_call(
    agent_api_context: Any,
    tmp_path: Path,
) -> None:
    client, factory, _, providers, _ = agent_api_context
    (tmp_path / "notes.txt").write_text(
        "Temporary workspace notes",
        encoding="utf-8",
    )
    tool_registry = ToolRegistry()
    register_builtin_tools(tool_registry, workspace_root=tmp_path)
    provider = ToolRoundProvider()
    providers["mock"] = provider
    app.dependency_overrides[get_tool_registry] = lambda: tool_registry

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Read the temporary notes",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["final_answer"] == (
        "The notes describe a temporary workspace."
    )
    assert len(body["tool_calls"]) == 1
    call = body["tool_calls"][0]
    assert call["tool_call_id"] == "call-read-notes"
    assert call["sequence_index"] == 1
    assert call["tool_name"] == "read_file"
    assert call["arguments"] == {"path": "notes.txt"}
    assert call["status"] == "success"
    assert call["error"] is None
    assert call["result"]["content"] == "Temporary workspace notes"
    assert call["result"]["metadata"]["path"] == "notes.txt"
    assert str(tmp_path) not in response.text

    observation = provider.requests[1].messages[-1]
    assert observation.role == "tool"
    assert observation.tool_call_id == "call-read-notes"
    assert json.loads(observation.content or "")["success"] is True

    query = client.get(
        f"/api/v1/agents/runs/{body['id']}/tool-calls"
    )
    assert query.status_code == 200
    assert query.json() == body["tool_calls"]

    with factory() as session:
        stored = session.scalar(select(ToolCall))
        assert stored is not None
        assert stored.status == "success"
        assert stored.result_json is not None
        assert stored.result_json["content"] == "Temporary workspace notes"


def test_agent_api_persists_safe_builtin_rejection_and_completes(
    agent_api_context: Any,
    tmp_path: Path,
) -> None:
    client, factory, _, providers, _ = agent_api_context
    synthetic_secret = "SYNTHETIC_ENVRC_VALUE_DO_NOT_EXPOSE"
    (tmp_path / ".envrc").write_text(synthetic_secret, encoding="utf-8")
    tool_registry = ToolRegistry()
    register_builtin_tools(tool_registry, workspace_root=tmp_path)
    provider = BlockedReadProvider()
    providers["mock"] = provider
    app.dependency_overrides[get_tool_registry] = lambda: tool_registry

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Read the protected environment file",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["final_answer"] == "The protected file was not read."
    assert len(body["tool_calls"]) == 1
    call = body["tool_calls"][0]
    assert call["tool_call_id"] == "call-blocked-envrc"
    assert call["tool_name"] == "read_file"
    assert call["status"] == "failed"
    assert call["error"] == "The requested path is not allowed"
    assert call["result"]["success"] is False
    assert call["result"]["error"] == "The requested path is not allowed"

    observation = provider.requests[1].messages[-1]
    assert observation.role == "tool"
    assert observation.tool_call_id == "call-blocked-envrc"
    assert json.loads(observation.content or "") == call["result"]
    assert synthetic_secret not in response.text
    assert synthetic_secret not in (observation.content or "")
    assert str(tmp_path) not in response.text
    assert str(tmp_path) not in (observation.content or "")

    with factory() as session:
        stored = session.scalar(select(ToolCall))
        assert stored is not None
        assert stored.status == "failed"
        assert stored.error_message == "The requested path is not allowed"
        assert stored.result_json == call["result"]
        assert synthetic_secret not in json.dumps(stored.result_json)


def test_agent_api_commits_structured_failed_run(
    agent_api_context: Any,
) -> None:
    client, factory, _, providers, _ = agent_api_context
    provider = TimeoutAgentProvider()
    providers["mock"] = provider

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["final_answer"] is None
    assert body["error"] == "Model request timed out"
    assert body["tool_calls"] == []
    assert "private-provider-timeout-diagnostic" not in response.text

    query = client.get(f"/api/v1/agents/runs/{body['id']}")
    assert query.status_code == 200
    assert query.json()["status"] == "failed"
    assert query.json()["error"] == "Model request timed out"

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 1
        assert session.scalar(select(func.count()).select_from(Message)) == 1
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 1
        assert session.scalar(select(func.count()).select_from(ToolCall)) == 0


def test_agent_api_max_steps_failure_preserves_budgeted_tool_only(
    agent_api_context: Any,
) -> None:
    client, factory, _, providers, _ = agent_api_context
    provider = LastStepToolProvider()
    providers["mock"] = provider

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Do not execute beyond the limit",
            "max_steps": 1,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"] == "Agent reached the maximum number of steps"
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["tool_call_id"] == "call-not-executed"
    assert body["tool_calls"][0]["sequence_index"] == 1
    assert body["tool_calls"][0]["status"] == "success"
    assert len(provider.requests) == 2

    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Message)) == 1
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 1
        assert session.scalar(select(func.count()).select_from(ToolCall)) == 1


def test_agent_api_queries_existing_run_and_empty_calls(
    agent_api_context: Any,
) -> None:
    client, _, _, _, _ = agent_api_context
    created = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
        },
    ).json()

    run_response = client.get(
        f"/api/v1/agents/runs/{created['id']}"
    )
    calls_response = client.get(
        f"/api/v1/agents/runs/{created['id']}/tool-calls"
    )

    assert run_response.status_code == 200
    assert run_response.json() == {
        key: value for key, value in created.items() if key != "tool_calls"
    }
    assert calls_response.status_code == 200
    assert calls_response.json() == []


def test_agent_api_tool_call_query_uses_deterministic_order(
    agent_api_context: Any,
) -> None:
    client, factory, _, _, _ = agent_api_context
    created_at = datetime(2026, 7, 19, 12, 0, 0)
    with factory() as session:
        conversation = Conversation(title="Ordered ToolCalls")
        run = AgentRun(
            conversation=conversation,
            status="completed",
            goal="Order calls",
            final_answer="Done",
        )
        session.add(run)
        session.flush()
        run_id = run.id
        session.add_all(
            [
                ToolCall(
                    id=UUID(int=1),
                    tool_call_id="call-later",
                    sequence_index=2,
                    agent_run_id=run.id,
                    conversation_id=run.conversation_id,
                    tool_name="list_dir",
                    arguments_json={"path": "."},
                    result_json=ToolResult(
                        tool_name="list_dir",
                        success=True,
                    ).model_dump(mode="json"),
                    status="success",
                    created_at=created_at,
                ),
                ToolCall(
                    id=UUID(int=2),
                    tool_call_id="call-earlier",
                    sequence_index=1,
                    agent_run_id=run.id,
                    conversation_id=run.conversation_id,
                    tool_name="read_file",
                    arguments_json={"path": "README.md"},
                    result_json=ToolResult(
                        tool_name="read_file",
                        success=True,
                    ).model_dump(mode="json"),
                    status="success",
                    created_at=created_at,
                ),
            ]
        )
        session.commit()

    response = client.get(
        f"/api/v1/agents/runs/{run_id}/tool-calls"
    )

    assert response.status_code == 200
    assert [item["tool_call_id"] for item in response.json()] == [
        "call-earlier",
        "call-later",
    ]
    assert [item["sequence_index"] for item in response.json()] == [1, 2]


@pytest.mark.parametrize("suffix", ["", "/tool-calls"])
def test_agent_api_returns_404_for_unknown_run_query(
    agent_api_context: Any,
    suffix: str,
) -> None:
    client, _, _, _, _ = agent_api_context

    response = client.get(
        f"/api/v1/agents/runs/{uuid4()}{suffix}"
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "agent_run_not_found",
            "message": "Agent run not found",
            "request_id": response.headers["x-request-id"],
        }
    }


@pytest.mark.parametrize("suffix", ["", "/tool-calls"])
def test_agent_api_rejects_malformed_run_id(
    agent_api_context: Any,
    suffix: str,
) -> None:
    client, _, _, _, _ = agent_api_context

    response = client.get(
        f"/api/v1/agents/runs/not-a-uuid{suffix}"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "request_update",
    [
        {"input": "   "},
        {"content": "not an accepted alias"},
        {"max_steps": True},
    ],
)
def test_agent_api_rejects_invalid_request_without_persistence(
    agent_api_context: Any,
    request_update: dict[str, object],
) -> None:
    client, factory, _, _, _ = agent_api_context
    payload: dict[str, object] = {
        "provider": "mock",
        "model": "tools-model",
        "input": "Inspect the workspace",
    }
    payload.update(request_update)

    response = client.post("/api/v1/agents/runs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0


def test_agent_api_rejects_unknown_model_before_persistence(
    agent_api_context: Any,
) -> None:
    client, factory, _, _, _ = agent_api_context

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "missing-model",
            "input": "Inspect the workspace",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "model_not_found"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0


def test_agent_api_rejects_model_without_tools_before_persistence(
    agent_api_context: Any,
) -> None:
    client, factory, _, _, _ = agent_api_context
    unsupported_registry = ModelRegistry(
        [
            ModelInfo(
                provider="mock",
                model="tools-model",
                display_name="No Tools Model",
                supports_tools=False,
            )
        ]
    )
    app.dependency_overrides[get_model_registry] = (
        lambda: unsupported_registry
    )

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "model_tools_unsupported"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0


def test_agent_api_rejects_unavailable_provider_before_persistence(
    agent_api_context: Any,
) -> None:
    client, factory, _, providers, _ = agent_api_context
    providers.clear()

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_unavailable"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0


def test_agent_api_rejects_unknown_conversation_before_run(
    agent_api_context: Any,
) -> None:
    client, factory, _, _, _ = agent_api_context

    response = client.post(
        "/api/v1/agents/runs",
        json={
            "conversation_id": str(uuid4()),
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0


def test_agent_queries_work_without_provider_configuration(
    agent_api_context: Any,
) -> None:
    client, _, _, _, _ = agent_api_context
    created = client.post(
        "/api/v1/agents/runs",
        json={
            "provider": "mock",
            "model": "tools-model",
            "input": "Inspect the workspace",
        },
    ).json()

    def raise_provider_configuration() -> dict[str, BaseLLMProvider]:
        raise ProviderConfigurationError(
            "private-provider-configuration-diagnostic"
        )

    app.dependency_overrides[get_llm_providers] = (
        raise_provider_configuration
    )

    run_response = client.get(
        f"/api/v1/agents/runs/{created['id']}"
    )
    calls_response = client.get(
        f"/api/v1/agents/runs/{created['id']}/tool-calls"
    )

    assert run_response.status_code == 200
    assert calls_response.status_code == 200
    assert "private-provider-configuration-diagnostic" not in (
        run_response.text + calls_response.text
    )


def test_agent_api_commit_failure_does_not_return_created(
    agent_api_context: Any,
) -> None:
    _, factory, _, _, _ = agent_api_context

    class FailingCommitSession(Session):
        def commit(self) -> None:
            raise SQLAlchemyError(
                "private-database-commit-diagnostic"
            )

    failing_factory = sessionmaker(
        bind=factory.kw["bind"],
        class_=FailingCommitSession,
        expire_on_commit=False,
    )

    async def override_failing_session() -> AsyncIterator[Session]:
        session = failing_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_failing_session
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/agents/runs",
            json={
                "provider": "mock",
                "model": "tools-model",
                "input": "Inspect the workspace",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_error",
            "message": "The database operation failed",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private-database-commit-diagnostic" not in response.text
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
