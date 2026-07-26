# Plan 3 M1 S7～S9 Knowledge Base API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` inline. Subagents, branch changes, staging,
> commits, pushes, and tags are forbidden by the active repository handoff.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Plan 3 Milestone 1 with tested Knowledge Base CRUD service
and HTTP boundaries plus the formal M1 data-model/API documentation.

**Architecture:** Keep the request path
`FastAPI route -> Pydantic validation -> KnowledgeBaseService -> SQLAlchemy
Session`. The request-scoped database dependency owns commit/rollback; the
service owns lookup, deterministic ordering, partial updates, deletion, and
flush behavior. Existing SQLite cascades remain the only deletion side effect.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite,
Alembic, pytest, FastAPI TestClient, Markdown.

## Global Constraints

- Work only on `P3-M1-S7～S9`.
- Preserve `main`; do not branch, stage, commit, push, or tag.
- Do not read, migrate, delete, or rebuild `backend/ai_agent_lab.db`.
- Use only newly created temporary SQLite databases in tests and migration
  checks.
- Do not access Qdrant from production code or tests in this batch.
- Do not add Document APIs, upload storage, parsers, Chunking, Embedding,
  Qdrant clients, Retriever/RAG runtime, Tool registration, or frontend code.
- Do not add Advanced RAG, Hybrid Search, Rerank, Evaluation, Trace runtime,
  Memory, OCR, multimodal, MCP, or Human Approval.
- Keep routes thin and transaction-free; business behavior belongs in
  `KnowledgeBaseService`.
- New comments, if needed for non-obvious boundaries, use Chinese.
- Use only Codex self-review. Do not request Claude Code, Fable, or another
  external review.
- The user creates the verified batch commit manually.

---

### Task 1: Knowledge Base partial-update schema

**Files:**
- Modify: `backend/app/schemas/knowledge_base.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/tests/test_knowledge_schemas.py`

**Interfaces:**
- Consumes: existing `KnowledgeBaseName`, `OptionalProviderName`, and
  `OptionalModelName` constrained string aliases.
- Produces: `KnowledgeBaseUpdate`, where omission preserves a field, explicit
  null clears nullable fields, empty payloads are invalid, and explicit null is
  invalid for `name` and `vector_store`.

- [x] **Step 1: Write failing update-schema tests**

Extend imports:

```python
from app.schemas import KnowledgeBaseUpdate
```

Add:

```python
def test_knowledge_base_update_tracks_only_supplied_fields() -> None:
    update = KnowledgeBaseUpdate(
        name="  Updated knowledge  ",
        description=None,
    )

    assert update.name == "Updated knowledge"
    assert update.description is None
    assert update.model_dump(exclude_unset=True) == {
        "name": "Updated knowledge",
        "description": None,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"name": "   "},
        {"vector_store": None},
        {"unknown": "value"},
    ],
)
def test_knowledge_base_update_rejects_invalid_payload(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        KnowledgeBaseUpdate.model_validate(payload)
```

- [x] **Step 2: Run RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_knowledge_schemas.py
```

Expected: collection fails because `KnowledgeBaseUpdate` is not exported.

- [x] **Step 3: Implement the minimal update schema**

In `knowledge_base.py`, import `Self` and `model_validator`, then add:

```python
class KnowledgeBaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: KnowledgeBaseName | None = None
    description: str | None = None
    embedding_provider: OptionalProviderName | None = None
    embedding_model: OptionalModelName | None = None
    vector_store: OptionalProviderName | None = None
    vector_collection_name: OptionalModelName | None = None

    @model_validator(mode="after")
    def validate_partial_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name must not be null")
        if (
            "vector_store" in self.model_fields_set
            and self.vector_store is None
        ):
            raise ValueError("vector_store must not be null")
        return self
```

Export it from `app.schemas`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_knowledge_schemas.py
```

Expected: all knowledge schema tests pass.

- [x] **Step 5: Record the checkpoint**

Record the exact RED and GREEN outputs in this plan's execution-evidence
section. Do not stage or commit.

---

### Task 2: Knowledge Base service and domain error

**Files:**
- Create: `backend/app/services/knowledge_base_service.py`
- Modify: `backend/app/services/errors.py`
- Modify: `backend/app/services/__init__.py`
- Create: `backend/tests/test_knowledge_base_service.py`

**Interfaces:**
- Consumes: `KnowledgeBase`, `KnowledgeBaseCreate`, `KnowledgeBaseUpdate`,
  `utc_now`, and a caller-owned SQLAlchemy `Session`.
- Produces:
  - `create_knowledge_base(data) -> KnowledgeBase`
  - `list_knowledge_bases() -> list[KnowledgeBase]`
  - `get_knowledge_base(id) -> KnowledgeBase`
  - `update_knowledge_base(id, data) -> KnowledgeBase`
  - `delete_knowledge_base(id) -> None`
  - `KnowledgeBaseNotFoundError`

- [x] **Step 1: Write failing service tests**

Create the test module with a temporary-database fixture:

```python
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services import (
    KnowledgeBaseNotFoundError,
    KnowledgeBaseService,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(
        f"sqlite:///{tmp_path / 'knowledge-base-service.db'}"
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()
```

Add creation/detail and deterministic-list tests:

```python
def test_service_creates_gets_and_lists_knowledge_bases(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    older = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Older")
    )
    tied_a = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Tied A")
    )
    tied_b = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Tied B")
    )
    older.created_at = datetime(2026, 7, 24)
    tied_at = datetime(2026, 7, 25)
    tied_a.created_at = tied_at
    tied_b.created_at = tied_at
    session.flush()

    assert service.get_knowledge_base(older.id) is older
    expected_tied = sorted([tied_a, tied_b], key=lambda item: item.id)
    assert service.list_knowledge_bases() == [*expected_tied, older]
```

Add partial-update and nullable-clear tests:

```python
def test_service_partially_updates_and_clears_nullable_fields(
    db: tuple[Session, Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    row = service.create_knowledge_base(
        KnowledgeBaseCreate(
            name="Original",
            description="Clear me",
            embedding_provider="mock",
            embedding_model="embed-v1",
        )
    )
    previous_updated_at = row.updated_at
    monkeypatch.setattr(
        "app.services.knowledge_base_service.utc_now",
        lambda: previous_updated_at,
    )

    updated = service.update_knowledge_base(
        row.id,
        KnowledgeBaseUpdate(name="Updated", description=None),
    )

    assert updated is row
    assert updated.name == "Updated"
    assert updated.description is None
    assert updated.embedding_provider == "mock"
    assert updated.embedding_model == "embed-v1"
    assert updated.updated_at > previous_updated_at
```

Add delete and not-found tests:

```python
def test_service_deletes_knowledge_base(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    row = service.create_knowledge_base(
        KnowledgeBaseCreate(name="Delete me")
    )
    knowledge_base_id = row.id

    service.delete_knowledge_base(knowledge_base_id)

    with pytest.raises(KnowledgeBaseNotFoundError):
        service.get_knowledge_base(knowledge_base_id)


@pytest.mark.parametrize("operation", ["get", "update", "delete"])
def test_service_rejects_unknown_knowledge_base(
    db: tuple[Session, Engine],
    operation: str,
) -> None:
    session, _ = db
    service = KnowledgeBaseService(session)
    missing_id = uuid4()

    with pytest.raises(
        KnowledgeBaseNotFoundError,
        match=f"Knowledge base not found: {missing_id}",
    ):
        if operation == "get":
            service.get_knowledge_base(missing_id)
        elif operation == "update":
            service.update_knowledge_base(
                missing_id,
                KnowledgeBaseUpdate(name="Missing"),
            )
        else:
            service.delete_knowledge_base(missing_id)
```

- [x] **Step 2: Run RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_knowledge_base_service.py
```

Expected: collection fails because the new service/error exports do not exist.

- [x] **Step 3: Implement the domain error**

Add to `services/errors.py`:

```python
class KnowledgeBaseNotFoundError(ServiceError):
    def __init__(self, knowledge_base_id: UUID) -> None:
        super().__init__(
            f"Knowledge base not found: {knowledge_base_id}"
        )
        self.knowledge_base_id = knowledge_base_id
```

Export it from `app.services`.

- [x] **Step 4: Implement the minimal service**

Create:

```python
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeBase
from app.models.common import utc_now
from app.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services.errors import KnowledgeBaseNotFoundError


class KnowledgeBaseService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_knowledge_base(
        self,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(**data.model_dump())
        self._session.add(knowledge_base)
        self._session.flush()
        return knowledge_base

    def list_knowledge_bases(self) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase).order_by(
            KnowledgeBase.created_at.desc(),
            KnowledgeBase.id,
        )
        return list(self._session.scalars(statement))

    def get_knowledge_base(
        self,
        knowledge_base_id: UUID,
    ) -> KnowledgeBase:
        knowledge_base = self._session.get(
            KnowledgeBase,
            knowledge_base_id,
        )
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError(knowledge_base_id)
        return knowledge_base

    def update_knowledge_base(
        self,
        knowledge_base_id: UUID,
        data: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        knowledge_base = self.get_knowledge_base(knowledge_base_id)
        for field_name, value in data.model_dump(
            exclude_unset=True
        ).items():
            setattr(knowledge_base, field_name, value)

        next_updated_at = utc_now()
        if next_updated_at <= knowledge_base.updated_at:
            next_updated_at = (
                knowledge_base.updated_at + timedelta(microseconds=1)
            )
        knowledge_base.updated_at = next_updated_at
        self._session.flush()
        return knowledge_base

    def delete_knowledge_base(
        self,
        knowledge_base_id: UUID,
    ) -> None:
        knowledge_base = self.get_knowledge_base(knowledge_base_id)
        self._session.delete(knowledge_base)
        self._session.flush()
```

Export `KnowledgeBaseService` from `app.services`.

- [x] **Step 5: Run GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_knowledge_schemas.py `
  tests/test_knowledge_base_service.py
```

Expected: schema and service tests pass.

- [x] **Step 6: Record the checkpoint**

Record the exact RED and GREEN outputs. Do not stage or commit.

---

### Task 3: Thin Knowledge Base HTTP API

**Files:**
- Create: `backend/app/api/v1/knowledge_bases.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/errors.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_knowledge_base_api.py`

**Interfaces:**
- Consumes: `KnowledgeBaseService`, `KnowledgeBaseCreate`,
  `KnowledgeBaseUpdate`, `KnowledgeBaseRead`, and request-scoped
  `get_db_session`.
- Produces:
  - `POST /api/v1/knowledge-bases` -> 201
  - `GET /api/v1/knowledge-bases` -> 200
  - `GET /api/v1/knowledge-bases/{knowledge_base_id}` -> 200
  - `PATCH /api/v1/knowledge-bases/{knowledge_base_id}` -> 200
  - `DELETE /api/v1/knowledge-bases/{knowledge_base_id}` -> 204
  - safe 404 `knowledge_base_not_found`

- [x] **Step 1: Write the failing API fixture and OpenAPI test**

Create:

```python
from collections.abc import AsyncIterator, Iterator
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
) -> Iterator[
    tuple[TestClient, sessionmaker[Session]]
]:
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
```

- [x] **Step 2: Add failing CRUD and ordering tests**

```python
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
```

Add deterministic list ordering:

```python
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
```

Add `from datetime import datetime` to the test imports.

- [x] **Step 3: Add failing validation and safe-error tests**

```python
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
```

Add a unit-testable safe mapping:

```python
def test_knowledge_base_error_mapping_is_stable_and_safe() -> None:
    missing_id = uuid4()

    spec = error_spec_for_exception(
        KnowledgeBaseNotFoundError(missing_id)
    )

    assert spec.status_code == 404
    assert spec.code == "knowledge_base_not_found"
    assert spec.message == "Knowledge base not found"
    assert str(missing_id) not in spec.message
```

- [x] **Step 4: Add the failing commit-error test**

Add:

```python
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
```

- [x] **Step 5: Run RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_knowledge_base_api.py
```

Expected: API tests fail with 404/missing OpenAPI paths because the router is
not registered.

- [x] **Step 6: Add the service dependency and error mapping**

In `api/dependencies.py`:

```python
def get_knowledge_base_service(
    session: Session = Depends(get_db_session, scope="function"),
) -> KnowledgeBaseService:
    return KnowledgeBaseService(session)
```

In `api/errors.py`, import the new error and map:

```python
if isinstance(exc, KnowledgeBaseNotFoundError):
    return ErrorSpec(
        404,
        "knowledge_base_not_found",
        "Knowledge base not found",
    )
```

- [x] **Step 7: Implement the thin router**

Create:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_knowledge_base_service
from app.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services import KnowledgeBaseService


router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge-bases"],
)


@router.get("", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> list[KnowledgeBaseRead]:
    return [
        KnowledgeBaseRead.model_validate(row)
        for row in service.list_knowledge_bases()
    ]


@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(
        service.create_knowledge_base(data)
    )


@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def get_knowledge_base(
    knowledge_base_id: UUID,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(
        service.get_knowledge_base(knowledge_base_id)
    )


@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def update_knowledge_base(
    knowledge_base_id: UUID,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(
        service.update_knowledge_base(knowledge_base_id, data)
    )


@router.delete(
    "/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_knowledge_base(
    knowledge_base_id: UUID,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> Response:
    service.delete_knowledge_base(knowledge_base_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Register the router in `main.py` below the other v1 resource routers.

- [x] **Step 8: Run GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_knowledge_schemas.py `
  tests/test_knowledge_base_service.py `
  tests/test_knowledge_base_api.py
```

Expected: all Knowledge Base schema/service/API tests pass.

- [x] **Step 9: Record the checkpoint**

Record the exact RED and GREEN outputs. Do not stage or commit.

---

### Task 4: S9 M1 documentation and current truth

**Files:**
- Create: `docs/20-knowledge-base-design.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this implementation plan's observed-evidence/checklist section

**Interfaces:**
- Consumes: verified service/API behavior and the S4～S6 model design.
- Produces: formal M1 model/API documentation and an accurate Batch 3
  acceptance record.

- [x] **Step 1: Write `docs/20-knowledge-base-design.md`**

Use these reader-facing sections:

```markdown
# Knowledge Base Design

## Scope
## Storage Responsibilities
## Ownership Graph
## KnowledgeBase
## Document Lifecycle
## DocumentChunk Integrity
## RagQuery Bridge
## Knowledge Base Service
## HTTP API
## Error And Transaction Behavior
## Verification
## Deferred Capabilities
```

Document exact fields, status values, named ownership/consistency constraints,
delete cascades, the five HTTP operations, safe 404 behavior, and the absence of
Qdrant deletion/runtime in M1.

- [x] **Step 2: Update architecture and API references**

Record:

- completed scope through `P3-M1-S9`;
- `KnowledgeBaseService` as the owner of CRUD business behavior;
- request-scoped commit/rollback;
- plural kebab-case routes and `PATCH` partial semantics;
- `DELETE` affecting SQLite-owned metadata only;
- no Document API, ingestion, Embedding, Qdrant client, Retriever, or frontend
  Knowledge Base behavior yet.

- [x] **Step 3: Update README/CHANGELOG/current Plan evidence**

Update current truth without claiming Plan 3 completion. Mark Batch 3 and the
M1 Knowledge Base creation/API/document rows implemented. Preserve all M2+
items as pending. Record fresh RED/GREEN, full regression, migration, docs,
security, boundary, and Git evidence after those commands have actually run.

Replace legacy per-batch external-review wording only in the new Batch 3
acceptance record; do not rewrite source planning history broadly.

- [x] **Step 4: Run documentation pre-gates**

Require:

- all local Markdown links/images resolve;
- `docs/20-knowledge-base-design.md` exists;
- current-stage statements consistently end at `P3-M1-S9`;
- no documentation claims Document upload, Qdrant client, RAG retrieval, or
  frontend Knowledge Base behavior is implemented.

- [x] **Step 5: Record the checkpoint**

Record exact document/link counts only after the gate runs. Do not stage or
commit.

---

### Task 5: Matching verification, full regression, and Codex review

**Files:**
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this implementation plan's observed evidence/checklists

**Interfaces:**
- Consumes: the complete S7～S9 diff.
- Produces: a verified manual-commit handoff and decision on whether M1 may
  enter `P3-M2-S1～S3`.

- [x] **Step 1: Run focused backend verification**

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests/test_knowledge_schemas.py `
  tests/test_knowledge_models.py `
  tests/test_knowledge_migration.py `
  tests/test_knowledge_base_service.py `
  tests/test_knowledge_base_api.py
```

- [x] **Step 2: Run complete regression**

Backend:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Frontend:

```powershell
npm run test
npm run typecheck
npm run build
```

- [x] **Step 3: Run fresh temporary Alembic gates**

Create a unique directory below the system temp root, verify its resolved path
is below that root and outside the workspace, set `DATABASE_URL` to its new
SQLite file, and run:

```powershell
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c alembic.ini current --check-heads
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c alembic.ini check
```

Require head `20260726_0005`, no new upgrade operations, and verified removal of
that temp root. Never point Alembic at `backend/ai_agent_lab.db`.

- [x] **Step 4: Run repository gates**

Require:

- all Markdown links/images resolve;
- added-line high-confidence secret hits are zero;
- real Provider host additions are zero;
- tracked/untracked generated database artifacts are zero;
- `web_fetch` runtime additions are zero;
- later-Plan runtime additions are zero;
- Document API/upload/parser/Chunking/Embedding/Qdrant-client/Retriever/
  frontend additions are zero;
- `git diff --check` has zero findings;
- staged paths are zero;
- `HEAD == origin/main == 13e0cba4313580195da3e26c9ab1240a68d1dcfb`;
- `v0.2.0^{}` remains
  `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`;
- `v0.2.1^{}` remains
  `872310b4dc1b78e2a2487303699d68ec8b22f88b`.

- [x] **Step 5: Perform Codex self-review**

Review the full diff for:

- route thinness and transaction ownership;
- PATCH omission/null semantics;
- deterministic list ordering;
- 204 response correctness;
- safe 404/422/503 behavior;
- no leaked UUID, SQL, paths, metadata, query/document content, or secrets;
- no Qdrant side-effect claim;
- no M2 or later-Plan implementation;
- docs matching actual runtime.

Classify every finding as:

- must fix;
- later Step;
- accepted limitation;
- not applicable.

Fix must-fix findings and rerun affected verification. Do not request external
review and do not commit.

- [x] **Step 6: Prepare the manual handoff**

State whether `P3-M1-S7～S9` and M1 are complete and whether the repository may
enter `P3-M2-S1～S3`. Suggested commit message:

```text
feat(knowledge): add knowledge base service and api
```

## Observed Execution Evidence

- Task 1 RED: `test_knowledge_schemas.py` stopped during collection with
  `ImportError: cannot import name 'KnowledgeBaseUpdate' from 'app.schemas'`.
- Task 1 GREEN: `35 passed in 1.07s`.
- Task 2 RED: `test_knowledge_base_service.py` stopped during collection with
  `ImportError: cannot import name 'KnowledgeBaseNotFoundError' from
  'app.services'`.
- Task 2 GREEN: schema and service focus reached `41 passed in 1.28s`.
- Task 3 RED: `test_knowledge_base_api.py` produced `13 failed, 1 warning`;
  the CRUD/OpenAPI requests returned the expected pre-route 404 surface and
  the new domain error still mapped to the pre-implementation 500 fallback.
- Task 3 GREEN: schema/service/API focus reached `54 passed, 1 warning in
  2.84s`.
- Task 4 documentation gate: `86` Markdown files and `69` local links/images
  were checked with `0` missing targets. Current-stage references end at
  `P3-M1-S9`, the formal M1 design exists, and later ingestion/Qdrant/RAG/UI
  runtime remains explicitly deferred.
- Task 5 focused verification: schema/model/migration/service/API reached `76
  passed, 1 warning in 5.65s`.
- Task 5 complete backend: `583 passed, 1 warning in 24.16s`; `pip check`
  reported `No broken requirements found`.
- Task 5 frontend: `18` files / `90` tests passed, typecheck succeeded, and the
  production build transformed `1813` modules.
- Task 5 temporary migration: `20260726_0005 (head)`,
  `No new upgrade operations detected`, and `temporary_root_removed=True`.
  The user database was not read or modified.
- Task 5 repository gates: `21` changed paths, `0` unexpected paths, `0`
  high-confidence secret hits, `0` real HTTP hosts, `0` deferred-runtime paths,
  `0` production `web_fetch` hits, `0` generated/database artifacts, `0` staged
  paths, and no `git diff --check` findings. Git refs matched the recorded
  baseline and existing tag targets.
- Task 5 Codex self-review: documentation-edit must-fix items were corrected
  before final gates; no runtime must-fix remains. Later steps, accepted
  limitations, and not-applicable external/later-Plan review items are
  classified in the active Plan 3 execution table.
