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
