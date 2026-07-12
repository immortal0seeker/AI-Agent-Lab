import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_db_session,
    get_llm_providers,
    get_model_registry,
    get_session_factory,
)
from app.db.base import Base
from app.db.session import create_db_engine
from app.main import app
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


class MockProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            id="api-response",
            model="resolved-model",
            content="API assistant answer",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=5, output_tokens=3, total_tokens=8),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        yield ChatChunk(
            id="api-stream",
            model="resolved-stream-model",
            content="API streamed ",
        )
        yield ChatChunk(
            id="api-stream",
            model="resolved-stream-model",
            content="answer",
        )
        yield ChatChunk(
            id="api-stream",
            model="resolved-stream-model",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=6, output_tokens=2, total_tokens=8),
        )


class FailingProvider(MockProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        raise ProviderRequestError("mock upstream failed", status_code=503)


class FailingStreamingProvider(MockProvider):
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        yield ChatChunk(content="partial")
        raise ProviderRequestError("mock stream failed", status_code=503)


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


@pytest.fixture
def api_context(
    tmp_path: Path,
) -> Any:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider = MockProvider()
    providers: dict[str, BaseLLMProvider] = {
        "openai_compatible": provider,
    }
    registry = create_registry()

    async def override_db_session() -> AsyncIterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_llm_providers] = lambda: providers
    app.dependency_overrides[get_model_registry] = lambda: registry

    with TestClient(app) as client:
        yield client, session_factory, provider, providers

    app.dependency_overrides.clear()
    engine.dispose()


def test_openapi_exposes_conversation_and_non_streaming_chat_routes(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}" in paths
    assert "/api/v1/chat/completions" in paths
    assert "/api/v1/chat/stream" in paths


def test_conversation_api_creates_and_gets_conversation(api_context: Any) -> None:
    client, _, _, _ = api_context

    created = client.post(
        "/api/v1/conversations",
        json={
            "title": "API conversation",
            "default_provider": "openai_compatible",
            "default_model": "example-model",
        },
    )
    loaded = client.get(
        f"/api/v1/conversations/{created.json()['id']}"
    )

    assert created.status_code == 201
    assert loaded.status_code == 200
    assert loaded.json() == created.json()


def test_conversation_api_returns_404_for_unknown_conversation(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context
    missing_id = uuid4()

    response = client.get(f"/api/v1/conversations/{missing_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Conversation not found: {missing_id}"}


def test_chat_api_returns_messages_usage_and_persists_records(
    api_context: Any,
) -> None:
    client, session_factory, provider, _ = api_context

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello API",
            "temperature": 0.3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_message"]["content"] == "Hello API"
    assert body["assistant_message"]["content"] == "API assistant answer"
    assert body["provider"] == "openai_compatible"
    assert body["model"] == "resolved-model"
    assert body["usage"] == {
        "input_tokens": 5,
        "output_tokens": 3,
        "total_tokens": 8,
    }
    assert provider.requests[0].messages[-1].content == "Hello API"

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 1
        assert session.scalar(select(func.count()).select_from(Message)) == 2
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 1


def test_chat_api_returns_400_for_unknown_model(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "missing-model",
            "content": "Hello",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Model not found: openai_compatible/missing-model"
    }


def test_chat_api_returns_503_for_unavailable_provider(api_context: Any) -> None:
    client, _, _, providers = api_context
    providers.clear()

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Provider is not configured: openai_compatible"
    }


def test_chat_api_returns_502_and_rolls_back_provider_failure(
    api_context: Any,
) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = FailingProvider()

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello",
        },
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "mock upstream failed"}
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0


def test_chat_api_rejects_blank_content(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "   ",
        },
    )

    assert response.status_code == 422


def test_transaction_finalization_failure_does_not_return_success(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'commit-failure.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    async def fail_after_yield() -> AsyncIterator[Session]:
        session = session_factory()
        try:
            yield session
            raise RuntimeError("simulated commit failure")
        finally:
            session.rollback()
            session.close()

    app.dependency_overrides[get_db_session] = fail_after_yield
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/conversations", json={})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 500


def parse_sse_events(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        event_name = next(line[7:] for line in lines if line.startswith("event: "))
        data = next(line[6:] for line in lines if line.startswith("data: "))
        events.append((event_name, json.loads(data)))
    return events


def test_stream_chat_api_emits_deltas_done_and_persists(api_context: Any) -> None:
    client, session_factory, provider, _ = api_context

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello stream",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse_events(response.text)
    assert [name for name, _ in events] == ["delta", "delta", "done"]
    assert [data["content"] for name, data in events if name == "delta"] == [
        "API streamed ",
        "answer",
    ]
    done = events[-1][1]
    assert done["assistant_message"]["content"] == "API streamed answer"
    assert done["model"] == "resolved-stream-model"
    assert done["usage"] == {
        "input_tokens": 6,
        "output_tokens": 2,
        "total_tokens": 8,
    }
    assert provider.requests[-1].messages[-1].content == "Hello stream"

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 1
        assert session.scalar(select(func.count()).select_from(Message)) == 2
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 1


def test_stream_chat_api_emits_error_and_rolls_back(api_context: Any) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = FailingStreamingProvider()

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello stream",
        },
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert events == [
        ("delta", {"content": "partial"}),
        ("error", {"message": "mock stream failed"}),
    ]
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
