"""Add strict per-run ToolCall sequence.

Revision ID: 20260720_0004
Revises: 20260718_0003
Create Date: 2026-07-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260720_0004"
down_revision: str | None = "20260718_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tool_calls",
        sa.Column("sequence_index", sa.Integer(), nullable=True),
    )
    op.get_bind().execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY agent_run_id
                        ORDER BY created_at, id
                    ) AS sequence_index
                FROM tool_calls
            )
            UPDATE tool_calls
            SET sequence_index = (
                SELECT ranked.sequence_index
                FROM ranked
                WHERE ranked.id = tool_calls.id
            )
            """
        )
    )
    with op.batch_alter_table("tool_calls") as batch_op:
        batch_op.alter_column(
            "sequence_index",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_tool_calls_sequence_index_positive",
            "sequence_index > 0",
        )
        batch_op.create_unique_constraint(
            "uq_tool_calls_agent_run_id_sequence_index",
            ["agent_run_id", "sequence_index"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tool_calls") as batch_op:
        batch_op.drop_constraint(
            "uq_tool_calls_agent_run_id_sequence_index",
            type_="unique",
        )
        batch_op.drop_constraint(
            "ck_tool_calls_sequence_index_positive",
            type_="check",
        )
        batch_op.drop_column("sequence_index")
