import json
from collections.abc import AsyncIterator, Mapping

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.api.dependencies import (
    get_chat_service,
    get_llm_providers,
    get_model_registry,
    get_session_factory,
)
from app.providers.llm.base import BaseLLMProvider, LLMProviderError
from app.providers.llm.registry import ModelRegistry
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatStreamDeltaResponse,
    ChatStreamErrorResponse,
)
from app.schemas.message import MessageRead
from app.services.chat_service import (
    ChatCompletionResult,
    ChatService,
    ChatStreamCompleted,
    ChatStreamDelta,
)
from app.services.errors import ServiceError


router = APIRouter(prefix="/chat", tags=["chat"])


def to_completion_response(result: ChatCompletionResult) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        conversation_id=result.conversation.id,
        user_message=MessageRead.model_validate(result.user_message),
        assistant_message=MessageRead.model_validate(result.assistant_message),
        provider=result.provider,
        model=result.model,
        usage=result.usage,
        llm_call_id=result.llm_call.id,
    )


def encode_sse(event: str, payload: BaseModel) -> str:
    data = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    data: ChatCompletionRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatCompletionResponse:
    result = await service.complete(data)
    return to_completion_response(result)


async def stream_chat_events(
    data: ChatCompletionRequest,
    *,
    session_factory: sessionmaker[Session],
    registry: ModelRegistry,
    providers: Mapping[str, BaseLLMProvider],
) -> AsyncIterator[str]:
    session = session_factory()
    try:
        service = ChatService(session, registry=registry, providers=providers)
        async for event in service.stream_complete(data):
            if isinstance(event, ChatStreamDelta):
                yield encode_sse(
                    "delta",
                    ChatStreamDeltaResponse(content=event.content),
                )
            elif isinstance(event, ChatStreamCompleted):
                yield encode_sse(
                    "done",
                    to_completion_response(event.result),
                )
    except (LLMProviderError, ServiceError) as exc:
        yield encode_sse("error", ChatStreamErrorResponse(message=str(exc)))
    except Exception:
        session.rollback()
        yield encode_sse(
            "error",
            ChatStreamErrorResponse(message="Streaming request failed"),
        )
    finally:
        session.close()


@router.post("/stream", response_class=StreamingResponse)
async def create_streaming_chat_completion(
    data: ChatCompletionRequest,
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    registry: ModelRegistry = Depends(get_model_registry),
    providers: Mapping[str, BaseLLMProvider] = Depends(get_llm_providers),
) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_events(
            data,
            session_factory=session_factory,
            registry=registry,
            providers=providers,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
