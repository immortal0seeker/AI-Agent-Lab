"""Create TraceRun and TraceStep observability foundation.

Revision ID: 20260802_0008
Revises: 20260801_0007
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260802_0008"
down_revision: str | None = "20260801_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trace_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("user_message_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("total_input_tokens", sa.Integer(), nullable=True),
        sa.Column("total_output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "run_type IN ('chat', 'agent', 'rag_query', 'rag_chat', "
            "'evaluation', 'tool')",
            name="ck_trace_runs_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', "
            "'cancelled')",
            name="ck_trace_runs_status",
        ),
        sa.CheckConstraint(
            "length(trim(input_text)) > 0",
            name="ck_trace_runs_input_text_not_blank",
        ),
        sa.CheckConstraint(
            "total_input_tokens IS NULL OR total_input_tokens >= 0",
            name="ck_trace_runs_total_input_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "total_output_tokens IS NULL OR total_output_tokens >= 0",
            name="ck_trace_runs_total_output_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_trace_runs_total_tokens_non_negative",
        ),
        sa.CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_trace_runs_estimated_cost_non_negative",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_trace_runs_latency_ms_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_trace_runs_conversation_id_conversations",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            name="fk_trace_runs_agent_run_id_agent_runs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id"],
            ["messages.id"],
            name="fk_trace_runs_user_message_id_messages",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id", "conversation_id"],
            ["agent_runs.id", "agent_runs.conversation_id"],
            name="fk_trace_runs_agent_run_conversation_agent_runs",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            name="fk_trace_runs_user_message_conversation_messages",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trace_runs"),
    )
    op.create_index(
        "ix_trace_runs_conversation_id",
        "trace_runs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_trace_runs_agent_run_id",
        "trace_runs",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_trace_runs_user_message_id",
        "trace_runs",
        ["user_message_id"],
        unique=False,
    )

    op.create_table(
        "trace_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trace_run_id", sa.Uuid(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "step_index > 0",
            name="ck_trace_steps_step_index_positive",
        ),
        sa.CheckConstraint(
            "step_type IN ('build_context', 'llm_call', 'tool_call', "
            "'rag_retrieve', 'query_rewrite', 'bm25_search', 'vector_search', "
            "'hybrid_fusion', 'parent_child_expand', 'rerank', "
            "'build_prompt', 'final_answer', 'eval_metric')",
            name="ck_trace_steps_step_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', "
            "'cancelled')",
            name="ck_trace_steps_status",
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_trace_steps_name_not_blank",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_trace_steps_latency_ms_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["trace_run_id"],
            ["trace_runs.id"],
            name="fk_trace_steps_trace_run_id_trace_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trace_steps"),
        sa.UniqueConstraint(
            "trace_run_id",
            "step_index",
            name="uq_trace_steps_trace_run_id_step_index",
        ),
    )
    op.create_index(
        "ix_trace_steps_trace_run_id",
        "trace_steps",
        ["trace_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trace_steps_trace_run_id", table_name="trace_steps")
    op.drop_table("trace_steps")
    op.drop_index("ix_trace_runs_user_message_id", table_name="trace_runs")
    op.drop_index("ix_trace_runs_agent_run_id", table_name="trace_runs")
    op.drop_index("ix_trace_runs_conversation_id", table_name="trace_runs")
    op.drop_table("trace_runs")
