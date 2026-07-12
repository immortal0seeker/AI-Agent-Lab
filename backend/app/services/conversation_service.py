from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Conversation, Message
from app.models.common import utc_now
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.services.errors import ConversationNotFoundError


class ConversationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_conversation(self, data: ConversationCreate) -> Conversation:
        conversation = Conversation(**data.model_dump())
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def get_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = self._session.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    def append_message(self, data: MessageCreate) -> Message:
        self.get_conversation(data.conversation_id)
        created_at = utc_now()
        latest_created_at = self._session.scalar(
            select(func.max(Message.created_at)).where(
                Message.conversation_id == data.conversation_id
            )
        )
        if latest_created_at is not None and created_at <= latest_created_at:
            created_at = latest_created_at + timedelta(microseconds=1)

        message = Message(**data.model_dump(), created_at=created_at)
        self._session.add(message)
        self._session.flush()
        return message

    def list_messages(self, conversation_id: UUID) -> list[Message]:
        self.get_conversation(conversation_id)
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(self._session.scalars(statement))
