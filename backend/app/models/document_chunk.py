from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
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
    from app.models.document import Document


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "knowledge_base_id"],
            ["documents.id", "documents.knowledge_base_id"],
            name="fk_document_chunks_document_knowledge_base_documents",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_document_chunks_chunk_index_non_negative",
        ),
        CheckConstraint(
            "token_count >= 0",
            name="ck_document_chunks_token_count_non_negative",
        ),
        CheckConstraint(
            "char_count >= 0",
            name="ck_document_chunks_char_count_non_negative",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_document_chunks_page_number_positive",
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    knowledge_base_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    char_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON(),
        nullable=False,
        default=dict,
    )
    vector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
