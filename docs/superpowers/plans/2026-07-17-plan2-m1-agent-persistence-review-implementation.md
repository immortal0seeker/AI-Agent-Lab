# Plan 2 M1 Agent Persistence and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository instructions prohibit sub-agent execution for this batch.

**Goal:** Complete `P2-M1-S7` through `P2-M1-S8` with migrated AgentRun/ToolCall audit models and an accurate M1 architecture/review record.

**Architecture:** SQLAlchemy models store future Agent execution records without adding an execution service. A composite AgentRun key keeps each ToolCall's direct Conversation lookup consistent with its owning run, while Alembic owns the additive SQLite schema and formal docs describe the M1 boundary.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0.51 series, Alembic 1.18.5 series, SQLite, pytest 9, React/TypeScript regression checks, and Markdown documentation.

## Global Constraints

- Work only on `P2-M1-S7` through `P2-M1-S8`.
- Do not add Pydantic Agent schemas, persistence services, Tool execution, built-in tools, Provider tool calling, Agent Loop, API routes, frontend behavior, RAG, Memory, MCP, or later-Plan capabilities.
- Keep SQLite as the default and long-term supported primary database.
- Use UUID v4 primary keys and timezone-naive UTC datetimes, matching existing models.
- Keep database UUID identity separate from the required string `tool_call_id` correlation ID.
- Enforce AgentRun/ToolCall status sets, non-negative latency, same-Conversation ownership, and per-run correlation-ID uniqueness in the database.
- Run migrations only against new temporary SQLite databases; never inspect, migrate, delete, or rebuild `backend/ai_agent_lab.db`.
- Do not read a real `.env`, secret, credential, SSH key, browser profile, or system credential store.
- Do not call a real or paid Provider.
- Preserve the released `v0.1.0` Git/tag history and CHANGELOG entry.
- Do not run Claude Code unless the user explicitly requests it; record that it was not run.
- Do not stage, commit, push, tag, or create a PR; the user commits manually.

---

### Task 1: AgentRun and ToolCall ORM Models

**Files:**
- Create: `backend/tests/test_agent_models.py`
- Create: `backend/app/models/agent_run.py`
- Create: `backend/app/models/tool_call.py`
- Modify: `backend/app/models/conversation.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Consumes: `Base`, `utc_now()`, `Conversation`, and `Message`.
- Produces: `AgentRun` with `conversation`, optional `user_message`, and owned `tool_calls`.
- Produces: `ToolCall` with UUID `id`, string `tool_call_id`, composite AgentRun ownership, JSON payloads, and status/timing fields.

- [ ] **Step 1: Write the failing ORM model tests**

Create `backend/tests/test_agent_models.py`:

```python
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import AgentRun, Conversation, Message, ToolCall


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'agent-models.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_run(
    session: Session,
    *,
    conversation: Conversation | None = None,
) -> tuple[Conversation, Message, AgentRun]:
    conversation = conversation or Conversation()
    message = Message(conversation=conversation, role="user", content="Use a tool")
    run = AgentRun(
        conversation=conversation,
        user_message=message,
        goal="Answer with one safe tool call",
    )
    session.add(conversation)
    session.flush()
    return conversation, message, run


def create_tool_call(
    run: AgentRun,
    *,
    tool_call_id: str = "call-1",
    conversation_id: UUID | None = None,
) -> ToolCall:
    return ToolCall(
        agent_run=run,
        conversation_id=conversation_id or run.conversation_id,
        tool_call_id=tool_call_id,
        tool_name="echo",
        arguments_json={"message": "hello"},
        result_json={"success": True, "content": "hello"},
    )


def test_agent_models_persist_relationships_json_and_defaults(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, message, run = create_run(session)
    tool_call = create_tool_call(run)
    session.add(tool_call)
    session.commit()
    session.expire_all()

    loaded = session.scalar(select(AgentRun).where(AgentRun.id == run.id))

    assert loaded is not None
    assert isinstance(loaded.id, UUID)
    assert loaded.conversation_id == conversation.id
    assert loaded.user_message_id == message.id
    assert loaded.status == "created"
    assert loaded.created_at.tzinfo is None
    assert loaded.tool_calls[0].status == "pending"
    assert loaded.tool_calls[0].tool_call_id == "call-1"
    assert loaded.tool_calls[0].arguments_json == {"message": "hello"}
    assert loaded.tool_calls[0].result_json == {
        "success": True,
        "content": "hello",
    }


def test_tool_call_argument_defaults_are_isolated(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, _, run = create_run(session)
    first = ToolCall(
        agent_run=run,
        conversation_id=conversation.id,
        tool_call_id="call-1",
        tool_name="echo",
    )
    second = ToolCall(
        agent_run=run,
        conversation_id=conversation.id,
        tool_call_id="call-2",
        tool_name="echo",
    )
    session.add_all([first, second])
    session.commit()

    first.arguments_json["message"] = "first"

    assert second.arguments_json == {}
    assert first.arguments_json is not second.arguments_json


def test_deleting_conversation_cascades_agent_audit_rows(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, _, run = create_run(session)
    session.add(create_tool_call(run))
    session.commit()

    session.delete(conversation)
    session.commit()

    assert session.scalars(select(AgentRun)).all() == []
    assert session.scalars(select(ToolCall)).all() == []


def test_deleting_agent_run_cascades_tool_calls(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, _, run = create_run(session)
    session.add(create_tool_call(run))
    session.commit()

    session.delete(run)
    session.commit()

    assert session.scalars(select(ToolCall)).all() == []


def test_deleting_user_message_preserves_agent_audit_rows(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, message, run = create_run(session)
    tool_call = create_tool_call(run)
    session.add(tool_call)
    session.commit()
    run_id = run.id
    tool_call_id = tool_call.id

    session.delete(message)
    session.commit()

    preserved_run = session.get(AgentRun, run_id)
    assert preserved_run is not None
    assert preserved_run.user_message_id is None
    assert session.get(ToolCall, tool_call_id) is not None


def test_agent_run_rejects_invalid_status_and_negative_latency(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation = Conversation()
    session.add(
        AgentRun(
            conversation=conversation,
            goal="invalid status",
            status="unknown",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    conversation = Conversation()
    session.add(
        AgentRun(
            conversation=conversation,
            goal="invalid latency",
            latency_ms=-1,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_tool_call_rejects_invalid_status_and_negative_latency(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    conversation, _, run = create_run(session)
    invalid_status = create_tool_call(run)
    invalid_status.status = "unknown"
    session.add(invalid_status)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    conversation, _, run = create_run(session)
    invalid_latency = create_tool_call(run, tool_call_id="call-2")
    invalid_latency.latency_ms = -1
    session.add(invalid_latency)
    with pytest.raises(IntegrityError):
        session.commit()


def test_tool_call_id_is_unique_within_one_run(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, _, run = create_run(session)
    session.add_all([create_tool_call(run), create_tool_call(run)])

    with pytest.raises(IntegrityError):
        session.commit()


def test_tool_call_conversation_must_match_agent_run(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    _, _, run = create_run(session)
    other_conversation = Conversation()
    session.add(other_conversation)
    session.flush()
    mismatched = ToolCall(
        agent_run_id=run.id,
        conversation_id=other_conversation.id,
        tool_call_id="call-mismatch",
        tool_name="echo",
    )
    session.add(mismatched)

    with pytest.raises(IntegrityError):
        session.commit()
```

- [ ] **Step 2: Run the ORM tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_models.py -q
```

Expected: collection fails because `AgentRun` and `ToolCall` do not exist.

- [ ] **Step 3: Implement AgentRun**

Create `backend/app/models/agent_run.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.tool_call import ToolCall


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'running', 'waiting_tool', 'completed', "
            "'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_agent_runs_latency_ms_non_negative",
        ),
        UniqueConstraint(
            "id",
            "conversation_id",
            name="uq_agent_runs_id_conversation_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="created",
    )
    goal: Mapped[str] = mapped_column(Text(), nullable=False)
    final_answer: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    conversation: Mapped[Conversation] = relationship(back_populates="agent_runs")
    user_message: Mapped[Message | None] = relationship()
    tool_calls: Mapped[list[ToolCall]] = relationship(
        back_populates="agent_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
```

- [ ] **Step 4: Implement ToolCall**

Create `backend/app/models/tool_call.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun


class ToolCall(Base):
    __tablename__ = "tool_calls"
    __table_args__ = (
        ForeignKeyConstraint(
            ["agent_run_id", "conversation_id"],
            ["agent_runs.id", "agent_runs.conversation_id"],
            name="fk_tool_calls_agent_run_conversation_agent_runs",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'success', 'failed', "
            "'timeout', 'blocked')",
            name="ck_tool_calls_status",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_tool_calls_latency_ms_non_negative",
        ),
        UniqueConstraint(
            "agent_run_id",
            "tool_call_id",
            name="uq_tool_calls_agent_run_id_tool_call_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tool_call_id: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON(),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    agent_run: Mapped[AgentRun] = relationship(back_populates="tool_calls")
```

- [ ] **Step 5: Connect Conversation and export the models**

In `backend/app/models/conversation.py`, add the `AgentRun` type-only import and:

```python
agent_runs: Mapped[list[AgentRun]] = relationship(
    back_populates="conversation",
    cascade="all, delete-orphan",
    passive_deletes=True,
)
```

Update `backend/app/models/__init__.py` to export:

```python
from app.models.agent_run import AgentRun
from app.models.conversation import Conversation
from app.models.llm_call import LLMCall
from app.models.message import Message
from app.models.tool_call import ToolCall

__all__ = ["AgentRun", "Conversation", "LLMCall", "Message", "ToolCall"]
```

- [ ] **Step 6: Run the ORM tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_models.py -q
```

Expected: all Agent persistence tests pass with no SQLAlchemy mapper warning.

- [ ] **Step 7: Run existing model regressions**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_agent_models.py -q
```

Expected: Plan 1 and Plan 2 ORM relationships and delete semantics all pass.

---

### Task 2: Additive Agent Persistence Migration

**Files:**
- Create: `backend/tests/test_agent_migrations.py`
- Create: `backend/alembic/versions/20260717_0002_agent_runs_tool_calls.py`

**Interfaces:**
- Consumes: revision `20260712_0001` and ORM metadata from Task 1.
- Produces: revision `20260717_0002` with `agent_runs` and `tool_calls` tables.
- Produces: reversible upgrade/downgrade behavior on fresh SQLite databases.

- [ ] **Step 1: Write the failing migration tests**

Create `backend/tests/test_agent_migrations.py`:

```python
from pathlib import Path

from alembic import command
from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).parents[1]


def migration_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> tuple[Config, str]:
    database_url = f"sqlite:///{tmp_path / 'agent-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    return Config(str(BACKEND_ROOT / "alembic.ini")), database_url


def test_upgrade_head_creates_agent_persistence_schema(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {"agent_runs", "tool_calls"} <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("agent_runs")} == {
        "id",
        "conversation_id",
        "user_message_id",
        "status",
        "goal",
        "final_answer",
        "error_message",
        "started_at",
        "ended_at",
        "latency_ms",
        "created_at",
    }
    assert {column["name"] for column in inspector.get_columns("tool_calls")} == {
        "id",
        "tool_call_id",
        "agent_run_id",
        "conversation_id",
        "tool_name",
        "arguments_json",
        "result_json",
        "status",
        "error_message",
        "started_at",
        "ended_at",
        "latency_ms",
        "created_at",
    }

    agent_foreign_keys = {
        tuple(foreign_key["constrained_columns"]): foreign_key
        for foreign_key in inspector.get_foreign_keys("agent_runs")
    }
    assert agent_foreign_keys[("conversation_id",)]["options"]["ondelete"] == "CASCADE"
    assert agent_foreign_keys[("user_message_id",)]["options"]["ondelete"] == "SET NULL"

    tool_foreign_key = inspector.get_foreign_keys("tool_calls")[0]
    assert tool_foreign_key["constrained_columns"] == [
        "agent_run_id",
        "conversation_id",
    ]
    assert tool_foreign_key["referred_columns"] == ["id", "conversation_id"]
    assert tool_foreign_key["options"]["ondelete"] == "CASCADE"

    assert {index["name"] for index in inspector.get_indexes("agent_runs")} == {
        "ix_agent_runs_conversation_id",
        "ix_agent_runs_user_message_id",
    }
    assert {index["name"] for index in inspector.get_indexes("tool_calls")} == {
        "ix_tool_calls_agent_run_id",
        "ix_tool_calls_conversation_id",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("agent_runs")
    } == {"uq_agent_runs_id_conversation_id"}
    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("tool_calls")
    } == {"uq_tool_calls_agent_run_id_tool_call_id"}
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("agent_runs")
    } == {
        "ck_agent_runs_latency_ms_non_negative",
        "ck_agent_runs_status",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("tool_calls")
    } == {
        "ck_tool_calls_latency_ms_non_negative",
        "ck_tool_calls_status",
    }
    engine.dispose()


def test_downgrade_to_plan1_removes_only_agent_tables(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "20260712_0001")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {"conversations", "messages", "llm_calls"} <= tables
    assert "agent_runs" not in tables
    assert "tool_calls" not in tables
    engine.dispose()
```

- [ ] **Step 2: Run the migration tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_migrations.py -q
```

Expected: the head-schema test fails because the new revision and tables do not
exist.

- [ ] **Step 3: Implement revision 20260717_0002**

Create `backend/alembic/versions/20260717_0002_agent_runs_tool_calls.py`:

```python
"""Create AgentRun and ToolCall audit tables.

Revision ID: 20260717_0002
Revises: 20260712_0001
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_0002"
down_revision: str | None = "20260712_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_message_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_agent_runs_latency_ms_non_negative",
        ),
        sa.CheckConstraint(
            "status IN ('created', 'running', 'waiting_tool', 'completed', "
            "'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_agent_runs_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id"],
            ["messages.id"],
            name="fk_agent_runs_user_message_id_messages",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
        sa.UniqueConstraint(
            "id",
            "conversation_id",
            name="uq_agent_runs_id_conversation_id",
        ),
    )
    op.create_index(
        "ix_agent_runs_conversation_id",
        "agent_runs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_runs_user_message_id",
        "agent_runs",
        ["user_message_id"],
        unique=False,
    )
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tool_call_id", sa.String(length=255), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_tool_calls_latency_ms_non_negative",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'success', 'failed', "
            "'timeout', 'blocked')",
            name="ck_tool_calls_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id", "conversation_id"],
            ["agent_runs.id", "agent_runs.conversation_id"],
            name="fk_tool_calls_agent_run_conversation_agent_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tool_calls"),
        sa.UniqueConstraint(
            "agent_run_id",
            "tool_call_id",
            name="uq_tool_calls_agent_run_id_tool_call_id",
        ),
    )
    op.create_index(
        "ix_tool_calls_agent_run_id",
        "tool_calls",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_calls_conversation_id",
        "tool_calls",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tool_calls_conversation_id", table_name="tool_calls")
    op.drop_index("ix_tool_calls_agent_run_id", table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_index("ix_agent_runs_user_message_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_conversation_id", table_name="agent_runs")
    op.drop_table("agent_runs")
```

- [ ] **Step 4: Run focused migration tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_migrations.py tests/test_migrations.py -q
```

Expected: the new revision tests and existing initial-schema lifecycle tests all
pass.

- [ ] **Step 5: Run Alembic lifecycle checks on one disposable database**

Run from `backend/` in PowerShell:

```powershell
$database = Join-Path ([System.IO.Path]::GetTempPath()) "ai-agent-lab-s7-$([guid]::NewGuid()).sqlite"
$env:DATABASE_URL = "sqlite:///$($database -replace '\\','/')"
try {
    ..\.venv\Scripts\python.exe -m alembic upgrade head
    ..\.venv\Scripts\python.exe -m alembic current --check-heads
    ..\.venv\Scripts\python.exe -m alembic check
    ..\.venv\Scripts\python.exe -m alembic downgrade 20260712_0001
    ..\.venv\Scripts\python.exe -m alembic upgrade head
} finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $database) {
        Remove-Item -LiteralPath $database
    }
}
```

Expected: upgrade reaches `20260717_0002`, current reports the head, Alembic
reports no new upgrade operations, downgrade reaches `20260712_0001`, and
re-upgrade succeeds. The generated path is under the system temporary directory
and is deleted after the checks.

---

### Task 3: M1 Design Documentation, Review, and Full Verification

**Files:**
- Create: `docs/10-tool-calling-design.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Verify: all Task 1-2 code/tests plus the approved design and this plan.

**Interfaces:**
- Consumes: verified S1-S7 Tool and persistence contracts.
- Produces: accurate M1 architecture, limitations, acceptance evidence, and next-batch boundary.

- [ ] **Step 1: Create the formal Tool Calling design document**

Create `docs/10-tool-calling-design.md` with these sections and facts:

```markdown
# Tool Calling Design

## Current Scope

Plan 2 M1 establishes Tool contracts, discovery, validation, read-only security,
and persistence models. It does not yet execute a Tool, expose an Agent API, or
call a Provider with Tool schemas.

## Tool Boundary

`Tool` owns normalized metadata, a JSON parameter schema, permission label,
timeout, and asynchronous `run(arguments) -> ToolResult`. `ToolResult` keeps
success, content, structured data, error, and metadata consistent. ToolCall
transport schemas keep Provider correlation IDs separate from ORM identities.

## Registry and Validation

`ToolRegistry` registers exact names, rejects duplicates, preserves order, and
exports defensive OpenAI-compatible function schemas. Draft 2020-12 validation
checks Tool schemas and arguments before future execution. Validation errors
contain safe paths/rules and never echo rejected argument values.

## Read-only Security

Paths are workspace-relative and resolved before use. Absolute, drive, UNC,
parent traversal, `.env`, sensitive directories, private keys, Windows path
aliases, and alternate data streams are rejected. File-size and directory-depth
limits are pure policy helpers. M1 does not read or enumerate files.

## Persistence

`AgentRun` records Conversation ownership, an optional user Message, simple
status, goal/final output/error, timing, and creation time. `ToolCall` uses a UUID
database ID plus a separate string `tool_call_id`, belongs to an AgentRun, keeps
direct Conversation lookup, stores JSON arguments/result, and records status and
timing. Composite and unique constraints prevent cross-Conversation ownership
and duplicate correlation IDs inside one run.

Deleting a Conversation removes its runs/calls. Deleting one user Message keeps
the audit record and nulls its link. Deleting an AgentRun removes its ToolCalls.

## Status Values

AgentRun: `created`, `running`, `waiting_tool`, `completed`, `failed`,
`cancelled`.

ToolCall: `pending`, `running`, `success`, `failed`, `timeout`, `blocked`.

These are integrity values, not a full runtime state machine.

## Current Data Flow

M1 provides definitions and storage only:

```text
Future Agent service -> AgentRun -> validated ToolCall -> ToolResult
```

No current route or service creates these records. Built-in tools, Provider
integration, Agent Loop transitions, API access, and frontend visualization are
scheduled in later Plan 2 milestones.

## Verification and Security Boundary

Tests use Mock Tools, `tmp_path`, and disposable SQLite databases. They do not
read a real `.env`, user database, credential, or call a real Provider.

## Deferred Work

- Agent persistence service and transactions
- built-in read-only tools
- Provider tool calling
- Simple Agent Loop
- Agent APIs and frontend ToolCall visualization
- Plan 4 Trace/replay/evaluation
```

- [ ] **Step 2: Correct current-stage documentation**

In `README.md` and `README_CN.md`, preserve `v0.1.0` as the current release but
replace the stale “no Plan 2 capability” text with:

```text
Current development stage: Plan 2 Milestone 1 is complete.
Completed Plan 2 scope: P2-M1-S1 through P2-M1-S8.
Next batch: P2-M2-S1 through P2-M2-S3.
```

Summarize the implemented Tool contracts, Registry, validation, security policy,
and AgentRun/ToolCall schema while stating that executable built-in tools,
Provider tool calling, Agent Loop, API, and frontend are not yet implemented.
Add `docs/10-tool-calling-design.md` to the current design-document links.

In `docs/00-project-overview.md`, update only the Current Stage section so it
retains the Plan 1 foundation record and adds the completed Plan 2 M1 foundation
plus next batch `P2-M2-S1～S3`.

In `docs/01-architecture.md`:

- update Current Architecture Stage to Plan 2 M1 complete on top of v0.1.0;
- add `tools/` to the backend repository structure;
- add `agent_runs` and `tool_calls` to Database Foundation with the delete,
  UUID/correlation-ID, JSON, status, and timing rules;
- add a Tool Calling Foundation section matching `docs/10-tool-calling-design.md`;
- leave Provider, Chat, frontend, and Plan 1 release facts unchanged.

Do not modify `CHANGELOG.md`; it records the released `v0.1.0` history.

- [ ] **Step 3: Run complete backend verification**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: all backend tests pass; only the accepted Starlette TestClient/httpx
deprecation warning may remain; dependency consistency is clean.

- [ ] **Step 4: Run unchanged frontend verification**

Run from `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: typecheck, the complete Vitest suite, and production build pass.

- [ ] **Step 5: Perform Codex M1 review**

Review S1-S7 contracts and classify findings as must fix, fix later, limitation,
or not applicable. Confirm:

- ORM and migration columns, types, nullability, constraints, indexes, and
  delete actions match exactly;
- ToolCall UUID identity and correlation identity remain separate;
- ToolCall Conversation ownership cannot differ from AgentRun ownership;
- invalid statuses, negative latency, duplicate correlation IDs, and delete
  semantics have tests;
- migrations only touched disposable SQLite;
- no Agent schema/service/API, builtin Tool, Provider tool support, Agent Loop,
  frontend, RAG, Memory, or MCP implementation exists;
- no secret or generated database/build artifact is tracked;
- current-stage docs no longer contradict implemented M1 behavior;
- Claude Code was not run because the user did not explicitly request it.

Fix every blocking finding with a failing regression test first and re-run the
affected plus full verification.

- [ ] **Step 6: Update the Plan 2 execution table after review passes**

In `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`:

- change Batch 3 to `已完成`;
- mark S7 `Codex（done）`;
- mark S8 `Codex（done；Claude Code 未运行）`;
- append an S7-S8 acceptance record containing exact observed focused/full test
  counts, migration lifecycle evidence, documentation links, security checks,
  the Codex review result, and the unchanged M2+ boundary;
- state that M1 and Batch 3 are complete and the next batch is
  `P2-M2-S1～S3`;
- leave Batch 4 and every M2+ Step unchanged.

- [ ] **Step 7: Run final repository checks**

Run from the repository root:

```powershell
git diff --check
git -c core.quotepath=false status --short --untracked-files=all
git -c core.quotepath=false diff --name-only
```

Run a credential/private-key pattern scan only across tracked and explicitly
changed files. Confirm no tracked `.env`, SQLite database, frontend build output,
S8+ Agent runtime path, builtin Tool directory, Provider/frontend implementation,
or unrelated change exists.

- [ ] **Step 8: Leave the verified batch for manual commit**

Do not stage or commit. Report exact verification evidence, changed files,
review classifications, Claude Code decision, residual limitations, next batch
`P2-M2-S1～S3`, and suggested commit:

```text
feat(agent): add run and tool call persistence foundation
```
