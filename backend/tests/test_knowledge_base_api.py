from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db_session
from app.api.errors import error_spec_for_exception
from app.db.base import Base
from app.db.session import create_db_engine
from app.main import app
from app.models import KnowledgeBase
from app.services import KnowledgeBaseNotFoundError


@pytest.fixture
def api_context(
    tmp_path: Path,
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(
        f"sqlite:///{tmp_path / 'knowledge-base-api.db'}"
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

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

    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def test_openapi_exposes_knowledge_base_crud(
    api_context: Any,
) -> None:
    client, _ = api_context
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths["/api/v1/knowledge-bases"]) == {
        "get",
        "post",
    }
    assert set(
        paths[
            "/api/v1/knowledge-bases/{knowledge_base_id}"
        ]
    ) == {"get", "patch", "delete"}


def test_knowledge_base_api_crud_round_trip(
    api_context: Any,
) -> None:
    client, factory = api_context

    created = client.post(
        "/api/v1/knowledge-bases",
        json={
            "name": "Project docs",
            "description": "Synthetic knowledge",
        },
    )
    knowledge_base_id = created.json()["id"]
    loaded = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}"
    )
    updated = client.patch(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        json={"name": "Updated docs", "description": None},
    )
    listed = client.get("/api/v1/knowledge-bases")
    deleted = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}"
    )
    missing = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}"
    )

    assert created.status_code == 201
    assert loaded.status_code == 200
    assert loaded.json() == created.json()
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated docs"
    assert updated.json()["description"] is None
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [
        knowledge_base_id
    ]
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == (
        "knowledge_base_not_found"
    )
    with factory() as session:
        assert session.scalar(
            select(func.count()).select_from(KnowledgeBase)
        ) == 0


def test_knowledge_base_api_lists_deterministically(
    api_context: Any,
) -> None:
    client, factory = api_context
    names = ["Older", "Tied A", "Tied B"]
    for name in names:
        response = client.post(
            "/api/v1/knowledge-bases",
            json={"name": name},
        )
        assert response.status_code == 201

    with factory() as session:
        rows = {
            row.name: row
            for row in session.scalars(select(KnowledgeBase))
        }
        rows["Older"].created_at = datetime(2026, 7, 24)
        tied_at = datetime(2026, 7, 25)
        rows["Tied A"].created_at = tied_at
        rows["Tied B"].created_at = tied_at
        expected_tied = sorted(
            [rows["Tied A"], rows["Tied B"]],
            key=lambda row: row.id,
        )
        expected_ids = [
            str(row.id)
            for row in [*expected_tied, rows["Older"]]
        ]
        session.commit()

    response = client.get("/api/v1/knowledge-bases")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == expected_ids


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("patch", "/not-a-uuid", {"name": "Invalid ID"}),
        ("patch", f"/{uuid4()}", {}),
        ("patch", f"/{uuid4()}", {"name": None}),
        ("patch", f"/{uuid4()}", {"vector_store": None}),
        ("patch", f"/{uuid4()}", {"unknown": "value"}),
    ],
)
def test_knowledge_base_api_rejects_invalid_update(
    api_context: Any,
    method: str,
    suffix: str,
    payload: dict[str, object],
) -> None:
    client, factory = api_context

    response = client.request(
        method,
        f"/api/v1/knowledge-bases{suffix}",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    with factory() as session:
        assert session.scalar(
            select(func.count()).select_from(KnowledgeBase)
        ) == 0


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_knowledge_base_api_returns_safe_404(
    api_context: Any,
    method: str,
) -> None:
    client, _ = api_context
    missing_id = uuid4()
    response = client.request(
        method,
        f"/api/v1/knowledge-bases/{missing_id}",
        json={"name": "Missing"} if method == "patch" else None,
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "knowledge_base_not_found",
            "message": "Knowledge base not found",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert str(missing_id) not in response.text


def test_knowledge_base_error_mapping_is_stable_and_safe() -> None:
    missing_id = uuid4()

    spec = error_spec_for_exception(
        KnowledgeBaseNotFoundError(missing_id)
    )

    assert spec.status_code == 404
    assert spec.code == "knowledge_base_not_found"
    assert spec.message == "Knowledge base not found"
    assert str(missing_id) not in spec.message


def test_knowledge_base_api_commit_failure_rolls_back(
    api_context: Any,
) -> None:
    _, factory = api_context

    class FailingCommitSession(Session):
        def commit(self) -> None:
            raise SQLAlchemyError(
                "private-database-commit-diagnostic"
            )

    failing_factory = sessionmaker(
        bind=factory.kw["bind"],
        class_=FailingCommitSession,
        expire_on_commit=False,
    )

    async def override_failing_session() -> AsyncIterator[Session]:
        session = failing_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = (
        override_failing_session
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/knowledge-bases",
            json={"name": "Rollback me"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_error",
            "message": "The database operation failed",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private-database-commit-diagnostic" not in response.text
    with factory() as session:
        assert session.scalar(
            select(func.count()).select_from(KnowledgeBase)
        ) == 0
