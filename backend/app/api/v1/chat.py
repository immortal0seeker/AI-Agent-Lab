from fastapi import APIRouter, Depends

from app.api.dependencies import get_chat_service
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.schemas.message import MessageRead
from app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    data: ChatCompletionRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatCompletionResponse:
    result = await service.complete(data)
    return ChatCompletionResponse(
        conversation_id=result.conversation.id,
        user_message=MessageRead.model_validate(result.user_message),
        assistant_message=MessageRead.model_validate(result.assistant_message),
        provider=result.provider,
        model=result.model,
        usage=result.usage,
        llm_call_id=result.llm_call.id,
    )
