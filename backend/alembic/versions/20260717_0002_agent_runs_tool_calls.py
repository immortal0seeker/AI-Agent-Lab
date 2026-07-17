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
