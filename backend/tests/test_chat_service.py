import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import Conversation, LLMCall, Message
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatRequest,
    LLMResponse,
    ProviderRequestError,
    TokenUsage,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.schemas.chat import ChatCompletionRequest
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.errors import (
    ChatModelNotFoundError,
    ChatProviderUnavailableError,
)


class MockProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            id="response-1",
            model="resolved-model",
            content="Assistant answer",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=4, output_tokens=2, total_tokens=6),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise NotImplementedError


class FailingProvider(MockProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        raise ProviderRequestError("mock provider failed", status_code=503)


def create_test_session(tmp_path: Path) -> tuple[Session, Engine]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'chat.db'}")
    Base.metadata.create_all(engine)
    return Session(engine), engine


def create_registry() -> ModelRegistry:
    return ModelRegistry(
        [
            ModelInfo(
                provider="openai_compatible",
                model="example-model",
                display_name="Example Model",
                supports_streaming=True,
            )
        ]
    )


def test_chat_service_creates_conversation_messages_and_llm_call(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = MockProvider()
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": provider},
    )

    result = asyncio.run(
        service.complete(
            ChatCompletionRequest(
                provider="openai_compatible",
                model="example-model",
                content="Hello",
                temperature=0.2,
                max_tokens=50,
            )
        )
    )

    assert result.user_message.content == "Hello"
    assert result.assistant_message.content == "Assistant answer"
    assert result.provider == "openai_compatible"
    assert result.model == "resolved-model"
    assert result.usage == TokenUsage(
        input_tokens=4,
        output_tokens=2,
        total_tokens=6,
    )
    assert [(message.role, message.content) for message in provider.requests[0].messages] == [
        ("user", "Hello")
    ]
    assert provider.requests[0].temperature == 0.2
    assert provider.requests[0].max_tokens == 50

    messages = session.scalars(select(Message).order_by(Message.created_at)).all()
    llm_calls = session.scalars(select(LLMCall)).all()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert llm_calls == [result.llm_call]
    assert result.llm_call.message_id == result.assistant_message.id
    assert result.llm_call.status == "completed"
    assert result.llm_call.input_tokens is None
    assert result.llm_call.output_tokens is None
    assert result.llm_call.total_tokens is None

    session.close()
    engine.dispose()


def test_chat_service_sends_existing_history_with_new_user_message(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversations = ConversationService(session)
    conversation = conversations.create_conversation(ConversationCreate())
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
    provider = MockProvider()
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": provider},
    )

    result = asyncio.run(
        service.complete(
            ChatCompletionRequest(
                conversation_id=conversation.id,
                provider="openai_compatible",
                model="example-model",
                content="Follow-up question",
            )
        )
    )

    assert result.conversation.id == conversation.id
    assert [message.content for message in provider.requests[0].messages] == [
        "Earlier question",
        "Earlier answer",
        "Follow-up question",
    ]

    session.close()
    engine.dispose()


@pytest.mark.parametrize("content", ["", "   "])
def test_chat_completion_request_rejects_empty_content(content: str) -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            provider="openai_compatible",
            model="example-model",
            content=content,
        )


def test_chat_service_rejects_unknown_model_before_provider_call(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = MockProvider()
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": provider},
    )

    with pytest.raises(
        ChatModelNotFoundError,
        match="Model not found: openai_compatible/missing-model",
    ):
        asyncio.run(
            service.complete(
                ChatCompletionRequest(
                    provider="openai_compatible",
                    model="missing-model",
                    content="Hello",
                )
            )
        )

    assert provider.requests == []
    assert session.scalars(select(Message)).all() == []

    session.close()
    engine.dispose()


def test_chat_service_rejects_unavailable_provider(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ChatService(
        session,
        registry=create_registry(),
        providers={},
    )

    with pytest.raises(
        ChatProviderUnavailableError,
        match="Provider is not configured: openai_compatible",
    ):
        asyncio.run(
            service.complete(
                ChatCompletionRequest(
                    provider="openai_compatible",
                    model="example-model",
                    content="Hello",
                )
            )
        )

    session.close()
    engine.dispose()


def test_chat_service_rolls_back_new_records_when_provider_fails(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = FailingProvider()
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": provider},
    )

    with pytest.raises(ProviderRequestError, match="mock provider failed"):
        asyncio.run(
            service.complete(
                ChatCompletionRequest(
                    provider="openai_compatible",
                    model="example-model",
                    content="Hello",
                )
            )
        )

    assert session.scalars(select(Message)).all() == []
    assert session.scalars(select(LLMCall)).all() == []
    assert session.scalars(select(Conversation)).all() == []

    session.close()
    engine.dispose()
