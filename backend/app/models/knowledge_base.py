from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.rag_query import RagQuery


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_knowledge_bases_name_not_blank",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    embedding_provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    vector_store: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="qdrant",
    )
    vector_collection_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    documents: Mapped[list[Document]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    rag_queries: Mapped[list[RagQuery]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
