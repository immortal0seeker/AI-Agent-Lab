"""Create Plan 3 knowledge metadata tables.

Revision ID: 20260726_0005
Revises: 20260720_0004
Create Date: 2026-07-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260726_0005"
down_revision: str | None = "20260720_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding_provider", sa.String(length=100), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("vector_store", sa.String(length=100), nullable=False),
        sa.Column(
            "vector_collection_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_knowledge_bases_name_not_blank",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_bases"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=4096), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("chunk_status", sa.String(length=32), nullable=False),
        sa.Column("embedding_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "chunk_status IN ('pending', 'chunking', 'chunked', 'failed')",
            name="ck_documents_chunk_status",
        ),
        sa.CheckConstraint(
            "embedding_status IN ('pending', 'embedding', 'ready', 'failed')",
            name="ck_documents_embedding_status",
        ),
        sa.CheckConstraint(
            "length(file_hash) = 64",
            name="ck_documents_file_hash_length",
        ),
        sa.CheckConstraint(
            "file_size >= 0",
            name="ck_documents_file_size_non_negative",
        ),
        sa.CheckConstraint(
            "file_type IN ('md', 'txt', 'pdf')",
            name="ck_documents_file_type",
        ),
        sa.CheckConstraint(
            "parse_status IN ('uploaded', 'parsing', 'parsed', 'failed')",
            name="ck_documents_parse_status",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name="fk_documents_knowledge_base_id_knowledge_bases",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint(
            "id",
            "knowledge_base_id",
            name="uq_documents_id_knowledge_base_id",
        ),
    )
    op.create_index(
        "ix_documents_knowledge_base_id",
        "documents",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=512), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("vector_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "char_count >= 0",
            name="ck_document_chunks_char_count_non_negative",
        ),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name="ck_document_chunks_chunk_index_non_negative",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_document_chunks_page_number_positive",
        ),
        sa.CheckConstraint(
            "token_count >= 0",
            name="ck_document_chunks_token_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "knowledge_base_id"],
            ["documents.id", "documents.knowledge_base_id"],
            name="fk_document_chunks_document_knowledge_base_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_knowledge_base_id",
        "document_chunks",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_table(
        "rag_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("retrieved_chunks_json", sa.JSON(), nullable=False),
        sa.Column("answer_message_id", sa.Uuid(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "answer_message_id IS NULL OR conversation_id IS NOT NULL",
            name="ck_rag_queries_answer_requires_conversation",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_rag_queries_latency_ms_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["answer_message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            name="fk_rag_queries_answer_message_conversation_messages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_rag_queries_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name="fk_rag_queries_knowledge_base_id_knowledge_bases",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rag_queries"),
    )
    op.create_index(
        "ix_rag_queries_answer_message_id",
        "rag_queries",
        ["answer_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_queries_conversation_id",
        "rag_queries",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_queries_knowledge_base_id",
        "rag_queries",
        ["knowledge_base_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_queries_knowledge_base_id",
        table_name="rag_queries",
    )
    op.drop_index(
        "ix_rag_queries_conversation_id",
        table_name="rag_queries",
    )
    op.drop_index(
        "ix_rag_queries_answer_message_id",
        table_name="rag_queries",
    )
    op.drop_table("rag_queries")
    op.drop_index(
        "ix_document_chunks_knowledge_base_id",
        table_name="document_chunks",
    )
    op.drop_index(
        "ix_document_chunks_document_id",
        table_name="document_chunks",
    )
    op.drop_table("document_chunks")
    op.drop_index(
        "ix_documents_knowledge_base_id",
        table_name="documents",
    )
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
