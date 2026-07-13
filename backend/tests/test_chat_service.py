import asyncio
import logging
from collections.abc import AsyncIterator
from decimal import Decimal
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
    ProviderResponseError,
    TokenUsage,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.schemas.chat import ChatCompletionRequest
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.chat_service import (
    ChatService,
    ChatStreamCompleted,
    ChatStreamDelta,
)
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


class StreamingProvider(MockProvider):
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        yield ChatChunk(
            id="stream-1",
            model="resolved-stream-model",
            content="Streamed ",
        )
        yield ChatChunk(
            id="stream-1",
            model="resolved-stream-model",
            content="answer",
        )
        yield ChatChunk(
            id="stream-1",
            model="resolved-stream-model",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=7, output_tokens=2, total_tokens=9),
        )


class FailingStreamingProvider(MockProvider):
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        yield ChatChunk(content="partial")
        raise ProviderRequestError("mock stream failed", status_code=503)


class EmptyStreamingProvider(MockProvider):
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        if False:
            yield ChatChunk()


def create_test_session(tmp_path: Path) -> tuple[Session, Engine]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'chat.db'}")
    Base.metadata.create_all(engine)
    return Session(engine), engine


def create_registry(
    *,
    input_price_per_1m: Decimal | None = Decimal("0.50"),
    output_price_per_1m: Decimal | None = Decimal("1.50"),
) -> ModelRegistry:
    return ModelRegistry(
        [
            ModelInfo(
                provider="openai_compatible",
                model="example-model",
                display_name="Example Model",
                supports_streaming=True,
                input_price_per_1m=input_price_per_1m,
                output_price_per_1m=output_price_per_1m,
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
    assert result.llm_call.input_tokens == 4
    assert result.llm_call.output_tokens == 2
    assert result.llm_call.total_tokens == 6
    assert result.llm_call.estimated_cost == Decimal("0.00000500")
    assert result.llm_call.latency_ms is not None
    assert result.llm_call.latency_ms >= 0
    assert result.conversation.title == "Hello"
    assert result.conversation.default_provider == "openai_compatible"
    assert result.conversation.default_model == "example-model"
    session.close()
    engine.dispose()


def test_chat_service_keeps_cost_null_when_registry_price_is_unknown(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = ChatService(
        session,
        registry=create_registry(output_price_per_1m=None),
        providers={"openai_compatible": MockProvider()},
    )

    result = asyncio.run(
        service.complete(
            ChatCompletionRequest(
                provider="openai_compatible",
                model="example-model",
                content="Hello",
            )
        )
    )

    assert result.llm_call.input_tokens == 4
    assert result.llm_call.output_tokens == 2
    assert result.llm_call.total_tokens == 6
    assert result.llm_call.estimated_cost is None

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
    assert conversation.default_provider == "openai_compatible"
    assert conversation.default_model == "example-model"

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


def test_chat_service_rolls_back_existing_conversation_metadata_on_failure(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversations = ConversationService(session)
    conversation = conversations.create_conversation(
        ConversationCreate(
            title="Existing title",
            default_provider="provider-before",
            default_model="model-before",
        )
    )
    session.commit()
    conversation_id = conversation.id
    previous_updated_at = conversation.updated_at
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": FailingProvider()},
    )

    with pytest.raises(ProviderRequestError, match="mock provider failed"):
        asyncio.run(
            service.complete(
                ChatCompletionRequest(
                    conversation_id=conversation_id,
                    provider="openai_compatible",
                    model="example-model",
                    content="Failed follow-up",
                )
            )
        )

    session.expire_all()
    persisted = session.get(Conversation, conversation_id)
    assert persisted is not None
    assert persisted.title == "Existing title"
    assert persisted.default_provider == "provider-before"
    assert persisted.default_model == "model-before"
    assert persisted.updated_at == previous_updated_at

    session.close()
    engine.dispose()


def test_stream_chat_yields_deltas_and_commits_completed_result(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    provider = StreamingProvider()
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": provider},
    )

    async def collect_events() -> list[ChatStreamDelta | ChatStreamCompleted]:
        return [
            event
            async for event in service.stream_complete(
                ChatCompletionRequest(
                    provider="openai_compatible",
                    model="example-model",
                    content="Stream this",
                )
            )
        ]

    events = asyncio.run(collect_events())

    assert [event.content for event in events if isinstance(event, ChatStreamDelta)] == [
        "Streamed ",
        "answer",
    ]
    completed = events[-1]
    assert isinstance(completed, ChatStreamCompleted)
    assert completed.result.assistant_message.content == "Streamed answer"
    assert completed.result.model == "resolved-stream-model"
    assert completed.result.usage == TokenUsage(
        input_tokens=7,
        output_tokens=2,
        total_tokens=9,
    )
    assert completed.result.llm_call.input_tokens == 7
    assert completed.result.llm_call.output_tokens == 2
    assert completed.result.llm_call.total_tokens == 9
    assert completed.result.llm_call.estimated_cost == Decimal("0.00000650")
    assert completed.result.llm_call.latency_ms is not None
    assert completed.result.llm_call.latency_ms >= 0
    assert completed.result.conversation.title == "Stream this"
    assert completed.result.conversation.default_provider == "openai_compatible"
    assert completed.result.conversation.default_model == "example-model"

    with Session(engine) as verification_session:
        assert len(verification_session.scalars(select(Message)).all()) == 2
        assert len(verification_session.scalars(select(LLMCall)).all()) == 1

    session.close()
    engine.dispose()


def test_stream_chat_rolls_back_when_provider_fails(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": FailingStreamingProvider()},
    )

    async def collect_events() -> None:
        async for _ in service.stream_complete(
            ChatCompletionRequest(
                provider="openai_compatible",
                model="example-model",
                content="Stream this",
            )
        ):
            pass

    with pytest.raises(ProviderRequestError, match="mock stream failed"):
        asyncio.run(collect_events())

    with Session(engine) as verification_session:
        assert verification_session.scalars(select(Conversation)).all() == []
        assert verification_session.scalars(select(Message)).all() == []
        assert verification_session.scalars(select(LLMCall)).all() == []

    session.close()
    engine.dispose()


def test_stream_chat_rejects_empty_provider_stream(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": EmptyStreamingProvider()},
    )

    async def collect_events() -> None:
        async for _ in service.stream_complete(
            ChatCompletionRequest(
                provider="openai_compatible",
                model="example-model",
                content="Stream this",
            )
        ):
            pass

    with pytest.raises(ProviderResponseError, match="empty content"):
        asyncio.run(collect_events())

    session.close()
    engine.dispose()


def test_stream_chat_rolls_back_when_consumer_stops_early(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = ChatService(
        session,
        registry=create_registry(),
        providers={"openai_compatible": StreamingProvider()},
    )

    async def receive_one_then_stop() -> ChatStreamDelta | ChatStreamCompleted:
        stream = service.stream_complete(
            ChatCompletionRequest(
                provider="openai_compatible",
                model="example-model",
                content="Stream this",
            )
        )
        first = await anext(stream)
        await stream.aclose()
        return first

    with caplog.at_level(logging.INFO):
        first = asyncio.run(receive_one_then_stop())

    assert isinstance(first, ChatStreamDelta)
    assert first.content == "Streamed "
    with Session(engine) as verification_session:
        assert verification_session.scalars(select(Conversation)).all() == []
        assert verification_session.scalars(select(Message)).all() == []
        assert verification_session.scalars(select(LLMCall)).all() == []
    assert any(
        record.getMessage() == "llm_call_cancelled"
        and record.provider == "openai_compatible"
        and record.model == "example-model"
        and record.latency_ms >= 0
        for record in caplog.records
    )

    session.close()
    engine.dispose()
