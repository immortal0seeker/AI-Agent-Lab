from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_conversation_service
from app.schemas.conversation import ConversationCreate, ConversationRead
from app.schemas.message import MessageRead
from app.services.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationRead]:
    return [
        ConversationRead.model_validate(item)
        for item in service.list_conversations()
    ]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRead:
    return ConversationRead.model_validate(service.create_conversation(data))


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRead:
    return ConversationRead.model_validate(
        service.get_conversation(conversation_id)
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
def list_conversation_messages(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> list[MessageRead]:
    return [
        MessageRead.model_validate(item)
        for item in service.list_messages(conversation_id)
    ]
