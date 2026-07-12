# Plan 1 M2 Database Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `P1-M2-S1` through `P1-M2-S3` with a migrated SQLite schema, typed SQLAlchemy ORM models, and Pydantic create/read contracts.

**Architecture:** Backend settings provide `DATABASE_URL` to a focused SQLAlchemy engine/session module. UUID-based ORM models share one declarative base, Alembic owns schema creation, and Pydantic schemas convert ORM instances without introducing services or API routes.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0.51 series, Alembic 1.18.5 series, SQLite, Pydantic 2, pytest 9.

## Global Constraints

- Work only on `P1-M2-S1` through `P1-M2-S3`.
- Do not add Provider, Chat, Streaming, service, API, or frontend behavior.
- Use UUID v4 identifiers exposed as `uuid.UUID`.
- Store timezone-naive datetimes with an explicit UTC semantic convention.
- Enable SQLite foreign key enforcement for every application-created connection.
- Use a stable SQLAlchemy naming convention for constraints and indexes.
- Index all foreign-key columns used for conversation/message lookup and cascade checks.
- Treat SQLite as the default and long-term supported primary database; PostgreSQL is optional compatibility, not a required migration path.
- Preserve reasonable portability through SQLAlchemy and Alembic without adding PostgreSQL-specific infrastructure preemptively.
- Keep the root `requirements.txt` and `backend/pyproject.toml` synchronized.
- Do not read or create real `.env` files or credentials.
- The user creates the Git commit manually; implementation checkpoints must not run `git commit`.

---

### Task 1: Database Dependencies, Settings, Base, And Session

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `requirements.txt`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/tests/test_db_session.py`

**Interfaces:**
- Consumes: `app.core.config.get_settings() -> Settings`
- Produces: `Base`, `create_db_engine(database_url: str) -> Engine`, `engine`, and `SessionLocal`

- [ ] **Step 1: Write failing database configuration tests**

Create `backend/tests/test_db_session.py` with tests that instantiate `Settings` using an explicit `DATABASE_URL`, call `create_db_engine()` for a temporary SQLite file, and assert `PRAGMA foreign_keys` returns `1`.

```python
from pathlib import Path

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import create_db_engine


def test_settings_accepts_database_url(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'settings.db'}"

    settings = Settings(DATABASE_URL=database_url)

    assert settings.database_url == database_url


def test_sqlite_engine_enables_foreign_keys(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'engine.db'}")

    with engine.connect() as connection:
        enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    engine.dispose()
    assert enabled == 1
```

- [ ] **Step 2: Run the focused test and verify RED**

Run from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_db_session.py -q
```

Expected: FAIL because SQLAlchemy and/or `app.db` is not available yet.

- [ ] **Step 3: Add synchronized dependency declarations**

Add these runtime dependencies to `backend/pyproject.toml` and root `requirements.txt`:

```toml
"sqlalchemy>=2.0.51,<2.1.0",
"alembic>=1.18.5,<1.19.0",
```

Install the backend package from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pip install -e .[dev] --no-build-isolation
```

If dependency download is blocked by the sandbox, request escalated network execution for this exact install command.

- [ ] **Step 4: Add database configuration and session implementation**

Add this field to `Settings` and mirror it in `backend/.env.example`:

```python
database_url: str = Field(
    default="sqlite:///./ai_agent_lab.db",
    alias="DATABASE_URL",
)
```

Create `Base` as a SQLAlchemy 2 declarative base with stable metadata naming:

```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

Implement `create_db_engine()` so SQLite gets `check_same_thread=False` and a connect event that executes `PRAGMA foreign_keys=ON`. Construct module-level `engine` from settings and `SessionLocal` with `autocommit=False`, `autoflush=False`, and `expire_on_commit=False`.

- [ ] **Step 5: Run the focused test and verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_db_session.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Review checkpoint**

Run `git diff --check` and inspect only Task 1 files. Do not commit.

---

### Task 2: UUID ORM Models And Relationship Behavior

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/common.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/llm_call.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.db.base.Base`, SQLAlchemy `Uuid(as_uuid=True)`, and `create_db_engine()`
- Produces: `Conversation`, `Message`, `LLMCall`, and `utc_now() -> datetime`

- [ ] **Step 1: Write failing persistence and relationship tests**

Create a pytest fixture that uses a temporary SQLite database, calls `Base.metadata.create_all(engine)`, and yields a `Session`. Add tests for:

```python
def test_models_create_and_load_relationships(session: Session) -> None:
    conversation = Conversation()
    message = Message(conversation=conversation, role="user", content="Hello")
    llm_call = LLMCall(
        conversation=conversation,
        message=message,
        provider="test-provider",
        model="test-model",
    )
    session.add(conversation)
    session.commit()

    assert isinstance(conversation.id, UUID)
    assert message in conversation.messages
    assert llm_call in conversation.llm_calls
    assert llm_call.status == "pending"
```

Also add one test that deletes a conversation and verifies both child tables are empty, and one test that deletes only a message and verifies its LLM call remains with `message_id is None`.

- [ ] **Step 2: Run model tests and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_models.py -q
```

Expected: FAIL because `app.models` does not exist.

- [ ] **Step 3: Implement shared UTC timestamp helper**

Create `utc_now()` in `backend/app/models/common.py`:

```python
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
```

- [ ] **Step 4: Implement Conversation**

Use SQLAlchemy 2 `Mapped`/`mapped_column` declarations with:

```python
id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
title: Mapped[str] = mapped_column(String(255), default="New conversation")
default_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
default_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
created_at: Mapped[datetime] = mapped_column(DateTime(), default=utc_now)
updated_at: Mapped[datetime] = mapped_column(DateTime(), default=utc_now, onupdate=utc_now)
```

Define `messages` and `llm_calls` relationships with `cascade="all, delete-orphan"` and `passive_deletes=True`.

- [ ] **Step 5: Implement Message**

Use an indexed required UUID foreign key with `ondelete="CASCADE"`, required `role: String(32)` and `content: Text`, optional provider/model fields, and a UTC `created_at`. Define the conversation back-reference and an LLM call relationship without delete-orphan cascade.

- [ ] **Step 6: Implement LLMCall**

Use an indexed required conversation UUID foreign key with `ondelete="CASCADE"` and indexed optional message UUID foreign key with `ondelete="SET NULL"`. Define provider/model, optional token counters, `Numeric(18, 8)` estimated cost, optional latency, status default `pending`, optional error text, and UTC creation timestamp.

- [ ] **Step 7: Export all models and verify GREEN**

Import `Conversation`, `Message`, and `LLMCall` from `app/models/__init__.py`, then run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_models.py -q
```

Expected: all model tests pass with no SQLAlchemy mapper warnings.

- [ ] **Step 8: Review checkpoint**

Run `git diff --check` and inspect model fields against the approved design. Do not commit.

---

### Task 3: Alembic Configuration And Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/20260712_0001_initial_schema.py`
- Create: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `Settings.database_url`, `Base.metadata`, and imports from `app.models`
- Produces: Alembic revision `20260712_0001` and three migrated tables

- [ ] **Step 1: Write failing migration test**

Create `backend/tests/test_migrations.py`. Set `DATABASE_URL` to a temporary SQLite file, clear `get_settings` cache, construct `alembic.config.Config`, run `command.upgrade(config, "head")`, and inspect table names, stable constraint names, and foreign-key indexes:

```python
def test_upgrade_head_creates_initial_tables(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    database_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    tables = set(inspect(create_engine(f"sqlite:///{database_path}")).get_table_names())
    assert {"alembic_version", "conversations", "messages", "llm_calls"} <= tables
```

Restore the settings cache in test cleanup.

- [ ] **Step 2: Run migration test and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_migrations.py -q
```

Expected: FAIL because `backend/alembic.ini` does not exist.

- [ ] **Step 3: Add Alembic runtime configuration**

Configure `backend/alembic.ini` with `script_location = %(here)s/alembic`. In `env.py`, import all models, set `target_metadata = Base.metadata`, set the URL from `get_settings().database_url`, and support both offline and online migrations.

- [ ] **Step 4: Add deterministic initial migration**

Create revision `20260712_0001` with `down_revision = None`. The upgrade must create tables in this order:

```text
conversations -> messages -> llm_calls
```

Use SQLAlchemy UUID, String, Text, DateTime, Integer, and Numeric types matching the ORM. Add named `CASCADE` and `SET NULL` foreign-key actions plus indexes for all three foreign-key columns. The downgrade drops indexes and tables in reverse order.

- [ ] **Step 5: Run migration test and verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_migrations.py -q
```

Expected: upgrade/schema and downgrade tests pass.

- [ ] **Step 6: Verify CLI migration lifecycle**

From `backend`, set a temporary test URL for the command process and run upgrade, current, and downgrade against a disposable database. Do not use or inspect a real `.env` file.

- [ ] **Step 7: Review checkpoint**

Compare every migration column type, nullability rule, default, and foreign-key action to ORM metadata. Confirm `Conversation.id`, `Message.id`, and `LLMCall.id` all remain `UUID` in Python and `Uuid(as_uuid=True)` in SQLAlchemy. Then run `git diff --check`. Do not commit.

---

### Task 4: Pydantic Create And Read Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/conversation.py`
- Create: `backend/app/schemas/message.py`
- Create: `backend/app/schemas/llm_call.py`
- Create: `backend/tests/test_schemas.py`

**Interfaces:**
- Consumes: ORM attributes from `Conversation`, `Message`, and `LLMCall`
- Produces: `ConversationCreate`, `ConversationRead`, `MessageCreate`, `MessageRead`, `LLMCallCreate`, and `LLMCallRead`

- [ ] **Step 1: Write failing schema tests**

Cover create defaults, required fields, ORM conversion, and malformed UUID input. Representative assertions:

```python
def test_conversation_create_defaults() -> None:
    schema = ConversationCreate()
    assert schema.title == "New conversation"
    assert schema.default_provider is None


def test_message_create_rejects_invalid_conversation_id() -> None:
    with pytest.raises(ValidationError):
        MessageCreate(conversation_id="not-a-uuid", role="user", content="Hello")
```

Create ORM instances for each read schema, flush them through the temporary database session, and validate with `SchemaRead.model_validate(instance)`.

- [ ] **Step 2: Run schema tests and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_schemas.py -q
```

Expected: FAIL because `app.schemas` does not exist.

- [ ] **Step 3: Implement conversation schemas**

`ConversationCreate` has title default `New conversation` and optional default provider/model. `ConversationRead` adds UUID id plus created/updated datetimes and uses `ConfigDict(from_attributes=True)`.

- [ ] **Step 4: Implement message schemas**

`MessageCreate` requires UUID conversation ID, role, and content, with optional provider/model. `MessageRead` adds UUID id and creation timestamp and supports ORM attributes.

- [ ] **Step 5: Implement LLM call schemas**

`LLMCallCreate` requires conversation UUID, provider, and model; message UUID, metrics, and error are optional; status defaults to `pending`. `LLMCallRead` adds UUID id and creation timestamp and supports ORM attributes. Use `Decimal | None` for estimated cost.

- [ ] **Step 6: Export schemas and verify GREEN**

Export all six contracts from `app/schemas/__init__.py`, then run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_schemas.py -q
```

Expected: all schema tests pass.

- [ ] **Step 7: Review checkpoint**

Check that no update/service/API schema was added, then run `git diff --check`. Do not commit.

---

### Task 5: Documentation, Batch Status, And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: verified migration commands and implemented file structure
- Produces: accurate Batch 4 startup/migration guidance and status

- [ ] **Step 1: Update operational documentation**

Document these backend commands without claiming Provider or Chat support:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m pytest -q
```

Explain the default SQLite location, `DATABASE_URL`, migration ownership, and the three current tables. Update architecture docs to describe UUIDs, relationships, and UTC convention.

- [ ] **Step 2: Update Plan 1 progress only after tests pass**

Set Batch 4 to `已完成`, update README completed range to `P1-M2-S1` through `P1-M2-S3`, and set the next batch to `P1-M2-S4` through `P1-M2-S6`.

- [ ] **Step 3: Run complete backend verification**

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: all tests pass, migration reaches head, and Uvicorn reaches `Application startup complete`. A timeout may terminate the long-running server after readiness is observed.

- [ ] **Step 4: Run unchanged frontend regression checks**

From `frontend`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: all pass. If the build cannot write ignored `frontend/dist` due sandbox permissions, rerun only `npm run build` with escalation.

- [ ] **Step 5: Run final repository checks**

From the repository root:

```powershell
git diff --check
git status --short
```

Inspect changed files for accidental secrets, real `.env` files, generated SQLite databases, debug output, and work outside Batch 4.

- [ ] **Step 6: Codex self-review and handoff**

Classify findings as must fix, later batch, limitation, or not applicable. Because this batch establishes database models, recommend Claude Code review if model or migration risk remains; otherwise state that the mandatory M2-end review is still scheduled after Batch 6. Provide a suggested manual commit message such as:

```text
feat(db): add sqlite models migrations and schemas
```
