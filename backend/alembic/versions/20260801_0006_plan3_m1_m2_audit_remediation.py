"""Harden Plan 3 M1/M2 database boundaries.

Revision ID: 20260801_0006
Revises: 20260726_0005
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_0006"
down_revision: str | None = "20260726_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_groups = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            "SELECT 1 FROM documents "
            "GROUP BY knowledge_base_id, file_hash HAVING COUNT(*) > 1"
            ") AS duplicate_document_groups"
        )
    ).scalar_one()
    if duplicate_groups:
        raise RuntimeError(
            "Plan 3 document hash uniqueness migration found "
            f"{duplicate_groups} duplicate group(s); review them manually."
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint(
            "fk_documents_knowledge_base_id_knowledge_bases",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_documents_knowledge_base_id_knowledge_bases",
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_documents_knowledge_base_id_file_hash",
            ["knowledge_base_id", "file_hash"],
        )

    with op.batch_alter_table("rag_queries") as batch_op:
        batch_op.drop_constraint(
            "fk_rag_queries_answer_message_conversation_messages",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_rag_queries_answer_message_conversation_messages",
            "messages",
            ["answer_message_id", "conversation_id"],
            ["id", "conversation_id"],
            ondelete="NO ACTION",
        )
        batch_op.create_foreign_key(
            "fk_rag_queries_answer_message_id_messages",
            "messages",
            ["answer_message_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("rag_queries") as batch_op:
        batch_op.drop_constraint(
            "fk_rag_queries_answer_message_id_messages",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_rag_queries_answer_message_conversation_messages",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_rag_queries_answer_message_conversation_messages",
            "messages",
            ["answer_message_id", "conversation_id"],
            ["id", "conversation_id"],
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint(
            "uq_documents_knowledge_base_id_file_hash",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_documents_knowledge_base_id_knowledge_bases",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_documents_knowledge_base_id_knowledge_bases",
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
            ondelete="CASCADE",
        )
