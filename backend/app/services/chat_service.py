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
        if self._registry.get_model(request.provider, request.model) is None:
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

        try:
            response = await provider.chat(provider_request)
        except LLMProviderError:
            self._session.rollback()
            raise

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
        try:
            if self._registry.get_model(request.provider, request.model) is None:
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
            async for chunk in provider.stream_chat(provider_request):
                if chunk.model:
                    response_model = chunk.model
                if chunk.usage is not None:
                    usage = chunk.usage
                if chunk.content:
                    content_parts.append(chunk.content)
                    yield ChatStreamDelta(content=chunk.content)

            assistant_content = "".join(content_parts)
            if not assistant_content:
                raise ProviderResponseError(
                    "Provider stream completed with empty content"
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
        finally:
            if not committed:
                self._session.rollback()
