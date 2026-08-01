"""Record requested Top-K on RAG query audits.

Revision ID: 20260801_0007
Revises: 20260801_0006
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_0007"
down_revision: str | None = "20260801_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("rag_queries") as batch_op:
        batch_op.add_column(
            sa.Column(
                "top_k",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("5"),
            )
        )
        batch_op.create_check_constraint(
            "ck_rag_queries_top_k_range",
            "top_k >= 1 AND top_k <= 100",
        )


def downgrade() -> None:
    with op.batch_alter_table("rag_queries") as batch_op:
        batch_op.drop_constraint(
            "ck_rag_queries_top_k_range",
            type_="check",
        )
        batch_op.drop_column("top_k")
