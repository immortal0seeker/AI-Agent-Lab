from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.knowledge_base import KnowledgeBase
    from app.models.message import Message


class RagQuery(Base):
    __tablename__ = "rag_queries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["answer_message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            name="fk_rag_queries_answer_message_conversation_messages",
            ondelete="NO ACTION",
        ),
        CheckConstraint(
            "answer_message_id IS NULL OR conversation_id IS NOT NULL",
            name="ck_rag_queries_answer_requires_conversation",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_rag_queries_latency_ms_non_negative",
        ),
        CheckConstraint(
            "top_k >= 1 AND top_k <= 100",
            name="ck_rag_queries_top_k_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    knowledge_base_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    query: Mapped[str] = mapped_column(Text(), nullable=False)
    top_k: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        default=5,
        server_default="5",
    )
    retrieved_chunks_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON(),
        nullable=False,
        default=list,
    )
    answer_message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "messages.id",
            name="fk_rag_queries_answer_message_id_messages",
            ondelete="SET NULL",
        ),
        index=True,
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=utc_now,
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(
        back_populates="rag_queries"
    )
    conversation: Mapped[Conversation | None] = relationship(
        back_populates="rag_queries",
        foreign_keys=[conversation_id],
    )
    answer_message: Mapped[Message | None] = relationship(
        back_populates="answered_rag_queries",
        primaryjoin=(
            "and_(RagQuery.answer_message_id == Message.id, "
            "RagQuery.conversation_id == Message.conversation_id)"
        ),
        foreign_keys=[answer_message_id],
    )
