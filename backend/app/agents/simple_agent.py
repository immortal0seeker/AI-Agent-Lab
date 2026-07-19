import asyncio
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)
from sqlalchemy.orm import Session

from app.agents.errors import (
    AgentModelNotFoundError,
    AgentModelToolsUnsupportedError,
    AgentProviderUnavailableError,
)
from app.models import AgentRun, Conversation, Message, ToolCall
from app.models.common import utc_now
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatMessage,
    ChatRequest,
    LLMResponse,
    LLMToolCall,
    ProviderTimeoutError,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.providers.llm.tool_adapter import build_llm_tool_definitions
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService
from app.tools.base import ToolResult
from app.tools.registry import ToolNotFoundError, ToolRegistry
from app.tools.validation import (
    ToolArgumentValidationError,
    validate_tool_arguments,
)


NonEmptyIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

MAX_STEPS_ERROR = "Agent reached the maximum number of steps"
INCOMPLETE_ERROR = "Agent did not produce a final answer"
DEFAULT_MAX_TOOL_OBSERVATION_CHARS = 32_000
MAX_COMPACT_ERROR_CHARS = 256


class SimpleAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conversation_id: UUID | None = None
    provider: NonEmptyIdentifier = Field(max_length=100)
    model: NonEmptyIdentifier = Field(max_length=255)
    content: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    max_steps: int = Field(default=3, ge=1, le=10, strict=True)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


@dataclass(frozen=True, slots=True)
class SimpleAgentResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message | None
    agent_run: AgentRun
    tool_calls: tuple[ToolCall, ...]
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class _ToolExecution:
    result: ToolResult
    status: Literal["success", "failed", "timeout"]


class SimpleAgentService:
    def __init__(
        self,
        session: Session,
        *,
        registry: ModelRegistry,
        providers: Mapping[str, BaseLLMProvider],
        tools: ToolRegistry,
        max_tool_observation_chars: int = DEFAULT_MAX_TOOL_OBSERVATION_CHARS,
    ) -> None:
        if isinstance(max_tool_observation_chars, bool) or not isinstance(
            max_tool_observation_chars,
            int,
        ):
            raise TypeError("max_tool_observation_chars must be an integer")
        if max_tool_observation_chars < 1024:
            raise ValueError(
                "max_tool_observation_chars must be at least 1024"
            )
        self._session = session
        self._registry = registry
        self._providers = providers
        self._tools = tools
        self._max_tool_observation_chars = max_tool_observation_chars
        self._conversations = ConversationService(session)

    async def run(self, request: SimpleAgentRequest) -> SimpleAgentResult:
        _, provider = self._resolve_model_and_provider(request)
        is_new_conversation = request.conversation_id is None
        if is_new_conversation:
            conversation = self._conversations.create_conversation(
                ConversationCreate(
                    default_provider=request.provider,
                    default_model=request.model,
                )
            )
        else:
            conversation = self._conversations.get_conversation(
                request.conversation_id
            )

        user_message = self._conversations.append_message(
            MessageCreate(
                conversation_id=conversation.id,
                role="user",
                content=request.content,
            )
        )
        history = self._conversations.list_messages(conversation.id)
        messages = [
            ChatMessage(role=message.role, content=message.content)
            for message in history
        ]
        tool_definitions = build_llm_tool_definitions(self._tools)
        started_at = utc_now()
        started = perf_counter()
        agent_run = AgentRun(
            conversation=conversation,
            user_message=user_message,
            status="running",
            goal=request.content,
            started_at=started_at,
        )
        self._session.add(agent_run)
        self._session.flush()

        executed_tool_calls: list[ToolCall] = []
        for step_index in range(request.max_steps):
            chat_request = ChatRequest(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=tool_definitions,
            )
            try:
                response = await provider.chat(chat_request)
                if not isinstance(response, LLMResponse):
                    raise TypeError("Provider returned an invalid response")
            except ProviderTimeoutError:
                return self._fail_run(
                    request=request,
                    conversation=conversation,
                    user_message=user_message,
                    agent_run=agent_run,
                    started=started,
                    tool_calls=tuple(executed_tool_calls),
                    error_message="Model request timed out",
                    model=request.model,
                )
            except Exception:
                return self._fail_run(
                    request=request,
                    conversation=conversation,
                    user_message=user_message,
                    agent_run=agent_run,
                    started=started,
                    tool_calls=tuple(executed_tool_calls),
                    error_message="Model request failed",
                    model=request.model,
                )
            if not response.tool_calls:
                return self._complete_run(
                    request=request,
                    response=response,
                    conversation=conversation,
                    user_message=user_message,
                    agent_run=agent_run,
                    started=started,
                    is_new_conversation=is_new_conversation,
                    tool_calls=tuple(executed_tool_calls),
                )
            if step_index == request.max_steps - 1:
                return self._fail_run(
                    request=request,
                    conversation=conversation,
                    user_message=user_message,
                    agent_run=agent_run,
                    started=started,
                    tool_calls=tuple(executed_tool_calls),
                    error_message=MAX_STEPS_ERROR,
                    model=response.model,
                )
            executed_ids = {
                call.tool_call_id for call in executed_tool_calls
            }
            if any(
                call.tool_call_id in executed_ids
                for call in response.tool_calls
            ):
                return self._fail_run(
                    request=request,
                    conversation=conversation,
                    user_message=user_message,
                    agent_run=agent_run,
                    started=started,
                    tool_calls=tuple(executed_tool_calls),
                    error_message="Model request failed",
                    model=response.model,
                )
            round_messages, round_tool_calls = (
                await self._execute_tool_round(
                    agent_run=agent_run,
                    response=response,
                )
            )
            executed_tool_calls.extend(round_tool_calls)
            messages.extend(round_messages)

        raise RuntimeError("unreachable Agent loop state")

    def _resolve_model_and_provider(
        self,
        request: SimpleAgentRequest,
    ) -> tuple[ModelInfo, BaseLLMProvider]:
        model_info = self._registry.get_model(
            request.provider,
            request.model,
        )
        if model_info is None:
            raise AgentModelNotFoundError(request.provider, request.model)
        if not model_info.supports_tools:
            raise AgentModelToolsUnsupportedError(
                request.provider,
                request.model,
            )
        provider = self._providers.get(request.provider)
        if provider is None:
            raise AgentProviderUnavailableError(request.provider)
        return model_info, provider

    async def _execute_tool_round(
        self,
        *,
        agent_run: AgentRun,
        response: LLMResponse,
    ) -> tuple[list[ChatMessage], tuple[ToolCall, ...]]:
        agent_run.status = "waiting_tool"
        self._session.flush()
        executed = [
            await self._record_tool_call(
                agent_run=agent_run,
                call=call,
            )
            for call in response.tool_calls
        ]
        tool_calls = tuple(row for row, _ in executed)
        results = [result for _, result in executed]
        assistant_tool_message = ChatMessage(
            role="assistant",
            content=response.content,
            tool_calls=response.tool_calls,
        )
        observations = [
            ChatMessage(
                role="tool",
                content=self._serialize_tool_result(result),
                tool_call_id=call.tool_call_id,
            )
            for call, result in zip(
                response.tool_calls,
                results,
                strict=True,
            )
        ]
        agent_run.status = "running"
        self._session.flush()
        return [assistant_tool_message, *observations], tool_calls

    async def _record_tool_call(
        self,
        *,
        agent_run: AgentRun,
        call: LLMToolCall,
    ) -> tuple[ToolCall, ToolResult]:
        row = ToolCall(
            agent_run=agent_run,
            conversation_id=agent_run.conversation_id,
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            arguments_json=deepcopy(call.arguments),
            status="running",
            started_at=utc_now(),
        )
        self._session.add(row)
        self._session.flush()
        started = perf_counter()
        execution = await self._execute_tool(call)
        result = execution.result
        row.result_json = result.model_dump(mode="json")
        row.status = execution.status
        row.error_message = None if result.success else result.error
        row.ended_at = utc_now()
        row.latency_ms = self._elapsed_ms(started)
        self._session.flush()
        return row, result

    async def _execute_tool(self, call: LLMToolCall) -> _ToolExecution:
        try:
            tool = self._tools.get_tool(call.tool_name)
        except ToolNotFoundError:
            return _ToolExecution(
                result=ToolResult(
                    tool_name=call.tool_name,
                    success=False,
                    error="Tool is not available",
                ),
                status="failed",
            )

        try:
            validated_arguments = validate_tool_arguments(
                tool,
                call.arguments,
            )
        except ToolArgumentValidationError as exc:
            return _ToolExecution(
                result=ToolResult(
                    tool_name=call.tool_name,
                    success=False,
                    error=str(exc),
                ),
                status="failed",
            )

        try:
            async with asyncio.timeout(tool.timeout_seconds):
                result = await tool.run(validated_arguments)
        except TimeoutError:
            return _ToolExecution(
                result=ToolResult(
                    tool_name=call.tool_name,
                    success=False,
                    error="Tool execution timed out",
                ),
                status="timeout",
            )
        except Exception:
            return _ToolExecution(
                result=ToolResult(
                    tool_name=call.tool_name,
                    success=False,
                    error="Tool execution failed",
                ),
                status="failed",
            )

        try:
            if result.tool_name != call.tool_name:
                raise ValueError("tool result name mismatch")
            json.dumps(
                result.model_dump(mode="python"),
                allow_nan=False,
            )
            return _ToolExecution(
                result=result,
                status="success" if result.success else "failed",
            )
        except Exception:
            return _ToolExecution(
                result=ToolResult(
                    tool_name=call.tool_name,
                    success=False,
                    error="Tool execution failed",
                ),
                status="failed",
            )

    def _serialize_tool_result(self, result: ToolResult) -> str:
        full_result = result.model_dump(mode="json")
        serialized = self._dump_json(full_result)
        if len(serialized) <= self._max_tool_observation_chars:
            return serialized

        compact_result = {
            "tool_name": result.tool_name,
            "success": result.success,
            "content": "",
            "data": None,
            "error": None if result.error is None else "",
            "metadata": {
                "observation_truncated": True,
                "original_characters": len(serialized),
            },
        }
        best = self._dump_json(compact_result)
        if result.error is not None:
            best = self._fit_text_field(
                compact_result,
                field_name="error",
                value=result.error,
                max_chars=MAX_COMPACT_ERROR_CHARS,
            )
        best = self._fit_text_field(
            compact_result,
            field_name="content",
            value=result.content,
            max_chars=len(result.content),
        )

        if len(best) > self._max_tool_observation_chars:
            raise ValueError("tool observation envelope exceeds configured limit")
        return best

    def _fit_text_field(
        self,
        payload: dict[str, object],
        *,
        field_name: str,
        value: str,
        max_chars: int,
    ) -> str:
        best_value = payload[field_name]
        best = self._dump_json(payload)
        low = 0
        high = min(len(value), max_chars)
        while low <= high:
            candidate_length = (low + high) // 2
            payload[field_name] = self._truncate_text(
                value,
                candidate_length,
            )
            candidate = self._dump_json(payload)
            if len(candidate) <= self._max_tool_observation_chars:
                best_value = payload[field_name]
                best = candidate
                low = candidate_length + 1
            else:
                high = candidate_length - 1
        payload[field_name] = best_value
        return best

    @staticmethod
    def _dump_json(value: object) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

    @staticmethod
    def _truncate_text(value: str, max_chars: int) -> str:
        if len(value) <= max_chars:
            return value
        if max_chars <= 0:
            return ""
        if max_chars == 1:
            return "…"
        return f"{value[: max_chars - 1]}…"

    def _complete_run(
        self,
        *,
        request: SimpleAgentRequest,
        response: LLMResponse,
        conversation: Conversation,
        user_message: Message,
        agent_run: AgentRun,
        started: float,
        is_new_conversation: bool,
        tool_calls: tuple[ToolCall, ...],
    ) -> SimpleAgentResult:
        if response.content is None or not response.content.strip():
            return self._fail_run(
                request=request,
                conversation=conversation,
                user_message=user_message,
                agent_run=agent_run,
                started=started,
                tool_calls=tool_calls,
                error_message=INCOMPLETE_ERROR,
                model=response.model,
            )

        assistant_message = self._conversations.append_message(
            MessageCreate(
                conversation_id=conversation.id,
                role="assistant",
                content=response.content,
                provider=request.provider,
                model=response.model,
            )
        )
        agent_run.status = "completed"
        agent_run.final_answer = response.content
        agent_run.error_message = None
        agent_run.ended_at = utc_now()
        agent_run.latency_ms = self._elapsed_ms(started)
        self._conversations.record_successful_turn(
            conversation,
            provider=request.provider,
            model=request.model,
            title_source=(
                request.content if is_new_conversation else None
            ),
        )
        self._session.flush()
        return SimpleAgentResult(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            agent_run=agent_run,
            tool_calls=tool_calls,
            provider=request.provider,
            model=response.model,
        )

    def _fail_run(
        self,
        *,
        request: SimpleAgentRequest,
        conversation: Conversation,
        user_message: Message,
        agent_run: AgentRun,
        started: float,
        tool_calls: tuple[ToolCall, ...],
        error_message: str,
        model: str,
    ) -> SimpleAgentResult:
        agent_run.status = "failed"
        agent_run.final_answer = None
        agent_run.error_message = error_message
        agent_run.ended_at = utc_now()
        agent_run.latency_ms = self._elapsed_ms(started)
        self._session.flush()
        return SimpleAgentResult(
            conversation=conversation,
            user_message=user_message,
            assistant_message=None,
            agent_run=agent_run,
            tool_calls=tool_calls,
            provider=request.provider,
            model=model,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, int((perf_counter() - started) * 1000))
