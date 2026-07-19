import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.agents import (
    AgentModelNotFoundError,
    AgentModelToolsUnsupportedError,
    AgentProviderUnavailableError,
    SimpleAgentRequest,
    SimpleAgentService,
)
from app.db.base import Base
from app.db.session import create_db_engine
from app.models import AgentRun, Message, ToolCall
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatRequest,
    LLMResponse,
    LLMToolCall,
    ProviderServerError,
    ProviderTimeoutError,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService
from app.tools import Tool, ToolRegistry, ToolResult, register_builtin_tools


class SequenceProvider(BaseLLMProvider):
    def __init__(
        self,
        responses: list[LLMResponse | BaseException | None],
    ) -> None:
        self._responses = list(responses)
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("Unexpected Provider call")
        response = self._responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response  # type: ignore[return-value]

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise NotImplementedError


class ControlledTool(Tool):
    def __init__(
        self,
        *,
        mode: str,
        name: str = "controlled_tool",
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            name=name,
            description="Controlled test Tool",
            parameters_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            permission_level="read_only",
            timeout_seconds=timeout_seconds,
        )
        self._mode = mode
        self.calls = 0
        self.timeout_completed = False
        self.timeout_finally_ran = False
        self.last_result: ToolResult | None = None

    async def run(self, arguments: dict[str, object]) -> ToolResult:
        self.calls += 1
        if self._mode == "timeout":
            try:
                await asyncio.sleep(0.05)
                self.timeout_completed = True
            finally:
                self.timeout_finally_ran = True
        if self._mode == "raise":
            raise RuntimeError("synthetic-secret")
        if self._mode == "mismatch":
            return ToolResult(
                tool_name="other_tool",
                success=True,
                content="unexpected",
            )
        if self._mode == "failed":
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Safe tool failure",
            )
        if self._mode == "non_json":
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"value": float("nan")},
            )
        if self._mode == "large":
            self.last_result = ToolResult(
                tool_name=self.name,
                success=True,
                content="x" * 2_000,
                data={"large": "y" * 2_000},
                metadata={"large": "z" * 2_000},
            )
            return self.last_result
        if self._mode == "large_error":
            self.last_result = ToolResult(
                tool_name=self.name,
                success=False,
                error="\x00" * 2_000,
            )
            return self.last_result
        self.last_result = ToolResult(
            tool_name=self.name,
            success=True,
            content="controlled result",
        )
        return self.last_result


def create_test_session(tmp_path: Path) -> tuple[Session, Engine]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'simple-agent.db'}")
    Base.metadata.create_all(engine)
    return Session(engine), engine


def create_registry(*, supports_tools: bool = True) -> ModelRegistry:
    return ModelRegistry(
        [
            ModelInfo(
                provider="mock",
                model="tool-model",
                display_name="Tool Model",
                supports_tools=supports_tools,
            )
        ]
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"content": " "},
        {"provider": " "},
        {"model": " "},
        {"temperature": -0.1},
        {"temperature": 2.1},
        {"max_tokens": 0},
        {"max_steps": 0},
        {"max_steps": 11},
        {"max_steps": True},
    ],
)
def test_simple_agent_request_rejects_invalid_values(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "provider": "mock",
        "model": "tool-model",
        "content": "hello",
    }
    values.update(overrides)

    with pytest.raises(ValidationError):
        SimpleAgentRequest.model_validate(values)


def test_simple_agent_request_defaults_to_three_steps() -> None:
    request = SimpleAgentRequest(
        provider="mock",
        model="tool-model",
        content="hello",
    )

    assert request.max_steps == 3


def test_agent_rejects_missing_model_before_persistence(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = SimpleAgentService(
        session,
        registry=ModelRegistry([]),
        providers={"mock": SequenceProvider([])},
        tools=ToolRegistry(),
    )

    with pytest.raises(AgentModelNotFoundError):
        asyncio.run(
            service.run(
                SimpleAgentRequest(
                    provider="mock",
                    model="missing-model",
                    content="hello",
                )
            )
        )

    assert session.scalars(select(AgentRun)).all() == []
    session.close()
    engine.dispose()


def test_agent_rejects_model_without_tool_capability_before_persistence(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(supports_tools=False),
        providers={"mock": SequenceProvider([])},
        tools=ToolRegistry(),
    )

    with pytest.raises(AgentModelToolsUnsupportedError):
        asyncio.run(
            service.run(
                SimpleAgentRequest(
                    provider="mock",
                    model="tool-model",
                    content="hello",
                )
            )
        )

    assert session.scalars(select(AgentRun)).all() == []
    session.close()
    engine.dispose()


def test_agent_rejects_unavailable_provider_before_persistence(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={},
        tools=ToolRegistry(),
    )

    with pytest.raises(AgentProviderUnavailableError):
        asyncio.run(
            service.run(
                SimpleAgentRequest(
                    provider="mock",
                    model="tool-model",
                    content="hello",
                )
            )
        )

    assert session.scalars(select(AgentRun)).all() == []
    session.close()
    engine.dispose()


def test_agent_direct_answer_creates_completed_run_without_tool_calls(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                id="response-1",
                model="resolved-model",
                content="Direct answer",
                finish_reason="stop",
            )
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Answer directly",
                temperature=0.2,
                max_tokens=50,
            )
        )
    )

    assert len(provider.requests) == 1
    assert [
        definition.function.name
        for definition in provider.requests[0].tools
    ] == ["read_file", "list_dir"]
    assert [
        (message.role, message.content)
        for message in provider.requests[0].messages
    ] == [("user", "Answer directly")]
    assert provider.requests[0].temperature == 0.2
    assert provider.requests[0].max_tokens == 50
    assert result.agent_run.status == "completed"
    assert result.agent_run.final_answer == "Direct answer"
    assert result.agent_run.error_message is None
    assert result.agent_run.user_message_id == result.user_message.id
    assert result.agent_run.started_at is not None
    assert result.agent_run.ended_at is not None
    assert result.agent_run.latency_ms is not None
    assert result.agent_run.latency_ms >= 0
    assert result.assistant_message is not None
    assert result.assistant_message.content == "Direct answer"
    assert result.assistant_message.provider == "mock"
    assert result.assistant_message.model == "resolved-model"
    assert result.tool_calls == ()
    assert session.scalars(select(ToolCall)).all() == []
    assert result.conversation.title == "Answer directly"
    assert result.conversation.default_provider == "mock"
    assert result.conversation.default_model == "tool-model"
    session.close()
    engine.dispose()


def test_agent_direct_answer_includes_existing_history(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversations = ConversationService(session)
    conversation = conversations.create_conversation(
        ConversationCreate(title="Existing title")
    )
    conversations.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="user",
            content="Earlier question",
        )
    )
    conversations.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="assistant",
            content="Earlier answer",
        )
    )
    provider = SequenceProvider(
        [LLMResponse(model="resolved-model", content="Follow-up answer")]
    )
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=ToolRegistry(),
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                conversation_id=conversation.id,
                provider="mock",
                model="tool-model",
                content="Follow-up question",
            )
        )
    )

    assert [
        (message.role, message.content)
        for message in provider.requests[0].messages
    ] == [
        ("user", "Earlier question"),
        ("assistant", "Earlier answer"),
        ("user", "Follow-up question"),
    ]
    assert result.conversation.id == conversation.id
    assert result.conversation.title == "Existing title"
    assert [
        (message.role, message.content)
        for message in conversations.list_messages(conversation.id)
    ] == [
        ("user", "Earlier question"),
        ("assistant", "Earlier answer"),
        ("user", "Follow-up question"),
        ("assistant", "Follow-up answer"),
    ]
    session.close()
    engine.dispose()


def test_agent_returns_failed_result_for_blank_terminal_text(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [LLMResponse(model="resolved-model", content="   ")]
    )
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=ToolRegistry(),
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Answer directly",
            )
        )
    )

    runs = session.scalars(select(AgentRun)).all()
    assert len(provider.requests) == 1
    assert len(runs) == 1
    assert result.assistant_message is None
    assert result.agent_run is runs[0]
    assert runs[0].status == "failed"
    assert runs[0].error_message == "Agent did not produce a final answer"
    assert runs[0].ended_at is not None
    assert runs[0].latency_ms is not None
    session.close()
    engine.dispose()


def test_agent_executes_read_file_and_backfills_observation(
    tmp_path: Path,
) -> None:
    (tmp_path / "guide.txt").write_text(
        "workspace guide",
        encoding="utf-8",
    )
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                finish_reason="tool_calls",
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_1",
                        tool_name="read_file",
                        arguments={"path": "guide.txt"},
                    ),
                ),
            ),
            LLMResponse(
                model="resolved-model",
                content="The guide was read",
                finish_reason="stop",
            ),
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Read the guide",
            )
        )
    )

    assert len(provider.requests) == 2
    second_messages = provider.requests[1].messages
    assert second_messages[-2].role == "assistant"
    assert second_messages[-2].content is None
    assert second_messages[-2].tool_calls[0].tool_call_id == "call_1"
    assert second_messages[-1].role == "tool"
    assert second_messages[-1].tool_call_id == "call_1"
    observation = json.loads(second_messages[-1].content or "")
    assert observation["tool_name"] == "read_file"
    assert observation["success"] is True
    assert observation["content"] == "workspace guide"
    assert provider.requests[1].tools == provider.requests[0].tools
    assert result.assistant_message.content == "The guide was read"
    assert result.agent_run.status == "completed"
    assert result.agent_run.final_answer == "The guide was read"
    assert [call.tool_call_id for call in result.tool_calls] == ["call_1"]
    session.close()
    engine.dispose()


def test_agent_completes_three_provider_steps_with_two_tool_rounds(
    tmp_path: Path,
) -> None:
    (tmp_path / "guide.txt").write_text("guide", encoding="utf-8")
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_read",
                        tool_name="read_file",
                        arguments={"path": "guide.txt"},
                    ),
                ),
            ),
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_list",
                        tool_name="list_dir",
                        arguments={"path": ".", "max_depth": 1},
                    ),
                ),
            ),
            LLMResponse(
                model="resolved-model",
                content="Two rounds completed",
            ),
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Inspect in two rounds",
            )
        )
    )

    assert len(provider.requests) == 3
    assert result.agent_run.status == "completed"
    assert result.assistant_message is not None
    assert result.assistant_message.content == "Two rounds completed"
    assert [call.tool_call_id for call in result.tool_calls] == [
        "call_read",
        "call_list",
    ]
    third_messages = provider.requests[2].messages
    assert [message.role for message in third_messages[-4:]] == [
        "assistant",
        "tool",
        "assistant",
        "tool",
    ]
    assert third_messages[-4].tool_calls[0].tool_call_id == "call_read"
    assert third_messages[-3].tool_call_id == "call_read"
    assert third_messages[-2].tool_calls[0].tool_call_id == "call_list"
    assert third_messages[-1].tool_call_id == "call_list"
    run_id = result.agent_run.id
    session.commit()
    session.expire_all()
    loaded_run = session.get(AgentRun, run_id)
    loaded_calls = session.scalars(
        select(ToolCall).where(ToolCall.agent_run_id == run_id)
    ).all()
    assert loaded_run is not None
    assert loaded_run.status == "completed"
    assert loaded_run.final_answer == "Two rounds completed"
    assert loaded_run.error_message is None
    assert loaded_run.ended_at is not None
    assert loaded_run.latency_ms is not None
    assert {
        call.tool_call_id: call.status for call in loaded_calls
    } == {"call_read": "success", "call_list": "success"}
    session.close()
    engine.dispose()


def test_agent_preserves_multiple_tool_call_observation_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "guide.txt").write_text("guide", encoding="utf-8")
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content="I will inspect the workspace.",
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_read",
                        tool_name="read_file",
                        arguments={"path": "guide.txt"},
                    ),
                    LLMToolCall(
                        tool_call_id="call_list",
                        tool_name="list_dir",
                        arguments={"path": ".", "max_depth": 1},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Inspection done"),
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Inspect the workspace",
                max_steps=2,
            )
        )
    )

    assert len(provider.requests) == 2
    follow_up = provider.requests[1].messages
    assert follow_up[-3].role == "assistant"
    assert follow_up[-3].content == "I will inspect the workspace."
    assert [call.tool_call_id for call in follow_up[-3].tool_calls] == [
        "call_read",
        "call_list",
    ]
    assert [message.tool_call_id for message in follow_up[-2:]] == [
        "call_read",
        "call_list",
    ]
    assert [
        json.loads(message.content or "")["tool_name"]
        for message in follow_up[-2:]
    ] == ["read_file", "list_dir"]
    assert [call.tool_call_id for call in result.tool_calls] == [
        "call_read",
        "call_list",
    ]
    session.close()
    engine.dispose()


def test_agent_backfills_unknown_tool_as_safe_failure(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_unknown",
                        tool_name="unknown_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Tool unavailable"),
        ]
    )
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=ToolRegistry(),
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Use an unavailable Tool",
            )
        )
    )

    observation = json.loads(
        provider.requests[1].messages[-1].content or ""
    )
    assert observation["success"] is False
    assert observation["error"] == "Tool is not available"
    assert result.agent_run.status == "completed"
    session.close()
    engine.dispose()


def test_agent_backfills_argument_validation_without_rejected_values(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_invalid",
                        tool_name="read_file",
                        arguments={
                            "path": "guide.txt",
                            "unexpected": "synthetic-secret",
                        },
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Invalid arguments"),
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Use invalid arguments",
            )
        )
    )

    observation_text = provider.requests[1].messages[-1].content or ""
    observation = json.loads(observation_text)
    assert observation["success"] is False
    assert observation["error"].startswith(
        "Invalid arguments for tool 'read_file':"
    )
    assert "synthetic-secret" not in observation_text
    assert "guide.txt" not in observation_text
    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    ("mode", "expected_error"),
    [
        ("failed", "Safe tool failure"),
        ("raise", "Tool execution failed"),
        ("mismatch", "Tool execution failed"),
        ("non_json", "Tool execution failed"),
    ],
)
def test_agent_normalizes_controlled_tool_failures(
    tmp_path: Path,
    mode: str,
    expected_error: str,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id=f"call_{mode}",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Handled failure"),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(ControlledTool(mode=mode))
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Run controlled Tool",
            )
        )
    )

    observation_text = provider.requests[1].messages[-1].content or ""
    observation = json.loads(observation_text)
    assert observation["success"] is False
    assert observation["error"] == expected_error
    assert "synthetic-secret" not in observation_text
    assert result.agent_run.status == "completed"
    session.close()
    engine.dispose()


def test_agent_records_tool_timeout_and_continues_same_round(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    timeout_tool = ControlledTool(
        mode="timeout",
        name="slow_tool",
        timeout_seconds=0.001,
    )
    success_tool = ControlledTool(mode="success", name="fast_tool")
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_slow",
                        tool_name="slow_tool",
                        arguments={},
                    ),
                    LLMToolCall(
                        tool_call_id="call_fast",
                        tool_name="fast_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(
                model="resolved-model",
                content="Handled timeout",
            ),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(timeout_tool)
    tools.register_tool(success_tool)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Run both Tools",
            )
        )
    )

    assert [call.status for call in result.tool_calls] == [
        "timeout",
        "success",
    ]
    assert result.tool_calls[0].error_message == "Tool execution timed out"
    observations = [
        json.loads(message.content or "")
        for message in provider.requests[1].messages[-2:]
    ]
    assert observations[0]["success"] is False
    assert observations[0]["error"] == "Tool execution timed out"
    assert observations[1]["success"] is True
    assert timeout_tool.calls == 1
    assert timeout_tool.timeout_finally_ran is True
    assert timeout_tool.timeout_completed is False
    assert success_tool.calls == 1
    assert result.agent_run.status == "completed"
    run_id = result.agent_run.id
    session.commit()
    session.expire_all()
    loaded_calls = session.scalars(
        select(ToolCall).where(ToolCall.agent_run_id == run_id)
    ).all()
    assert {
        call.tool_call_id: call.status for call in loaded_calls
    } == {"call_slow": "timeout", "call_fast": "success"}
    timeout_row = next(
        call for call in loaded_calls if call.tool_call_id == "call_slow"
    )
    assert timeout_row.error_message == "Tool execution timed out"
    assert timeout_row.ended_at is not None
    assert timeout_row.latency_ms is not None
    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    "invalid_limit",
    [True, 1024.0, 1023],
)
def test_agent_service_rejects_invalid_tool_observation_limit(
    tmp_path: Path,
    invalid_limit: object,
) -> None:
    session, engine = create_test_session(tmp_path)

    with pytest.raises((TypeError, ValueError)):
        SimpleAgentService(
            session,
            registry=create_registry(),
            providers={"mock": SequenceProvider([])},
            tools=ToolRegistry(),
            max_tool_observation_chars=invalid_limit,
        )

    session.close()
    engine.dispose()


def test_agent_service_accepts_minimum_tool_observation_limit(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)

    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": SequenceProvider([])},
        tools=ToolRegistry(),
        max_tool_observation_chars=1024,
    )

    assert service is not None
    session.close()
    engine.dispose()


def test_agent_compacts_provider_observation_but_persists_full_result(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    large_tool = ControlledTool(mode="large")
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_large",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Compacted"),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(large_tool)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
        max_tool_observation_chars=1024,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Return a large result",
            )
        )
    )

    observation_text = provider.requests[1].messages[-1].content or ""
    observation = json.loads(observation_text)
    stored_result = result.tool_calls[0].result_json
    assert len(observation_text) <= 1024
    assert observation["tool_name"] == "controlled_tool"
    assert observation["success"] is True
    assert observation["data"] is None
    assert observation["content"].endswith("…")
    assert observation["metadata"] == {
        "observation_truncated": True,
        "original_characters": observation["metadata"][
            "original_characters"
        ],
    }
    assert stored_result is not None
    full_text = json.dumps(
        stored_result,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    assert observation["metadata"]["original_characters"] == len(full_text)
    assert stored_result["content"] == "x" * 2_000
    assert stored_result["data"] == {"large": "y" * 2_000}
    assert stored_result["metadata"] == {"large": "z" * 2_000}
    assert large_tool.last_result is not None
    assert large_tool.last_result.content == "x" * 2_000
    assert large_tool.last_result.data == {"large": "y" * 2_000}
    assert large_tool.last_result.metadata == {"large": "z" * 2_000}
    session.close()
    engine.dispose()


def test_agent_preserves_small_tool_observation_exactly(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    controlled_tool = ControlledTool(mode="success")
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_small",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Unchanged"),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(controlled_tool)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
        max_tool_observation_chars=1024,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Return a small result",
            )
        )
    )

    observation_text = provider.requests[1].messages[-1].content or ""
    expected_text = json.dumps(
        result.tool_calls[0].result_json,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    assert observation_text == expected_text
    session.close()
    engine.dispose()


def test_agent_compacts_json_escaped_tool_error_within_limit(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    controlled_tool = ControlledTool(mode="large_error")
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_large_error",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Handled"),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(controlled_tool)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
        max_tool_observation_chars=1024,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Return an escaped error",
            )
        )
    )

    observation_text = provider.requests[1].messages[-1].content or ""
    observation = json.loads(observation_text)
    assert len(observation_text) <= 1024
    assert observation["success"] is False
    assert len(observation["error"]) <= 256
    assert observation["error"].endswith("…")
    assert result.tool_calls[0].result_json is not None
    assert result.tool_calls[0].result_json["error"] == "\x00" * 2_000
    session.close()
    engine.dispose()


def test_agent_rejects_tool_call_id_reused_across_rounds_safely(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    repeated_call = LLMToolCall(
        tool_call_id="call_reused",
        tool_name="controlled_tool",
        arguments={},
    )
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(repeated_call,),
            ),
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(repeated_call,),
            ),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(ControlledTool(mode="success"))
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Reuse an invalid ID",
            )
        )
    )

    stored_calls = session.scalars(select(ToolCall)).all()
    assert len(provider.requests) == 2
    assert result.assistant_message is None
    assert result.agent_run.status == "failed"
    assert result.agent_run.error_message == "Model request failed"
    assert [call.tool_call_id for call in result.tool_calls] == [
        "call_reused"
    ]
    assert [call.tool_call_id for call in stored_calls] == ["call_reused"]
    session.commit()
    session.close()
    engine.dispose()


def test_agent_returns_failed_result_at_maximum_steps_without_executing_call(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    repeated_call = LLMToolCall(
        tool_call_id="call_1",
        tool_name="read_file",
        arguments={"path": "missing.txt"},
    )
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(repeated_call,),
            ),
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    repeated_call.model_copy(
                        update={"tool_call_id": "call_2"}
                    ),
                ),
            ),
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Keep reading",
                max_steps=2,
            )
        )
    )

    run = session.scalar(select(AgentRun))
    stored_calls = session.scalars(select(ToolCall)).all()
    assert len(provider.requests) == 2
    assert run is not None
    assert result.assistant_message is None
    assert result.agent_run is run
    assert [call.tool_call_id for call in result.tool_calls] == ["call_1"]
    assert [call.tool_call_id for call in stored_calls] == ["call_1"]
    assert run.status == "failed"
    assert run.error_message == "Agent reached the maximum number of steps"
    run_id = run.id
    conversation_id = result.conversation.id
    session.commit()
    session.expire_all()
    loaded_run = session.get(AgentRun, run_id)
    loaded_messages = session.scalars(
        select(Message).where(Message.conversation_id == conversation_id)
    ).all()
    assert loaded_run is not None
    assert loaded_run.status == "failed"
    assert loaded_run.final_answer is None
    assert loaded_run.error_message == (
        "Agent reached the maximum number of steps"
    )
    assert loaded_run.ended_at is not None
    assert loaded_run.latency_ms is not None
    assert [(message.role, message.content) for message in loaded_messages] == [
        ("user", "Keep reading")
    ]
    session.close()
    engine.dispose()


def test_agent_max_steps_one_does_not_execute_initial_tool_call(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_not_executed",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            )
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(ControlledTool(mode="success"))
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Do not exceed one decision",
                max_steps=1,
            )
        )
    )

    assert len(provider.requests) == 1
    assert result.assistant_message is None
    assert result.agent_run.status == "failed"
    assert result.agent_run.error_message == (
        "Agent reached the maximum number of steps"
    )
    assert result.tool_calls == ()
    assert session.scalars(select(ToolCall)).all() == []
    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    ("provider_error", "expected_error"),
    [
        (
            ProviderTimeoutError("synthetic-secret"),
            "Model request timed out",
        ),
        (
            ProviderServerError("synthetic-secret"),
            "Model request failed",
        ),
        (RuntimeError("synthetic-secret"), "Model request failed"),
    ],
)
def test_agent_returns_safe_failed_result_for_initial_provider_failure(
    tmp_path: Path,
    provider_error: Exception,
    expected_error: str,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider([provider_error])
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=ToolRegistry(),
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Handle Provider failure",
            )
        )
    )
    run_id = result.agent_run.id
    session.commit()
    session.expire_all()
    loaded_run = session.get(AgentRun, run_id)

    assert len(provider.requests) == 1
    assert result.assistant_message is None
    assert result.tool_calls == ()
    assert loaded_run is not None
    assert loaded_run.status == "failed"
    assert loaded_run.final_answer is None
    assert loaded_run.error_message == expected_error
    assert loaded_run.ended_at is not None
    assert loaded_run.latency_ms is not None
    assert "synthetic-secret" not in str(loaded_run.error_message)
    session.close()
    engine.dispose()


def test_agent_preserves_completed_tool_call_when_followup_provider_fails(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_before_failure",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            ),
            ProviderServerError("synthetic-secret"),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(ControlledTool(mode="success"))
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Fail after Tool execution",
            )
        )
    )
    run_id = result.agent_run.id
    session.commit()
    session.expire_all()
    loaded_run = session.get(AgentRun, run_id)
    loaded_calls = session.scalars(
        select(ToolCall).where(ToolCall.agent_run_id == run_id)
    ).all()

    assert len(provider.requests) == 2
    assert result.assistant_message is None
    assert loaded_run is not None
    assert loaded_run.status == "failed"
    assert loaded_run.error_message == "Model request failed"
    assert [call.tool_call_id for call in loaded_calls] == [
        "call_before_failure"
    ]
    assert loaded_calls[0].status == "success"
    assert "synthetic-secret" not in str(loaded_run.error_message)
    assert "synthetic-secret" not in str(loaded_calls[0].result_json)
    session.close()
    engine.dispose()


def test_agent_returns_safe_failure_for_invalid_provider_result(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider([None])
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=ToolRegistry(),
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Reject invalid Provider result",
            )
        )
    )

    assert result.assistant_message is None
    assert result.agent_run.status == "failed"
    assert result.agent_run.error_message == "Model request failed"
    session.close()
    engine.dispose()


def test_agent_does_not_swallow_provider_cancellation(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider([asyncio.CancelledError()])
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=ToolRegistry(),
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            service.run(
                SimpleAgentRequest(
                    provider="mock",
                    model="tool-model",
                    content="Cancel Provider request",
                )
            )
        )

    session.close()
    engine.dispose()


def test_agent_persists_successful_tool_call_round_trip(
    tmp_path: Path,
) -> None:
    (tmp_path / "guide.txt").write_text(
        "workspace guide",
        encoding="utf-8",
    )
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_1",
                        tool_name="read_file",
                        arguments={"path": "guide.txt"},
                    ),
                ),
            ),
            LLMResponse(
                model="resolved-model",
                content="The guide was read",
            ),
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, workspace_root=tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Read the guide",
            )
        )
    )
    run_id = result.agent_run.id
    user_message_id = result.user_message.id
    session.commit()
    session.expire_all()

    loaded_run = session.scalar(
        select(AgentRun).where(AgentRun.id == run_id)
    )
    loaded_calls = session.scalars(
        select(ToolCall).where(ToolCall.agent_run_id == run_id)
    ).all()

    assert loaded_run is not None
    assert loaded_run.status == "completed"
    assert loaded_run.final_answer == "The guide was read"
    assert loaded_run.error_message is None
    assert loaded_run.user_message_id == user_message_id
    assert loaded_run.started_at is not None
    assert loaded_run.ended_at is not None
    assert loaded_run.latency_ms is not None
    assert len(loaded_calls) == 1
    assert loaded_calls[0].tool_call_id == "call_1"
    assert loaded_calls[0].tool_name == "read_file"
    assert loaded_calls[0].arguments_json == {"path": "guide.txt"}
    assert loaded_calls[0].status == "success"
    assert loaded_calls[0].result_json is not None
    assert loaded_calls[0].result_json["success"] is True
    assert loaded_calls[0].result_json["content"] == "workspace guide"
    assert loaded_calls[0].error_message is None
    assert loaded_calls[0].started_at is not None
    assert loaded_calls[0].ended_at is not None
    assert loaded_calls[0].latency_ms is not None
    assert loaded_calls[0].latency_ms >= 0
    assert result.tool_calls == tuple(loaded_calls)
    session.close()
    engine.dispose()


def test_agent_persists_failed_tool_call_without_exception_leakage(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = SequenceProvider(
        [
            LLMResponse(
                model="tool-model",
                content=None,
                tool_calls=(
                    LLMToolCall(
                        tool_call_id="call_raise",
                        tool_name="controlled_tool",
                        arguments={},
                    ),
                ),
            ),
            LLMResponse(model="resolved-model", content="Handled failure"),
        ]
    )
    tools = ToolRegistry()
    tools.register_tool(ControlledTool(mode="raise"))
    service = SimpleAgentService(
        session,
        registry=create_registry(),
        providers={"mock": provider},
        tools=tools,
    )

    result = asyncio.run(
        service.run(
            SimpleAgentRequest(
                provider="mock",
                model="tool-model",
                content="Run controlled Tool",
            )
        )
    )
    run_id = result.agent_run.id
    session.commit()
    session.expire_all()

    loaded_run = session.get(AgentRun, run_id)
    loaded_call = session.scalar(
        select(ToolCall).where(ToolCall.agent_run_id == run_id)
    )

    assert loaded_run is not None
    assert loaded_run.status == "completed"
    assert loaded_call is not None
    assert loaded_call.status == "failed"
    assert loaded_call.arguments_json == {}
    assert loaded_call.error_message == "Tool execution failed"
    assert loaded_call.result_json == {
        "tool_name": "controlled_tool",
        "success": False,
        "content": "",
        "data": None,
        "error": "Tool execution failed",
        "metadata": {},
    }
    assert "synthetic-secret" not in str(loaded_call.result_json)
    assert "synthetic-secret" not in (loaded_call.error_message or "")
    assert loaded_call.started_at is not None
    assert loaded_call.ended_at is not None
    assert loaded_call.latency_ms is not None
    session.close()
    engine.dispose()
