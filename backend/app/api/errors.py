from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.providers.llm.base import (
    LLMProviderError,
    ProviderConfigurationError,
)
from app.services.errors import (
    ChatModelNotFoundError,
    ChatProviderUnavailableError,
    ConversationNotFoundError,
)


async def conversation_not_found_handler(
    _: Request,
    exc: ConversationNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def chat_model_not_found_handler(
    _: Request,
    exc: ChatModelNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def chat_provider_unavailable_handler(
    _: Request,
    exc: ChatProviderUnavailableError,
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def provider_configuration_handler(
    _: Request,
    exc: ProviderConfigurationError,
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def llm_provider_error_handler(
    _: Request,
    exc: LLMProviderError,
) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        ConversationNotFoundError,
        conversation_not_found_handler,
    )
    app.add_exception_handler(ChatModelNotFoundError, chat_model_not_found_handler)
    app.add_exception_handler(
        ChatProviderUnavailableError,
        chat_provider_unavailable_handler,
    )
    app.add_exception_handler(
        ProviderConfigurationError,
        provider_configuration_handler,
    )
    app.add_exception_handler(LLMProviderError, llm_provider_error_handler)
