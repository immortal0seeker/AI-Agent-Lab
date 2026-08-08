"""Create RAG retrieval Trace audit tables.

Revision ID: 20260808_0009
Revises: 20260802_0008
Create Date: 2026-08-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260808_0009"
down_revision: str | None = "20260802_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_retrieval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trace_run_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("rewritten_query", sa.Text(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("score_threshold", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("metadata_filter_json", sa.JSON(), nullable=False),
        sa.Column("strategy_config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "candidate_count >= 0 AND candidate_count <= 100",
            name="ck_rag_retrieval_runs_candidate_count_range",
        ),
        sa.CheckConstraint(
            "latency_ms >= 0",
            name="ck_rag_retrieval_runs_latency_ms_non_negative",
        ),
        sa.CheckConstraint(
            "length(trim(original_query)) > 0",
            name="ck_rag_retrieval_runs_original_query_not_blank",
        ),
        sa.CheckConstraint(
            "selected_count <= candidate_count",
            name=(
                "ck_rag_retrieval_runs_selected_count_not_above_"
                "candidate_count"
            ),
        ),
        sa.CheckConstraint(
            "selected_count >= 0 AND selected_count <= 100",
            name="ck_rag_retrieval_runs_selected_count_range",
        ),
        sa.CheckConstraint(
            "length(trim(strategy_name)) > 0",
            name="ck_rag_retrieval_runs_strategy_name_not_blank",
        ),
        sa.CheckConstraint(
            "top_k >= 1 AND top_k <= 100",
            name="ck_rag_retrieval_runs_top_k_range",
        ),
        sa.ForeignKeyConstraint(
            ["trace_run_id"],
            ["trace_runs.id"],
            name="fk_rag_retrieval_runs_trace_run_id_trace_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rag_retrieval_runs"),
    )
    op.create_index(
        "ix_rag_retrieval_runs_knowledge_base_id",
        "rag_retrieval_runs",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_retrieval_runs_trace_run_id",
        "rag_retrieval_runs",
        ["trace_run_id"],
        unique=False,
    )

    op.create_table(
        "rag_retrieval_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("retrieval_run_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("final_rank", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("dense_score", sa.Float(), nullable=True),
        sa.Column("sparse_score", sa.Float(), nullable=True),
        sa.Column("fused_score", sa.Float(), nullable=True),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("content_preview", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "length(content_preview) <= 500",
            name="ck_rag_retrieval_candidates_content_preview_max_length",
        ),
        sa.CheckConstraint(
            "length(trim(content_preview)) > 0",
            name="ck_rag_retrieval_candidates_content_preview_not_blank",
        ),
        sa.CheckConstraint(
            "final_rank IS NULL OR final_rank > 0",
            name="ck_rag_retrieval_candidates_final_rank_positive",
        ),
        sa.CheckConstraint(
            "rank > 0",
            name="ck_rag_retrieval_candidates_rank_positive",
        ),
        sa.CheckConstraint(
            "source IN ('dense', 'sparse', 'hybrid', 'parent', 'rerank')",
            name="ck_rag_retrieval_candidates_source",
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_run_id"],
            ["rag_retrieval_runs.id"],
            name=(
                "fk_rag_retrieval_candidates_retrieval_run_id_"
                "rag_retrieval_runs"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rag_retrieval_candidates"),
        sa.UniqueConstraint(
            "retrieval_run_id",
            "final_rank",
            name="uq_rag_retrieval_candidates_retrieval_run_id_final_rank",
        ),
        sa.UniqueConstraint(
            "retrieval_run_id",
            "rank",
            name="uq_rag_retrieval_candidates_retrieval_run_id_rank",
        ),
    )
    op.create_index(
        "ix_rag_retrieval_candidates_chunk_id",
        "rag_retrieval_candidates",
        ["chunk_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_retrieval_candidates_document_id",
        "rag_retrieval_candidates",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_rag_retrieval_candidates_retrieval_run_id",
        "rag_retrieval_candidates",
        ["retrieval_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_retrieval_candidates_retrieval_run_id",
        table_name="rag_retrieval_candidates",
    )
    op.drop_index(
        "ix_rag_retrieval_candidates_document_id",
        table_name="rag_retrieval_candidates",
    )
    op.drop_index(
        "ix_rag_retrieval_candidates_chunk_id",
        table_name="rag_retrieval_candidates",
    )
    op.drop_table("rag_retrieval_candidates")
    op.drop_index(
        "ix_rag_retrieval_runs_trace_run_id",
        table_name="rag_retrieval_runs",
    )
    op.drop_index(
        "ix_rag_retrieval_runs_knowledge_base_id",
        table_name="rag_retrieval_runs",
    )
    op.drop_table("rag_retrieval_runs")
