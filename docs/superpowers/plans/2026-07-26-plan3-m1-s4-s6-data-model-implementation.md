# Plan 3 M1 S4～S6 Data Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` inline. Subagents, branch changes, staging,
> commits, pushes, and tags are forbidden by the active repository handoff.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bridge-ready KnowledgeBase, Document, DocumentChunk, and RagQuery
ORM/schema persistence on SQLite with one reversible Alembic migration.

**Architecture:** Keep one ORM module per persisted concept and group public
Pydantic schemas by knowledge/document/RAG domain. Enforce ownership and
cross-parent consistency in the database, while deferring services, APIs,
upload/parsing, Embedding, Qdrant access, and frontend behavior.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0, Alembic 1.18, Pydantic 2.13,
SQLite, pytest 9.

## Global Constraints

- Work only on `P3-M1-S4～S6`.
- Preserve `main`; do not branch, stage, commit, push, or tag.
- Do not read, migrate, delete, or rebuild `backend/ai_agent_lab.db`.
- Run migrations only against newly created temporary SQLite databases.
- Do not add services, routes, upload storage, parsers, Chunking, Embedding,
  Qdrant clients, Retriever/RAG runtime, Tools, or frontend code.
- Do not add Advanced RAG, Hybrid Search, Rerank, Evaluation, Memory, OCR,
  multimodal, MCP, or Human Approval behavior.
- Keep SQLite as the primary business/audit database and Qdrant as vector
  storage only.
- Use synthetic UUIDs, paths, metadata, and content in tests.
- Add Chinese comments only for non-obvious integrity boundaries.

---

### Task 1: Lock ORM persistence and integrity contracts with RED tests

**Files:**
- Create: `backend/tests/test_knowledge_models.py`

**Interfaces:**
- Consumes: `Base`, `create_db_engine`, and the wished-for exports
  `KnowledgeBase`, `Document`, `DocumentChunk`, and `RagQuery`.
- Produces: executable contracts for defaults, JSON isolation, relationships,
  cascades, lifecycle checks, composite ownership, and query/message
  consistency.

- [x] **Step 1: Add the temporary-database fixture and graph helper**

Create the test module with:

```python
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import (
    Conversation,
    Document,
    DocumentChunk,
    KnowledgeBase,
    Message,
    RagQuery,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'knowledge-models.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_document(knowledge_base: KnowledgeBase) -> Document:
    return Document(
        knowledge_base=knowledge_base,
        filename="guide.md",
        original_filename="Guide.md",
        file_type="md",
        file_path="uploads/kb/guide.md",
        file_size=128,
        file_hash="a" * 64,
    )
```

- [x] **Step 2: Add graph/default/JSON/cascade tests**

Add:

```python
def test_knowledge_models_persist_graph_defaults_and_json(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    answer = Message(
        conversation=conversation,
        role="assistant",
        content="Synthetic answer",
    )
    knowledge_base = KnowledgeBase(name="Project docs")
    document = create_document(knowledge_base)
    chunk = DocumentChunk(
        document=document,
        knowledge_base_id=knowledge_base.id,
        chunk_index=0,
        content="Synthetic chunk",
        token_count=3,
        char_count=15,
        metadata_json={"section": "intro"},
    )
    query = RagQuery(
        knowledge_base=knowledge_base,
        conversation=conversation,
        answer_message=answer,
        query="What is this?",
        retrieved_chunks_json=[{"chunk_id": "synthetic"}],
    )
    session.add_all([knowledge_base, conversation])
    session.commit()
    session.expire_all()

    loaded = session.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base.id)
    )

    assert loaded is not None
    assert loaded.vector_store == "qdrant"
    assert loaded.documents[0].parse_status == "uploaded"
    assert loaded.documents[0].chunk_status == "pending"
    assert loaded.documents[0].embedding_status == "pending"
    assert loaded.documents[0].metadata_json == {}
    assert loaded.documents[0].chunks == [chunk]
    assert chunk.metadata_json == {"section": "intro"}
    assert loaded.rag_queries == [query]
    assert query.answer_message_id == answer.id
    assert query.retrieved_chunks_json == [{"chunk_id": "synthetic"}]


def test_json_defaults_are_isolated(db: tuple[Session, Engine]) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Defaults")
    first = create_document(knowledge_base)
    second = create_document(knowledge_base)
    second.filename = "second.md"
    second.original_filename = "Second.md"
    second.file_path = "uploads/kb/second.md"
    second.file_hash = "b" * 64
    session.add(knowledge_base)
    session.flush()

    first.metadata_json["source"] = "first"

    assert second.metadata_json == {}
    assert first.metadata_json is not second.metadata_json


def test_deleting_knowledge_base_cascades_documents_chunks_and_queries(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Delete me")
    document = create_document(knowledge_base)
    document.chunks.append(
        DocumentChunk(
            knowledge_base_id=knowledge_base.id,
            chunk_index=0,
            content="Synthetic chunk",
            token_count=3,
            char_count=15,
        )
    )
    knowledge_base.rag_queries.append(RagQuery(query="Synthetic query"))
    session.add(knowledge_base)
    session.commit()

    session.delete(knowledge_base)
    session.commit()

    assert session.scalars(select(Document)).all() == []
    assert session.scalars(select(DocumentChunk)).all() == []
    assert session.scalars(select(RagQuery)).all() == []
```

- [x] **Step 3: Add database-constraint tests**

Add focused tests that each rollback after the expected `IntegrityError`:

```python
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("parse_status", "unknown"),
        ("chunk_status", "unknown"),
        ("embedding_status", "unknown"),
        ("file_size", -1),
        ("file_hash", "short"),
        ("file_type", "docx"),
    ],
)
def test_document_rejects_invalid_lifecycle_data(
    db: tuple[Session, Engine],
    field_name: str,
    invalid_value: object,
) -> None:
    session, _ = db
    knowledge_base = KnowledgeBase(name="Invalid document")
    document = create_document(knowledge_base)
    setattr(document, field_name, invalid_value)
    session.add(knowledge_base)

    with pytest.raises(IntegrityError):
        session.commit()


def test_chunk_rejects_cross_knowledge_base(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    first = KnowledgeBase(name="First")
    second = KnowledgeBase(name="Second")
    document = create_document(first)
    session.add_all([first, second])
    session.flush()
    session.add(
        DocumentChunk(
            document_id=document.id,
            knowledge_base_id=second.id,
            chunk_index=0,
            content="Wrong owner",
            token_count=2,
            char_count=11,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_rag_query_answer_message_must_match_conversation(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    first = Conversation()
    second = Conversation()
    answer = Message(
        conversation=second,
        role="assistant",
        content="Other conversation",
    )
    knowledge_base = KnowledgeBase(name="Queries")
    session.add_all([first, second, knowledge_base])
    session.flush()
    session.add(
        RagQuery(
            knowledge_base_id=knowledge_base.id,
            conversation_id=first.id,
            answer_message_id=answer.id,
            query="Mismatch",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
```

Also add:

- a separate duplicate `(document_id, chunk_index)` test;
- a parameterized chunk numeric-constraint test for negative `chunk_index`,
  `token_count`, `char_count`, and non-positive `page_number`;
- a blank KnowledgeBase name database-constraint test;
- a test that deleting one answer Message clears `answer_message_id` while
  preserving its RagQuery.

- [x] **Step 4: Run RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_knowledge_models.py
```

Expected: collection fails because the four new model exports do not exist.
No unrelated test should run.

---

### Task 2: Implement the four ORM models and relationships

**Files:**
- Create: `backend/app/models/knowledge_base.py`
- Create: `backend/app/models/document.py`
- Create: `backend/app/models/document_chunk.py`
- Create: `backend/app/models/rag_query.py`
- Modify: `backend/app/models/conversation.py`
- Modify: `backend/app/models/message.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Consumes: `Base`, `utc_now`, `Conversation`, and `Message`.
- Produces: the four public model classes and `Base.metadata` table
  definitions consumed by Alembic and later services.

- [x] **Step 1: Implement KnowledgeBase**

Create `knowledge_base.py` with UUID/timestamps, the approved bounded fields, a
blank-name check, and these relationships:

```python
id: Mapped[UUID]
name: Mapped[str]
description: Mapped[str | None]
embedding_provider: Mapped[str | None]
embedding_model: Mapped[str | None]
vector_store: Mapped[str]  # default="qdrant"
vector_collection_name: Mapped[str | None]
created_at: Mapped[datetime]
updated_at: Mapped[datetime]

documents: Mapped[list[Document]] = relationship(
    back_populates="knowledge_base",
    cascade="all, delete-orphan",
    passive_deletes=True,
)
rag_queries: Mapped[list[RagQuery]] = relationship(
    back_populates="knowledge_base",
    cascade="all, delete-orphan",
    passive_deletes=True,
)
```

The table check is named `ck_knowledge_bases_name_not_blank`.

- [x] **Step 2: Implement Document**

Create `document.py` with the exact fields/status defaults from the spec.
Declare:

```python
__table_args__ = (
    CheckConstraint(
        "file_type IN ('md', 'txt', 'pdf')",
        name="ck_documents_file_type",
    ),
    CheckConstraint(
        "file_size >= 0",
        name="ck_documents_file_size_non_negative",
    ),
    CheckConstraint(
        "length(file_hash) = 64",
        name="ck_documents_file_hash_length",
    ),
    CheckConstraint(
        "parse_status IN ('uploaded', 'parsing', 'parsed', 'failed')",
        name="ck_documents_parse_status",
    ),
    CheckConstraint(
        "chunk_status IN ('pending', 'chunking', 'chunked', 'failed')",
        name="ck_documents_chunk_status",
    ),
    CheckConstraint(
        "embedding_status IN ('pending', 'embedding', 'ready', 'failed')",
        name="ck_documents_embedding_status",
    ),
    UniqueConstraint(
        "id",
        "knowledge_base_id",
        name="uq_documents_id_knowledge_base_id",
    ),
)
```

Use `metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON(), default=dict)`
and relate Document to KnowledgeBase and DocumentChunk.

The complete mapped field set is:

```python
id: Mapped[UUID]
knowledge_base_id: Mapped[UUID]
filename: Mapped[str]
original_filename: Mapped[str]
file_type: Mapped[str]
file_path: Mapped[str]
file_size: Mapped[int]
file_hash: Mapped[str]
parse_status: Mapped[str]  # default="uploaded"
chunk_status: Mapped[str]  # default="pending"
embedding_status: Mapped[str]  # default="pending"
error_message: Mapped[str | None]
metadata_json: Mapped[dict[str, Any]]
created_at: Mapped[datetime]
updated_at: Mapped[datetime]
```

- [x] **Step 3: Implement DocumentChunk**

Create `document_chunk.py` with the approved fields and:

```python
__table_args__ = (
    ForeignKeyConstraint(
        ["document_id", "knowledge_base_id"],
        ["documents.id", "documents.knowledge_base_id"],
        name="fk_document_chunks_document_knowledge_base_documents",
        ondelete="CASCADE",
    ),
    CheckConstraint(
        "chunk_index >= 0",
        name="ck_document_chunks_chunk_index_non_negative",
    ),
    CheckConstraint(
        "token_count >= 0",
        name="ck_document_chunks_token_count_non_negative",
    ),
    CheckConstraint(
        "char_count >= 0",
        name="ck_document_chunks_char_count_non_negative",
    ),
    CheckConstraint(
        "page_number IS NULL OR page_number > 0",
        name="ck_document_chunks_page_number_positive",
    ),
    UniqueConstraint(
        "document_id",
        "chunk_index",
        name="uq_document_chunks_document_id_chunk_index",
    ),
)
```

Relate only to Document; keep `knowledge_base_id` as an indexed denormalized
filter value validated through the composite foreign key.

The complete mapped field set is:

```python
id: Mapped[UUID]
document_id: Mapped[UUID]
knowledge_base_id: Mapped[UUID]
chunk_index: Mapped[int]
content: Mapped[str]
token_count: Mapped[int]
char_count: Mapped[int]
heading: Mapped[str | None]
page_number: Mapped[int | None]
metadata_json: Mapped[dict[str, Any]]
vector_id: Mapped[str | None]
created_at: Mapped[datetime]
```

- [x] **Step 4: Implement RagQuery and existing-model relationships**

Create `rag_query.py` with the approved full record and:

```python
__table_args__ = (
    ForeignKeyConstraint(
        ["answer_message_id", "conversation_id"],
        ["messages.id", "messages.conversation_id"],
        name="fk_rag_queries_answer_message_conversation_messages",
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "answer_message_id IS NULL OR conversation_id IS NOT NULL",
        name="ck_rag_queries_answer_requires_conversation",
    ),
    CheckConstraint(
        "latency_ms IS NULL OR latency_ms >= 0",
        name="ck_rag_queries_latency_ms_non_negative",
    ),
)
```

Use a direct `conversation_id -> conversations.id ON DELETE CASCADE` foreign
key and a direct `knowledge_base_id -> knowledge_bases.id ON DELETE CASCADE`
foreign key. Use `JSON()` with `default=list` for retrieved chunks.

The complete mapped field set is:

```python
id: Mapped[UUID]
conversation_id: Mapped[UUID | None]
knowledge_base_id: Mapped[UUID]
query: Mapped[str]
retrieved_chunks_json: Mapped[list[dict[str, Any]]]
answer_message_id: Mapped[UUID | None]
latency_ms: Mapped[int | None]
created_at: Mapped[datetime]
```

Add `Conversation.rag_queries` and `Message.answered_rag_queries` using the
same composite-message join/`foreign_keys` pattern already used by AgentRun.

- [x] **Step 5: Export models and run GREEN**

Export all four classes in `app.models.__init__`, then run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_knowledge_models.py
```

Expected: all knowledge-model tests pass. If SQLAlchemy emits relationship
overlap warnings, correct the relationship ownership instead of suppressing
unrelated warnings.

---

### Task 3: Lock and implement Pydantic schema contracts

**Files:**
- Create: `backend/tests/test_knowledge_schemas.py`
- Create: `backend/app/schemas/knowledge_base.py`
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/schemas/rag.py`
- Modify: `backend/app/schemas/__init__.py`

**Interfaces:**
- Consumes: the four ORM models.
- Produces: `KnowledgeBaseCreate/Read`, `DocumentCreate/Read`,
  `DocumentChunkCreate/Read`, `RagQueryCreate/Read`, and the three status
  Literal aliases.

- [x] **Step 1: Write RED schema tests**

Create tests for defaults and validation:

```python
def test_knowledge_base_create_defaults() -> None:
    schema = KnowledgeBaseCreate(name="  Project docs  ")

    assert schema.name == "Project docs"
    assert schema.vector_store == "qdrant"
    assert schema.embedding_provider is None
    assert schema.vector_collection_name is None


def test_document_create_defaults_and_metadata() -> None:
    schema = DocumentCreate(
        knowledge_base_id=UUID(int=1),
        filename="guide.md",
        original_filename="Guide.md",
        file_type="md",
        file_path="uploads/kb/guide.md",
        file_size=128,
        file_hash="a" * 64,
        metadata={"source": "synthetic"},
    )

    assert schema.parse_status == "uploaded"
    assert schema.chunk_status == "pending"
    assert schema.embedding_status == "pending"
    assert schema.metadata == {"source": "synthetic"}
```

Add parameterized `ValidationError` tests for blank names/query/content,
unsupported file type, malformed SHA-256, negative sizes/counts/index/latency,
page zero, unknown fields, and `answer_message_id` without
`conversation_id`.

Add one ORM conversion test that creates all four ORM rows in a temporary
SQLite database and verifies the read schemas expose `metadata`, not
`metadata_json`.

- [x] **Step 2: Run schema RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_knowledge_schemas.py
```

Expected: collection fails because the new schema exports do not exist.

- [x] **Step 3: Implement KnowledgeBase schemas**

Create a stripped non-empty bounded name type with `StringConstraints`. Define
create/read schemas with `ConfigDict(extra="forbid")`; add
`from_attributes=True` only to the read schema.

- [x] **Step 4: Implement Document and DocumentChunk schemas**

Define:

```python
DocumentFileType = Literal["md", "txt", "pdf"]
DocumentParseStatus = Literal["uploaded", "parsing", "parsed", "failed"]
DocumentChunkStatus = Literal["pending", "chunking", "chunked", "failed"]
DocumentEmbeddingStatus = Literal["pending", "embedding", "ready", "failed"]
```

Use:

```python
metadata: dict[str, Any] = Field(
    default_factory=dict,
    validation_alias=AliasChoices("metadata", "metadata_json"),
    serialization_alias="metadata",
)
```

Set `populate_by_name=True` so direct public input and ORM `metadata_json`
validation both work. Validate hash with
`StringConstraints(pattern=r"^[0-9a-fA-F]{64}$")`.

- [x] **Step 5: Implement RagQuery schemas**

Use `retrieved_chunks_json: list[dict[str, Any]]` consistently in both ORM and
schema, with an isolated `default_factory=list`.

Add an `after` model validator:

```python
@model_validator(mode="after")
def require_conversation_for_answer(self) -> Self:
    if self.answer_message_id is not None and self.conversation_id is None:
        raise ValueError("answer_message_id requires conversation_id")
    return self
```

- [x] **Step 6: Export schemas and run GREEN**

Update `app.schemas.__init__`, run the schema tests, then run model and schema
tests together. Expected: all pass with no new warnings.

---

### Task 4: Lock and implement Alembic revision 0005

**Files:**
- Create: `backend/tests/test_knowledge_migration.py`
- Create: `backend/alembic/versions/20260726_0005_plan3_knowledge_models.py`

**Interfaces:**
- Consumes: ORM `Base.metadata` and migration head `20260720_0004`.
- Produces: revision `20260726_0005` with the four tables and reversible
  downgrade.

- [x] **Step 1: Write migration RED**

Create a temporary-database Alembic fixture that always sets `DATABASE_URL`,
clears `get_settings` before/after migration commands, and never points at the
project database.

Add a head-upgrade test asserting:

```python
assert {
    "knowledge_bases",
    "documents",
    "document_chunks",
    "rag_queries",
} <= set(inspector.get_table_names())
```

Assert exact column sets for all four tables, named status/numeric/hash
checks, expected indexes, `uq_documents_id_knowledge_base_id`,
`uq_document_chunks_document_id_chunk_index`, the composite chunk/document
foreign key, both RagQuery ownership foreign keys, and the composite
answer-message foreign key.

Add a downgrade test:

```python
command.upgrade(config, "head")
command.downgrade(config, "20260720_0004")

assert new_tables.isdisjoint(inspect(engine).get_table_names())
assert {"conversations", "messages", "agent_runs", "tool_calls"} <= tables
```

- [x] **Step 2: Run migration RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_knowledge_migration.py
```

Expected: failure because the four tables/revision do not exist.

- [x] **Step 3: Implement revision 0005**

Create revision metadata:

```python
revision = "20260726_0005"
down_revision = "20260720_0004"
```

Create all columns, indexes, checks, unique constraints, and foreign keys
exactly as defined by the ORM/spec. Use dependency order for upgrade and
reverse order for downgrade.

- [x] **Step 4: Run migration GREEN and focused suite**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q `
  tests\test_knowledge_models.py `
  tests\test_knowledge_schemas.py `
  tests\test_knowledge_migration.py `
  tests\test_migrations.py `
  tests\test_agent_migrations.py
```

Expected: all focused tests pass.

- [x] **Step 5: Run temporary Alembic gates**

Create one system-temporary directory, resolve and verify its absolute path,
set `DATABASE_URL` only to a SQLite file inside it, then run:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
```

Expected head: `20260726_0005`. Remove only the verified temporary directory
after all commands finish and confirm it no longer exists.

---

### Task 5: Synchronize documentation and complete verification

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this implementation plan's observed evidence/checklists

**Interfaces:**
- Consumes: the verified schema and complete diff.
- Produces: accurate current-stage documentation and a manual-commit handoff.

- [x] **Step 1: Update current truth**

Record completed scope through `P3-M1-S6`, the four SQLite tables, ownership
and status/hash/metadata/vector/query bridge fields, revision
`20260726_0005`, and the explicit deferral of S7+ services/APIs and all M2+
runtime.

Do not create `docs/20-knowledge-base-design.md`; it remains S9.

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

- [x] **Step 3: Run repository gates**

Require:

- all Markdown local links/images resolve;
- added-line high-confidence secret hits are zero;
- tracked/untracked generated database artifacts are zero;
- `web_fetch` runtime additions are zero;
- later-Plan runtime additions are zero;
- service/API/upload/parser/Embedding/Qdrant-client/frontend additions are
  zero;
- no real Provider host is added;
- `git diff --check` has zero findings;
- staged paths are zero;
- `HEAD == origin/main == dbdda4416b548ed805d1d3f1421f21a81c830f88`
  throughout the batch.

- [x] **Step 4: Perform Codex self-review**

Classify every finding as:

- must fix;
- later Step;
- accepted limitation;
- not applicable.

Fix must-fix findings and rerun affected verification. Do not request external
review and do not commit.

- [x] **Step 5: Prepare the manual handoff**

State whether S4～S6 are complete and whether the repository may enter
`P3-M1-S7～S9`. Suggested commit message:

```text
feat(knowledge): add plan 3 persistence models
```

## Observed Execution Evidence

- ORM RED: collection ImportError for the four absent model exports.
- ORM GREEN: `19 passed`; the later self-review cascade regression also passed.
- Schema RED: collection ImportError for the absent schema exports.
- ORM/schema GREEN: `48 passed`.
- Migration RED: `1 failed, 1 passed` because the four Plan 3 tables were absent.
- Migration GREEN: `2 passed`; the focused model/schema/migration set reached
  `57 passed`.
- Complete backend regression after the self-review test: `558 passed,
  1 warning`; the warning is the known Starlette TestClient/httpx deprecation.
- Dependency check: `No broken requirements found.`
- Frontend: `18 files / 90 tests`, typecheck, and production build with
  `1813 modules` passed.
- Fresh temporary SQLite: `upgrade head`, `current --check-heads`, and
  `alembic check` passed at `20260726_0005`; the verified system-temp directory
  was removed. The project database was not read or changed.
- Repository gates: 83 Markdown files, 67 local links/images, 0 missing;
  secret, real Provider host, `web_fetch` runtime, later-Plan runtime,
  out-of-batch path, and generated database artifact hits were all zero.
- Git: `git diff --check` reported no findings, staged paths remained zero, and
  `HEAD == origin/main == dbdda4416b548ed805d1d3f1421f21a81c830f88`.
