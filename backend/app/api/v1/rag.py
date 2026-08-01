from fastapi import APIRouter, Depends

from app.api.dependencies import get_rag_query_service, get_rag_service
from app.schemas.message import MessageRead
from app.schemas.rag import (
    RagChatRequest,
    RagChatResponse,
    RagQueryResponse,
    RagRetrievalRequest,
)
from app.services.rag_service import RagChatResult, RagQueryService, RagService


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
async def query_knowledge_base(
    data: RagRetrievalRequest,
    service: RagQueryService = Depends(get_rag_query_service),
) -> RagQueryResponse:
    result = await service.query(data)
    return RagQueryResponse(
        results=result.results,
        metadata=result.metadata,
    )


@router.post("/chat", response_model=RagChatResponse)
async def create_rag_chat_completion(
    data: RagChatRequest,
    service: RagService = Depends(get_rag_service),
) -> RagChatResponse:
    return _to_chat_response(await service.chat(data))


def _to_chat_response(result: RagChatResult) -> RagChatResponse:
    return RagChatResponse(
        conversation_id=result.conversation.id,
        user_message=MessageRead.model_validate(result.user_message),
        assistant_message=MessageRead.model_validate(
            result.assistant_message
        ),
        answer=result.answer,
        sources=result.sources,
        metadata=result.metadata,
        provider=result.provider,
        model=result.model,
        usage=result.usage,
        llm_call_id=result.llm_call.id,
    )
