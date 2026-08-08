from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
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
    from app.models.trace import TraceRun


class RagRetrievalRun(Base):
    __tablename__ = "rag_retrieval_runs"
    __table_args__ = (
        CheckConstraint(
            "length(trim(strategy_name)) > 0",
            name="ck_rag_retrieval_runs_strategy_name_not_blank",
        ),
        CheckConstraint(
            "length(trim(original_query)) > 0",
            name="ck_rag_retrieval_runs_original_query_not_blank",
        ),
        CheckConstraint(
            "top_k >= 1 AND top_k <= 100",
            name="ck_rag_retrieval_runs_top_k_range",
        ),
        CheckConstraint(
            "candidate_count >= 0 AND candidate_count <= 100",
            name="ck_rag_retrieval_runs_candidate_count_range",
        ),
        CheckConstraint(
            "selected_count >= 0 AND selected_count <= 100",
            name="ck_rag_retrieval_runs_selected_count_range",
        ),
        CheckConstraint(
            "selected_count <= candidate_count",
            name=(
                "ck_rag_retrieval_runs_selected_count_not_above_"
                "candidate_count"
            ),
        ),
        CheckConstraint(
            "latency_ms >= 0",
            name="ck_rag_retrieval_runs_latency_ms_non_negative",
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
            name="fk_rag_retrieval_runs_trace_run_id_trace_runs",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    knowledge_base_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    original_query: Mapped[str] = mapped_column(Text(), nullable=False)
    rewritten_query: Mapped[str | None] = mapped_column(Text(), nullable=True)
    top_k: Mapped[int] = mapped_column(Integer(), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    score_threshold: Mapped[float | None] = mapped_column(
        Float(),
        nullable=True,
    )
    latency_ms: Mapped[int] = mapped_column(Integer(), nullable=False)
    metadata_filter_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    strategy_config_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    trace_run: Mapped[TraceRun] = relationship(back_populates="retrieval_runs")
    candidates: Mapped[list[RagRetrievalCandidate]] = relationship(
        back_populates="retrieval_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RagRetrievalCandidate.rank",
    )


class RagRetrievalCandidate(Base):
    __tablename__ = "rag_retrieval_candidates"
    __table_args__ = (
        CheckConstraint(
            "rank > 0",
            name="ck_rag_retrieval_candidates_rank_positive",
        ),
        CheckConstraint(
            "final_rank IS NULL OR final_rank > 0",
            name="ck_rag_retrieval_candidates_final_rank_positive",
        ),
        CheckConstraint(
            "source IN ('dense', 'sparse', 'hybrid', 'parent', 'rerank')",
            name="ck_rag_retrieval_candidates_source",
        ),
        CheckConstraint(
            "length(trim(content_preview)) > 0",
            name="ck_rag_retrieval_candidates_content_preview_not_blank",
        ),
        CheckConstraint(
            "length(content_preview) <= 500",
            name="ck_rag_retrieval_candidates_content_preview_max_length",
        ),
        UniqueConstraint(
            "retrieval_run_id",
            "rank",
            name="uq_rag_retrieval_candidates_retrieval_run_id_rank",
        ),
        UniqueConstraint(
            "retrieval_run_id",
            "final_rank",
            name="uq_rag_retrieval_candidates_retrieval_run_id_final_rank",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    retrieval_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "rag_retrieval_runs.id",
            name=(
                "fk_rag_retrieval_candidates_retrieval_run_id_"
                "rag_retrieval_runs"
            ),
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    chunk_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer(), nullable=False)
    final_rank: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    dense_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    sparse_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    fused_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    rerank_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    selected: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        default=False,
    )
    content_preview: Mapped[str] = mapped_column(Text(), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    retrieval_run: Mapped[RagRetrievalRun] = relationship(
        back_populates="candidates"
    )
