from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import utc_now
from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.retrieval import RagRetrievalRun


def enum_values_sql(enum_type: type[TraceRunType | TraceStatus | TraceStepType]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


class TraceRun(Base):
    __tablename__ = "trace_runs"
    __table_args__ = (
        CheckConstraint(
            f"run_type IN ({enum_values_sql(TraceRunType)})",
            name="ck_trace_runs_run_type",
        ),
        CheckConstraint(
            f"status IN ({enum_values_sql(TraceStatus)})",
            name="ck_trace_runs_status",
        ),
        CheckConstraint(
            "length(trim(input_text)) > 0",
            name="ck_trace_runs_input_text_not_blank",
        ),
        CheckConstraint(
            "total_input_tokens IS NULL OR total_input_tokens >= 0",
            name="ck_trace_runs_total_input_tokens_non_negative",
        ),
        CheckConstraint(
            "total_output_tokens IS NULL OR total_output_tokens >= 0",
            name="ck_trace_runs_total_output_tokens_non_negative",
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_trace_runs_total_tokens_non_negative",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_trace_runs_estimated_cost_non_negative",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_trace_runs_latency_ms_non_negative",
        ),
        ForeignKeyConstraint(
            ["agent_run_id", "conversation_id"],
            ["agent_runs.id", "agent_runs.conversation_id"],
            name="fk_trace_runs_agent_run_conversation_agent_runs",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["user_message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            name="fk_trace_runs_user_message_conversation_messages",
            ondelete="NO ACTION",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "conversations.id",
            name="fk_trace_runs_conversation_id_conversations",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "agent_runs.id",
            name="fk_trace_runs_agent_run_id_agent_runs",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )
    user_message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "messages.id",
            name="fk_trace_runs_user_message_id_messages",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_text: Mapped[str] = mapped_column(Text(), nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TraceStatus.PENDING.value,
    )
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_input_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    conversation: Mapped[Conversation | None] = relationship(
        back_populates="trace_runs",
        foreign_keys=[conversation_id],
    )
    agent_run: Mapped[AgentRun | None] = relationship(
        back_populates="trace_runs",
        foreign_keys=[agent_run_id],
    )
    user_message: Mapped[Message | None] = relationship(
        back_populates="trace_runs",
        foreign_keys=[user_message_id],
    )
    steps: Mapped[list[TraceStep]] = relationship(
        back_populates="trace_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TraceStep.step_index",
    )
    retrieval_runs: Mapped[list[RagRetrievalRun]] = relationship(
        back_populates="trace_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RagRetrievalRun.created_at",
    )


class TraceStep(Base):
    __tablename__ = "trace_steps"
    __table_args__ = (
        CheckConstraint(
            "step_index > 0",
            name="ck_trace_steps_step_index_positive",
        ),
        CheckConstraint(
            f"step_type IN ({enum_values_sql(TraceStepType)})",
            name="ck_trace_steps_step_type",
        ),
        CheckConstraint(
            f"status IN ({enum_values_sql(TraceStatus)})",
            name="ck_trace_steps_status",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_trace_steps_name_not_blank",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_trace_steps_latency_ms_non_negative",
        ),
        UniqueConstraint(
            "trace_run_id",
            "step_index",
            name="uq_trace_steps_trace_run_id_step_index",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    trace_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "trace_runs.id",
            name="fk_trace_steps_trace_run_id_trace_runs",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    step_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TraceStatus.PENDING.value,
    )
    input_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    output_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON(),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    trace_run: Mapped[TraceRun] = relationship(back_populates="steps")


@event.listens_for(TraceRun, "before_insert")
@event.listens_for(TraceRun, "before_update")
def validate_owned_trace_correlations(
    _: Any,
    __: Any,
    target: TraceRun,
) -> None:
    if target.conversation_id is None and (
        target.agent_run_id is not None or target.user_message_id is not None
    ):
        raise ValueError(
            "conversation_id is required for agent_run_id or user_message_id"
        )
