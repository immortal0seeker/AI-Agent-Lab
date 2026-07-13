import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
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
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderTimeoutError,
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


class TimeoutProvider(MockProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        raise ProviderTimeoutError(
            "private timeout diagnostic",
            status_code=504,
        )


class RateLimitedStreamingProvider(MockProvider):
    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        self.requests.append(request)
        if False:
            yield ChatChunk()
        raise ProviderRateLimitError(
            "private rate-limit diagnostic",
            status_code=429,
        )


def create_registry() -> ModelRegistry:
    return ModelRegistry(
        [
            ModelInfo(
                provider="openai_compatible",
                model="example-model",
                display_name="Example Model",
                supports_streaming=True,
                input_price_per_1m=Decimal("0.50"),
                output_price_per_1m=Decimal("1.50"),
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


def test_openapi_exposes_chat_catalog_and_conversation_routes(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}" in paths
    assert "/api/v1/conversations/{conversation_id}/messages" in paths
    assert "/api/v1/models" in paths
    assert "/api/v1/chat/completions" in paths
    assert "/api/v1/chat/stream" in paths


def test_server_generates_request_id_and_ignores_client_value(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "client-controlled"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "client-controlled"
    UUID(response.headers["x-request-id"])


def test_models_api_returns_registry_order(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "provider": "openai_compatible",
            "model": "example-model",
            "display_name": "Example Model",
            "supports_streaming": True,
            "supports_tools": False,
            "supports_json": False,
            "input_price_per_1m": "0.50",
            "output_price_per_1m": "1.50",
        }
    ]


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


def test_conversation_api_uses_default_title(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.post("/api/v1/conversations", json={})

    assert response.status_code == 201
    assert response.json()["title"] == "New conversation"
    assert response.json()["default_provider"] is None
    assert response.json()["default_model"] is None


def test_conversation_api_rejects_malformed_id_with_unified_error(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    response = client.get("/api/v1/conversations/not-a-uuid")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_conversation_api_returns_404_for_unknown_conversation(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context
    missing_id = uuid4()

    response = client.get(f"/api/v1/conversations/{missing_id}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "conversation_not_found",
            "message": "Conversation not found",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_conversation_api_lists_recent_conversations_and_messages(
    api_context: Any,
) -> None:
    client, session_factory, _, _ = api_context
    with session_factory() as session:
        older = Conversation(
            title="Older",
            updated_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        newer = Conversation(
            title="Newer",
            updated_at=datetime(2026, 1, 2, 12, 0, 0),
        )
        session.add_all([older, newer])
        session.flush()
        session.add_all(
            [
                Message(
                    conversation_id=newer.id,
                    role="assistant",
                    content="Second",
                    created_at=datetime(2026, 1, 2, 12, 0, 2),
                ),
                Message(
                    conversation_id=newer.id,
                    role="user",
                    content="First",
                    created_at=datetime(2026, 1, 2, 12, 0, 1),
                ),
            ]
        )
        session.commit()
        older_id = str(older.id)
        newer_id = str(newer.id)

    conversations = client.get("/api/v1/conversations")
    messages = client.get(f"/api/v1/conversations/{newer_id}/messages")

    assert conversations.status_code == 200
    assert [item["id"] for item in conversations.json()] == [
        newer_id,
        older_id,
    ]
    assert messages.status_code == 200
    assert [item["content"] for item in messages.json()] == [
        "First",
        "Second",
    ]


def test_conversation_messages_api_returns_404_for_unknown_conversation(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context
    missing_id = uuid4()

    response = client.get(f"/api/v1/conversations/{missing_id}/messages")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "conversation_not_found",
            "message": "Conversation not found",
            "request_id": response.headers["x-request-id"],
        }
    }


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
        llm_call = session.scalar(select(LLMCall))
        assert llm_call is not None
        assert llm_call.input_tokens == 5
        assert llm_call.output_tokens == 3
        assert llm_call.total_tokens == 8
        assert llm_call.estimated_cost == Decimal("0.00000700")
        assert llm_call.latency_ms is not None


def test_chat_logs_request_and_model_metadata_without_content(
    api_context: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, _, _, _ = api_context
    sensitive_content = "complete secret prompt for log safety"

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "provider": "openai_compatible",
                "model": "example-model",
                "content": sensitive_content,
            },
        )

    request_id = response.headers["x-request-id"]
    assert any(
        record.getMessage() == "request_completed"
        and record.method == "POST"
        and record.path == "/api/v1/chat/completions"
        and record.status_code == 200
        and record.request_id == request_id
        for record in caplog.records
    )
    assert any(
        record.getMessage() == "llm_call_completed"
        and record.provider == "openai_compatible"
        and record.model == "example-model"
        and record.latency_ms >= 0
        and record.request_id == request_id
        for record in caplog.records
    )
    assert sensitive_content not in caplog.text
    assert not any(
        record.name in {"httpx", "httpcore"}
        and record.levelno < logging.WARNING
        for record in caplog.records
    )


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
        "error": {
            "code": "model_not_found",
            "message": "The requested model is not available",
            "request_id": response.headers["x-request-id"],
        }
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
        "error": {
            "code": "provider_unavailable",
            "message": "The requested provider is unavailable",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_chat_api_returns_safe_error_for_provider_configuration(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    def raise_provider_configuration_error() -> dict[str, BaseLLMProvider]:
        raise ProviderConfigurationError(
            "fake local key must not be returned"
        )

    app.dependency_overrides[get_llm_providers] = (
        raise_provider_configuration_error
    )

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
        "error": {
            "code": "provider_unavailable",
            "message": "The model provider is not configured",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "fake local key" not in response.text


def test_chat_api_returns_502_and_rolls_back_provider_failure(
    api_context: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = FailingProvider()

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "provider": "openai_compatible",
                "model": "example-model",
                "content": "Hello",
            },
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "provider_unknown_error",
            "message": "The model provider request failed",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "mock upstream failed" not in response.text
    assert "mock upstream failed" not in caplog.text
    assert any(
        record.getMessage() == "llm_call_failed"
        and record.provider == "openai_compatible"
        and record.model == "example-model"
        and record.latency_ms >= 0
        and record.request_id == response.headers["x-request-id"]
        for record in caplog.records
    )
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0


def test_chat_api_maps_timeout_and_rolls_back(api_context: Any) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = TimeoutProvider()

    response = client.post(
        "/api/v1/chat/completions",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello",
        },
    )

    assert response.status_code == 504
    assert response.json() == {
        "error": {
            "code": "provider_timeout",
            "message": "The model provider timed out",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private timeout diagnostic" not in response.text
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
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_database_error_returns_safe_unified_response(
    api_context: Any,
) -> None:
    client, _, _, _ = api_context

    async def raise_database_error() -> AsyncIterator[Session]:
        raise SQLAlchemyError(
            "simulated database failure with private detail"
        )
        if False:
            yield Session()

    app.dependency_overrides[get_db_session] = raise_database_error

    response = client.get("/api/v1/conversations")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_error",
            "message": "The database operation failed",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private detail" not in response.text


def test_unknown_route_uses_unified_http_error(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Resource not found",
            "request_id": response.headers["x-request-id"],
        }
    }


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
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "The request could not be completed",
            "request_id": response.headers["x-request-id"],
        }
    }


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
        llm_call = session.scalar(select(LLMCall))
        assert llm_call is not None
        assert llm_call.input_tokens == 6
        assert llm_call.output_tokens == 2
        assert llm_call.total_tokens == 8
        assert llm_call.estimated_cost == Decimal("0.00000600")
        assert llm_call.latency_ms is not None


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
        (
            "error",
            {
                "error": {
                    "code": "provider_unknown_error",
                    "message": "The model provider request failed",
                    "request_id": response.headers["x-request-id"],
                }
            },
        ),
    ]
    assert "mock stream failed" not in response.text
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0


def test_stream_chat_api_maps_rate_limit_and_rolls_back(
    api_context: Any,
) -> None:
    client, session_factory, _, providers = api_context
    providers["openai_compatible"] = RateLimitedStreamingProvider()

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "provider": "openai_compatible",
            "model": "example-model",
            "content": "Hello stream",
        },
    )

    assert response.status_code == 200
    assert parse_sse_events(response.text) == [
        (
            "error",
            {
                "error": {
                    "code": "provider_rate_limit",
                    "message": "The model provider rate limit was exceeded",
                    "request_id": response.headers["x-request-id"],
                }
            },
        )
    ]
    assert "private rate-limit diagnostic" not in response.text
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0


def test_stream_database_error_emits_safe_error_and_rolls_back(
    api_context: Any,
) -> None:
    client, session_factory, _, _ = api_context

    class FailingCommitSession(Session):
        def commit(self) -> None:
            raise SQLAlchemyError(
                "simulated stream database failure with private detail"
            )

    failing_session_factory = sessionmaker(
        bind=session_factory.kw["bind"],
        class_=FailingCommitSession,
        expire_on_commit=False,
    )
    app.dependency_overrides[get_session_factory] = (
        lambda: failing_session_factory
    )

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
    assert [name for name, _ in events] == ["delta", "delta", "error"]
    assert events[-1] == (
        "error",
        {
            "error": {
                "code": "database_error",
                "message": "The database operation failed",
                "request_id": response.headers["x-request-id"],
            }
        },
    )
    assert "private detail" not in response.text
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
