import asyncio
import logging
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Conversation, LLMCall, Message
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatMessage,
    ChatRequest,
    LLMProviderError,
    ProviderResponseError,
    TokenUsage,
)
from app.providers.llm.registry import ModelRegistry
from app.schemas.chat import ChatCompletionRequest
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService
from app.services.errors import (
    ChatModelNotFoundError,
    ChatProviderUnavailableError,
)
from app.services.llm_usage import (
    LLMCallMetrics,
    ProviderLatencyTimer,
    build_llm_call_metrics,
)


logger = logging.getLogger("app.llm")


def _log_llm_completed(
    request: ChatCompletionRequest,
    metrics: LLMCallMetrics,
) -> None:
    logger.info(
        "llm_call_completed",
        extra={
            "provider": request.provider,
            "model": request.model,
            "latency_ms": metrics.latency_ms,
            "outcome": "completed",
            "input_tokens": metrics.input_tokens,
            "output_tokens": metrics.output_tokens,
            "total_tokens": metrics.total_tokens,
            "estimated_cost": metrics.estimated_cost,
        },
    )


def _log_llm_not_completed(
    request: ChatCompletionRequest,
    *,
    event: str,
    outcome: str,
    latency_ms: int,
    exc: BaseException,
) -> None:
    logger.warning(
        event,
        extra={
            "provider": request.provider,
            "model": request.model,
            "latency_ms": latency_ms,
            "outcome": outcome,
            "error_code": (
                "provider_error"
                if isinstance(exc, LLMProviderError)
                else outcome
            ),
            "exception_type": exc.__class__.__name__,
        },
    )


@dataclass(frozen=True)
class ChatCompletionResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    llm_call: LLMCall
    provider: str
    model: str
    usage: TokenUsage | None


@dataclass(frozen=True)
class ChatStreamDelta:
    content: str


@dataclass(frozen=True)
class ChatStreamCompleted:
    result: ChatCompletionResult


class ChatService:
    def __init__(
        self,
        session: Session,
        *,
        registry: ModelRegistry,
        providers: Mapping[str, BaseLLMProvider],
    ) -> None:
        self._session = session
        self._registry = registry
        self._providers = providers
        self._conversations = ConversationService(session)

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        model_info = self._registry.get_model(request.provider, request.model)
        if model_info is None:
            raise ChatModelNotFoundError(request.provider, request.model)

        provider = self._providers.get(request.provider)
        if provider is None:
            raise ChatProviderUnavailableError(request.provider)

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
        provider_request = ChatRequest(
            messages=[
                ChatMessage(role=message.role, content=message.content)
                for message in history
            ],
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        timer = ProviderLatencyTimer()
        try:
            with timer.measure():
                response = await provider.chat(provider_request)
        except LLMProviderError as exc:
            _log_llm_not_completed(
                request,
                event="llm_call_failed",
                outcome="failed",
                latency_ms=timer.latency_ms,
                exc=exc,
            )
            self._session.rollback()
            raise

        metrics = build_llm_call_metrics(
            usage=response.usage,
            model_info=model_info,
            latency_ms=timer.latency_ms,
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
        llm_call = LLMCall(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            provider=request.provider,
            model=response.model,
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            total_tokens=metrics.total_tokens,
            estimated_cost=metrics.estimated_cost,
            latency_ms=metrics.latency_ms,
            status="completed",
        )
        self._session.add(llm_call)
        self._session.flush()
        self._conversations.record_successful_turn(
            conversation,
            provider=request.provider,
            model=request.model,
            title_source=request.content if is_new_conversation else None,
        )
        _log_llm_completed(request, metrics)

        return ChatCompletionResult(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            llm_call=llm_call,
            provider=request.provider,
            model=response.model,
            usage=response.usage,
        )

    async def stream_complete(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[ChatStreamDelta | ChatStreamCompleted]:
        committed = False
        call_started = False
        timer: ProviderLatencyTimer | None = None
        try:
            model_info = self._registry.get_model(request.provider, request.model)
            if model_info is None:
                raise ChatModelNotFoundError(request.provider, request.model)

            provider = self._providers.get(request.provider)
            if provider is None:
                raise ChatProviderUnavailableError(request.provider)

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
            provider_request = ChatRequest(
                messages=[
                    ChatMessage(role=message.role, content=message.content)
                    for message in history
                ],
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            content_parts: list[str] = []
            response_model = request.model
            usage: TokenUsage | None = None
            timer = ProviderLatencyTimer()
            call_started = True
            provider_stream = provider.stream_chat(provider_request)
            try:
                while True:
                    try:
                        with timer.measure():
                            chunk = await anext(provider_stream)
                    except StopAsyncIteration:
                        break

                    if chunk.model:
                        response_model = chunk.model
                    if chunk.usage is not None:
                        usage = chunk.usage
                    if chunk.content:
                        content_parts.append(chunk.content)
                        yield ChatStreamDelta(content=chunk.content)
            finally:
                close_stream = getattr(provider_stream, "aclose", None)
                if close_stream is not None:
                    await close_stream()

            assistant_content = "".join(content_parts)
            if not assistant_content:
                raise ProviderResponseError(
                    "Provider stream completed with empty content"
                )

            metrics = build_llm_call_metrics(
                usage=usage,
                model_info=model_info,
                latency_ms=timer.latency_ms,
            )

            assistant_message = self._conversations.append_message(
                MessageCreate(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=assistant_content,
                    provider=request.provider,
                    model=response_model,
                )
            )
            llm_call = LLMCall(
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                provider=request.provider,
                model=response_model,
                input_tokens=metrics.input_tokens,
                output_tokens=metrics.output_tokens,
                total_tokens=metrics.total_tokens,
                estimated_cost=metrics.estimated_cost,
                latency_ms=metrics.latency_ms,
                status="completed",
            )
            self._session.add(llm_call)
            self._session.flush()
            self._conversations.record_successful_turn(
                conversation,
                provider=request.provider,
                model=request.model,
                title_source=request.content if is_new_conversation else None,
            )
            self._session.commit()
            committed = True
            _log_llm_completed(request, metrics)

            yield ChatStreamCompleted(
                result=ChatCompletionResult(
                    conversation=conversation,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    llm_call=llm_call,
                    provider=request.provider,
                    model=response_model,
                    usage=usage,
                )
            )
        except (GeneratorExit, asyncio.CancelledError) as exc:
            if call_started and not committed and timer is not None:
                _log_llm_not_completed(
                    request,
                    event="llm_call_cancelled",
                    outcome="cancelled",
                    latency_ms=timer.latency_ms,
                    exc=exc,
                )
            raise
        except Exception as exc:
            if call_started and timer is not None:
                _log_llm_not_completed(
                    request,
                    event="llm_call_failed",
                    outcome="failed",
                    latency_ms=timer.latency_ms,
                    exc=exc,
                )
            raise
        finally:
            if not committed:
                self._session.rollback()
