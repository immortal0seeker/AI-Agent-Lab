"""Enforce AgentRun and user Message conversation consistency.

Revision ID: 20260718_0003
Revises: 20260717_0002
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260718_0003"
down_revision: str | None = "20260717_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_inconsistent_agent_message_rows() -> bool:
    result = op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM agent_runs AS ar
            LEFT JOIN messages AS m ON m.id = ar.user_message_id
            WHERE ar.user_message_id IS NOT NULL
              AND (
                  m.id IS NULL
                  OR ar.conversation_id <> m.conversation_id
              )
            LIMIT 1
            """
        )
    )
    return result.first() is not None


def upgrade() -> None:
    if _has_inconsistent_agent_message_rows():
        raise RuntimeError(
            "Cannot enforce AgentRun message conversation integrity: "
            "inconsistent audit rows exist"
        )

    with op.batch_alter_table("messages") as batch_op:
        batch_op.create_unique_constraint(
            "uq_messages_id_conversation_id",
            ["id", "conversation_id"],
        )

    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_constraint(
            "fk_agent_runs_user_message_id_messages",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_agent_runs_user_message_conversation_messages",
            "messages",
            ["user_message_id", "conversation_id"],
            ["id", "conversation_id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_constraint(
            "fk_agent_runs_user_message_conversation_messages",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_agent_runs_user_message_id_messages",
            "messages",
            ["user_message_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint(
            "uq_messages_id_conversation_id",
            type_="unique",
        )
