from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeBase
from app.models.common import utc_now
from app.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services.errors import KnowledgeBaseNotFoundError


class KnowledgeBaseService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_knowledge_base(
        self,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(**data.model_dump())
        self._session.add(knowledge_base)
        self._session.flush()
        return knowledge_base

    def list_knowledge_bases(self) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase).order_by(
            KnowledgeBase.created_at.desc(),
            KnowledgeBase.id,
        )
        return list(self._session.scalars(statement))

    def get_knowledge_base(
        self,
        knowledge_base_id: UUID,
    ) -> KnowledgeBase:
        knowledge_base = self._session.get(
            KnowledgeBase,
            knowledge_base_id,
        )
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError(knowledge_base_id)
        return knowledge_base

    def update_knowledge_base(
        self,
        knowledge_base_id: UUID,
        data: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        knowledge_base = self.get_knowledge_base(knowledge_base_id)
        for field_name, value in data.model_dump(
            exclude_unset=True
        ).items():
            setattr(knowledge_base, field_name, value)

        next_updated_at = utc_now()
        if next_updated_at <= knowledge_base.updated_at:
            next_updated_at = (
                knowledge_base.updated_at + timedelta(microseconds=1)
            )
        knowledge_base.updated_at = next_updated_at
        self._session.flush()
        return knowledge_base

    def delete_knowledge_base(
        self,
        knowledge_base_id: UUID,
    ) -> None:
        knowledge_base = self.get_knowledge_base(knowledge_base_id)
        self._session.delete(knowledge_base)
        self._session.flush()
