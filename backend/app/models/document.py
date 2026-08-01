from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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
    from app.models.document_chunk import DocumentChunk
    from app.models.knowledge_base import KnowledgeBase


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('md', 'txt', 'pdf')",
            name="ck_documents_file_type",
        ),
        CheckConstraint(
            "file_size >= 0",
            name="ck_documents_file_size_non_negative",
        ),
        CheckConstraint(
            "length(file_hash) = 64",
            name="ck_documents_file_hash_length",
        ),
        CheckConstraint(
            "parse_status IN ('uploaded', 'parsing', 'parsed', 'failed')",
            name="ck_documents_parse_status",
        ),
        CheckConstraint(
            "chunk_status IN ('pending', 'chunking', 'chunked', 'failed')",
            name="ck_documents_chunk_status",
        ),
        CheckConstraint(
            "embedding_status IN ('pending', 'embedding', 'ready', 'failed')",
            name="ck_documents_embedding_status",
        ),
        UniqueConstraint(
            "id",
            "knowledge_base_id",
            name="uq_documents_id_knowledge_base_id",
        ),
        UniqueConstraint(
            "knowledge_base_id",
            "file_hash",
            name="uq_documents_knowledge_base_id_file_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    knowledge_base_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "knowledge_bases.id",
            name="fk_documents_knowledge_base_id_knowledge_bases",
            ondelete="RESTRICT",
        ),
        index=True,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer(), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="uploaded",
    )
    chunk_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
    )
    embedding_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(
        back_populates="documents"
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
