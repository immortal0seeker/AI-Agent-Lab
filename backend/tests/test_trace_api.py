from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_db_session,
    get_llm_providers,
    get_trace_query_service,
    get_vector_store,
)
from app.db.base import Base
from app.db.session import create_db_engine
from app.main import app
from app.models import RagRetrievalCandidate, RagRetrievalRun, TraceRun, TraceStep


TRACE_ID = UUID(int=100)
RETRIEVAL_ID = UUID(int=200)
CANDIDATE_ID = UUID(int=300)
CREATED_AT = datetime(2026, 8, 9, 12, 0, 0)


@pytest.fixture
def trace_api_context(tmp_path: Path) -> Iterator[tuple[TestClient, Any, list[str]]]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'trace-api.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    dependency_calls: list[str] = []

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

    def unexpected_llm_dependency() -> object:
        dependency_calls.append("llm")
        raise AssertionError("Trace API must not initialize LLM providers")

    def unexpected_vector_dependency() -> object:
        dependency_calls.append("vector")
        raise AssertionError("Trace API must not initialize the vector store")

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_llm_providers] = unexpected_llm_dependency
    app.dependency_overrides[get_vector_store] = unexpected_vector_dependency

    with TestClient(app) as client:
        yield client, factory, dependency_calls

    app.dependency_overrides.clear()
    engine.dispose()


def seed_trace(factory: Any) -> None:
    with factory() as session:
        trace = TraceRun(
            id=TRACE_ID,
            run_type="rag_chat",
            status="completed",
            title="Architecture answer",
            input_text="Where is the design?",
            output_text="In the architecture document.",
            provider="mock",
            model="mock-chat",
            total_input_tokens=7,
            total_output_tokens=5,
            total_tokens=12,
            estimated_cost=Decimal("0.00000700"),
            latency_ms=18,
            metadata_json={"prompt_version": "naive-rag-v1"},
            started_at=CREATED_AT,
            ended_at=CREATED_AT,
            created_at=CREATED_AT,
        )
        trace.steps.append(
            TraceStep(
                id=UUID(int=110),
                step_index=1,
                step_type="rag_retrieve",
                name="Retrieve knowledge base",
                status="completed",
                input_json={"top_k": 5},
                output_json={"retrieval_run_id": str(RETRIEVAL_ID)},
                latency_ms=12,
                started_at=CREATED_AT,
                ended_at=CREATED_AT,
                created_at=CREATED_AT,
            )
        )
        retrieval = RagRetrievalRun(
            id=RETRIEVAL_ID,
            knowledge_base_id=UUID(int=210),
            strategy_name="naive_vector",
            original_query="Where is the design?",
            top_k=5,
            candidate_count=1,
            selected_count=1,
            score_threshold=0.5,
            latency_ms=12,
            metadata_filter_json={"embedding_model": "mock-embedding"},
            strategy_config_json={},
            created_at=CREATED_AT,
        )
        retrieval.candidates.append(
            RagRetrievalCandidate(
                id=CANDIDATE_ID,
                document_id=UUID(int=310),
                chunk_id=UUID(int=320),
                rank=1,
                final_rank=1,
                source="dense",
                dense_score=0.91,
                selected=True,
                content_preview="Architecture source",
                metadata_json={"filename": "architecture.md"},
                created_at=CREATED_AT,
            )
        )
        trace.retrieval_runs.append(retrieval)
        session.add(trace)
        session.commit()


def test_trace_api_paths_are_published(trace_api_context: Any) -> None:
    client, _, _ = trace_api_context

    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/traces" in paths
    assert "/api/v1/traces/{trace_run_id}" in paths


def test_trace_api_reads_without_runtime_provider_dependencies(
    trace_api_context: Any,
) -> None:
    client, _, dependency_calls = trace_api_context

    response = client.get("/api/v1/traces?limit=25")

    assert response.status_code == 200
    assert response.json() == []
    assert dependency_calls == []


def test_trace_api_lists_and_returns_nested_detail(trace_api_context: Any) -> None:
    client, factory, _ = trace_api_context
    seed_trace(factory)

    list_response = client.get("/api/v1/traces")
    detail_response = client.get(f"/api/v1/traces/{TRACE_ID}")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": str(TRACE_ID),
            "run_type": "rag_chat",
            "status": "completed",
            "title": "Architecture answer",
            "input_preview": "Where is the design?",
            "conversation_id": None,
            "agent_run_id": None,
            "user_message_id": None,
            "provider": "mock",
            "model": "mock-chat",
            "total_input_tokens": 7,
            "total_output_tokens": 5,
            "total_tokens": 12,
            "estimated_cost": "0.00000700",
            "latency_ms": 18,
            "error_message": None,
            "started_at": "2026-08-09T12:00:00",
            "ended_at": "2026-08-09T12:00:00",
            "created_at": "2026-08-09T12:00:00",
        }
    ]
    detail = detail_response.json()
    assert detail_response.status_code == 200
    assert "input_preview" not in detail
    assert detail["input_text"] == "Where is the design?"
    assert detail["steps"][0]["step_index"] == 1
    assert detail["retrieval_runs"][0]["id"] == str(RETRIEVAL_ID)
    assert detail["retrieval_runs"][0]["candidates"][0]["id"] == str(
        CANDIDATE_ID
    )
    assert detail["estimated_cost"] == "0.00000700"


def test_trace_api_honors_limit_and_returns_failed_zero_candidate_run(
    trace_api_context: Any,
) -> None:
    client, factory, _ = trace_api_context
    with factory() as session:
        for index in range(3):
            trace = TraceRun(
                id=UUID(int=400 + index),
                run_type="rag_query",
                status="failed" if index == 2 else "completed",
                input_text=f"Question {index}",
                error_message="Safe retrieval failure" if index == 2 else None,
                created_at=CREATED_AT,
            )
            if index == 2:
                trace.retrieval_runs.append(
                    RagRetrievalRun(
                        knowledge_base_id=UUID(int=500),
                        strategy_name="naive_vector",
                        original_query="Question 2",
                        top_k=5,
                        candidate_count=0,
                        selected_count=0,
                        latency_ms=0,
                        created_at=CREATED_AT,
                    )
                )
            session.add(trace)
        session.commit()

    listed = client.get("/api/v1/traces?limit=2").json()
    detail = client.get("/api/v1/traces/00000000-0000-0000-0000-000000000192")

    assert [row["id"] for row in listed] == [
        "00000000-0000-0000-0000-000000000192",
        "00000000-0000-0000-0000-000000000191",
    ]
    assert detail.status_code == 200
    assert detail.json()["status"] == "failed"
    assert detail.json()["error_message"] == "Safe retrieval failure"
    assert detail.json()["retrieval_runs"][0]["candidates"] == []


def test_trace_api_returns_safe_unknown_run(trace_api_context: Any) -> None:
    client, _, _ = trace_api_context

    response = client.get(f"/api/v1/traces/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "trace_run_not_found"
    assert response.json()["error"]["message"] == "Trace run not found"
    assert response.headers["x-request-id"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/traces?limit=0",
        "/api/v1/traces?limit=101",
        "/api/v1/traces/not-a-uuid",
    ],
)
def test_trace_api_rejects_invalid_parameters(
    trace_api_context: Any,
    path: str,
) -> None:
    client, _, _ = trace_api_context

    response = client.get(path)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_trace_api_redacts_database_errors(trace_api_context: Any) -> None:
    client, _, _ = trace_api_context

    class FailingTraceQueryService:
        def list_trace_runs(self, *, limit: int) -> list[object]:
            raise SQLAlchemyError("private-database-diagnostic")

    app.dependency_overrides[get_trace_query_service] = FailingTraceQueryService
    try:
        response = client.get("/api/v1/traces")
    finally:
        app.dependency_overrides.pop(get_trace_query_service, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_error"
    assert "private-database-diagnostic" not in response.text
