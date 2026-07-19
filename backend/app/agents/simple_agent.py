import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Annotated
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
    AgentLoopIncompleteError,
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
    LLMToolDefinition,
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


class SimpleAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conversation_id: UUID | None = None
    provider: NonEmptyIdentifier = Field(max_length=100)
    model: NonEmptyIdentifier = Field(max_length=255)
    content: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)

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
    assistant_message: Message
    agent_run: AgentRun
    tool_calls: tuple[ToolCall, ...]
    provider: str
    model: str


class SimpleAgentService:
    def __init__(
        self,
        session: Session,
        *,
        registry: ModelRegistry,
        providers: Mapping[str, BaseLLMProvider],
        tools: ToolRegistry,
    ) -> None:
        self._session = session
        self._registry = registry
        self._providers = providers
        self._tools = tools
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

        response = await provider.chat(
            ChatRequest(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=tool_definitions,
            )
        )
        if response.tool_calls:
            return await self._run_tool_round(
                request=request,
                provider=provider,
                first_response=response,
                messages=messages,
                tool_definitions=tool_definitions,
                conversation=conversation,
                user_message=user_message,
                agent_run=agent_run,
                started=started,
                is_new_conversation=is_new_conversation,
            )
        return self._complete_run(
            request=request,
            response=response,
            conversation=conversation,
            user_message=user_message,
            agent_run=agent_run,
            started=started,
            is_new_conversation=is_new_conversation,
            tool_calls=(),
        )

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

    async def _run_tool_round(
        self,
        *,
        request: SimpleAgentRequest,
        provider: BaseLLMProvider,
        first_response: LLMResponse,
        messages: list[ChatMessage],
        tool_definitions: tuple[LLMToolDefinition, ...],
        conversation: Conversation,
        user_message: Message,
        agent_run: AgentRun,
        started: float,
        is_new_conversation: bool,
    ) -> SimpleAgentResult:
        agent_run.status = "waiting_tool"
        self._session.flush()
        executed = [
            await self._record_tool_call(
                agent_run=agent_run,
                call=call,
            )
            for call in first_response.tool_calls
        ]
        tool_calls = tuple(row for row, _ in executed)
        results = [result for _, result in executed]
        assistant_tool_message = ChatMessage(
            role="assistant",
            content=first_response.content,
            tool_calls=first_response.tool_calls,
        )
        observations = [
            ChatMessage(
                role="tool",
                content=self._serialize_tool_result(result),
                tool_call_id=call.tool_call_id,
            )
            for call, result in zip(
                first_response.tool_calls,
                results,
                strict=True,
            )
        ]
        agent_run.status = "running"
        self._session.flush()
        response = await provider.chat(
            ChatRequest(
                messages=[
                    *messages,
                    assistant_tool_message,
                    *observations,
                ],
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=tool_definitions,
            )
        )
        if response.tool_calls:
            self._fail_run(agent_run, started=started)
            raise AgentLoopIncompleteError
        return self._complete_run(
            request=request,
            response=response,
            conversation=conversation,
            user_message=user_message,
            agent_run=agent_run,
            started=started,
            is_new_conversation=is_new_conversation,
            tool_calls=tool_calls,
        )

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
        result = await self._execute_tool(call)
        row.result_json = result.model_dump(mode="json")
        row.status = "success" if result.success else "failed"
        row.error_message = None if result.success else result.error
        row.ended_at = utc_now()
        row.latency_ms = self._elapsed_ms(started)
        self._session.flush()
        return row, result

    async def _execute_tool(self, call: LLMToolCall) -> ToolResult:
        try:
            tool = self._tools.get_tool(call.tool_name)
        except ToolNotFoundError:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error="Tool is not available",
            )

        try:
            validated_arguments = validate_tool_arguments(
                tool,
                call.arguments,
            )
        except ToolArgumentValidationError as exc:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error=str(exc),
            )

        try:
            result = await tool.run(validated_arguments)
            if result.tool_name != call.tool_name:
                raise ValueError("tool result name mismatch")
            json.dumps(
                result.model_dump(mode="python"),
                allow_nan=False,
            )
            return result
        except Exception:
            return ToolResult(
                tool_name=call.tool_name,
                success=False,
                error="Tool execution failed",
            )

    @staticmethod
    def _serialize_tool_result(result: ToolResult) -> str:
        return json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

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
            self._fail_run(agent_run, started=started)
            raise AgentLoopIncompleteError

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

    def _fail_run(self, agent_run: AgentRun, *, started: float) -> None:
        agent_run.status = "failed"
        agent_run.final_answer = None
        agent_run.error_message = "Agent did not produce a final answer"
        agent_run.ended_at = utc_now()
        agent_run.latency_ms = self._elapsed_ms(started)
        self._session.flush()

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, int((perf_counter() - started) * 1000))
