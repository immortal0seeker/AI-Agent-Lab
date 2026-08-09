import logging
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.agents import (
    AgentModelNotFoundError,
    AgentModelToolsUnsupportedError,
    AgentProviderUnavailableError,
    AgentRunNotFoundError,
)
from app.core.logging import safe_stack_locations
from app.core.request_context import bind_request_id, get_request_id
from app.knowledge import (
    DocumentDuplicateError,
    DocumentError,
    DocumentFileInvalidError,
    DocumentStorageError,
    DocumentTooLargeError,
    DocumentTypeUnsupportedError,
    KnowledgeBaseDocumentLimitReachedError,
)
from app.providers.llm.base import (
    LLMProviderError,
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderServerError,
    ProviderTimeoutError,
)
from app.providers.embedding import EmbeddingProviderError
from app.rag.retriever import (
    RetrieverError,
    RetrieverInputError,
    RetrieverResponseError,
)
from app.rag.vectorstores import VectorStoreError
from app.schemas.error import ErrorDetail, ErrorResponse
from app.services.errors import (
    ChatModelNotFoundError,
    ChatProviderUnavailableError,
    ConversationNotFoundError,
    KnowledgeBaseNotEmptyError,
    KnowledgeBaseNotFoundError,
    ServiceError,
)
from app.services.trace_query_service import TraceRunNotFoundError


logger = logging.getLogger("app.error")


@dataclass(frozen=True)
class ErrorSpec:
    status_code: int
    code: str
    message: str


def error_spec_for_exception(exc: Exception) -> ErrorSpec:
    if isinstance(exc, RequestValidationError):
        return ErrorSpec(422, "validation_error", "Request validation failed")
    if isinstance(exc, AgentModelNotFoundError):
        return ErrorSpec(
            400,
            "model_not_found",
            "The requested model is not available",
        )
    if isinstance(exc, AgentModelToolsUnsupportedError):
        return ErrorSpec(
            400,
            "model_tools_unsupported",
            "The requested model does not support tools",
        )
    if isinstance(exc, AgentProviderUnavailableError):
        return ErrorSpec(
            503,
            "provider_unavailable",
            "The requested provider is unavailable",
        )
    if isinstance(exc, AgentRunNotFoundError):
        return ErrorSpec(404, "agent_run_not_found", "Agent run not found")
    if isinstance(exc, TraceRunNotFoundError):
        return ErrorSpec(404, "trace_run_not_found", "Trace run not found")
    if isinstance(exc, ConversationNotFoundError):
        return ErrorSpec(404, "conversation_not_found", "Conversation not found")
    if isinstance(exc, KnowledgeBaseNotFoundError):
        return ErrorSpec(
            404,
            "knowledge_base_not_found",
            "Knowledge base not found",
        )
    if isinstance(exc, KnowledgeBaseNotEmptyError):
        return ErrorSpec(
            409,
            "knowledge_base_not_empty",
            "Delete documents before deleting the knowledge base",
        )
    if isinstance(exc, DocumentFileInvalidError):
        return ErrorSpec(
            400,
            "document_file_invalid",
            "The uploaded document is invalid",
        )
    if isinstance(exc, DocumentTooLargeError):
        return ErrorSpec(
            413,
            "document_too_large",
            "The uploaded document exceeds the size limit",
        )
    if isinstance(exc, DocumentTypeUnsupportedError):
        return ErrorSpec(
            415,
            "document_type_unsupported",
            "The uploaded document type is not supported",
        )
    if isinstance(exc, DocumentDuplicateError):
        return ErrorSpec(
            409,
            "document_duplicate",
            "The document already exists in this knowledge base",
        )
    if isinstance(exc, KnowledgeBaseDocumentLimitReachedError):
        return ErrorSpec(
            409,
            "knowledge_base_document_limit_reached",
            "The knowledge base document limit was reached",
        )
    if isinstance(exc, DocumentStorageError):
        return ErrorSpec(
            503,
            "document_storage_error",
            "The document storage operation failed",
        )
    if isinstance(exc, EmbeddingProviderError):
        return ErrorSpec(
            503,
            "embedding_provider_unavailable",
            "The embedding provider is unavailable",
        )
    if isinstance(exc, VectorStoreError):
        return ErrorSpec(
            503,
            "vector_store_unavailable",
            "The vector store is unavailable",
        )
    if isinstance(exc, RetrieverInputError):
        return ErrorSpec(
            400,
            "rag_retrieval_input_invalid",
            "The retrieval request is invalid",
        )
    if isinstance(exc, RetrieverResponseError):
        return ErrorSpec(
            502,
            "rag_retrieval_response_invalid",
            "The retrieval backend returned an invalid response",
        )
    if isinstance(exc, ChatModelNotFoundError):
        return ErrorSpec(
            400,
            "model_not_found",
            "The requested model is not available",
        )
    if isinstance(exc, ChatProviderUnavailableError):
        return ErrorSpec(
            503,
            "provider_unavailable",
            "The requested provider is unavailable",
        )
    if isinstance(exc, ProviderConfigurationError):
        return ErrorSpec(
            503,
            "provider_unavailable",
            "The model provider is not configured",
        )
    if isinstance(exc, ProviderAuthError):
        return ErrorSpec(
            502,
            "provider_auth_error",
            "The model provider rejected its credentials",
        )
    if isinstance(exc, ProviderRateLimitError):
        return ErrorSpec(
            429,
            "provider_rate_limit",
            "The model provider rate limit was exceeded",
        )
    if isinstance(exc, ProviderTimeoutError):
        return ErrorSpec(
            504,
            "provider_timeout",
            "The model provider timed out",
        )
    if isinstance(exc, ProviderBadRequestError):
        return ErrorSpec(
            502,
            "provider_bad_request",
            "The model provider rejected the request",
        )
    if isinstance(exc, ProviderServerError):
        return ErrorSpec(
            502,
            "provider_server_error",
            "The model provider is unavailable",
        )
    if isinstance(exc, ProviderResponseError):
        return ErrorSpec(
            502,
            "provider_response_error",
            "The model provider returned an invalid response",
        )
    if isinstance(exc, (ProviderRequestError, LLMProviderError)):
        return ErrorSpec(
            502,
            "provider_unknown_error",
            "The model provider request failed",
        )
    if isinstance(exc, SQLAlchemyError):
        return ErrorSpec(503, "database_error", "The database operation failed")
    if isinstance(exc, HTTPException):
        if exc.status_code == 404:
            message = "Resource not found"
        elif exc.status_code == 405:
            message = "Method not allowed"
        else:
            message = "HTTP request failed"
        return ErrorSpec(exc.status_code, "http_error", message)
    return ErrorSpec(
        500,
        "internal_error",
        "The request could not be completed",
    )


def error_response_for_exception(
    exc: Exception,
    *,
    request_id: str | None = None,
) -> tuple[int, ErrorResponse]:
    spec = error_spec_for_exception(exc)
    return spec.status_code, ErrorResponse(
        error=ErrorDetail(
            code=spec.code,
            message=spec.message,
            request_id=request_id or get_request_id(),
        )
    )


def log_api_error(exc: Exception, spec: ErrorSpec | None = None) -> None:
    resolved = spec or error_spec_for_exception(exc)
    extra: dict[str, object] = {
        "error_code": resolved.code,
        "exception_type": exc.__class__.__name__,
    }
    if isinstance(exc, SQLAlchemyError) or resolved.code == "internal_error":
        extra["stack"] = safe_stack_locations(exc)
    logger.log(
        logging.ERROR if resolved.status_code >= 500 else logging.WARNING,
        "request_failed",
        extra=extra,
    )


async def unified_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", get_request_id())
    spec = error_spec_for_exception(exc)
    with bind_request_id(request_id):
        log_api_error(exc, spec)
    _, payload = error_response_for_exception(exc, request_id=request_id)
    return JSONResponse(
        status_code=spec.status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, unified_error_handler)
    app.add_exception_handler(HTTPException, unified_error_handler)
    app.add_exception_handler(ServiceError, unified_error_handler)
    app.add_exception_handler(TraceRunNotFoundError, unified_error_handler)
    app.add_exception_handler(DocumentError, unified_error_handler)
    app.add_exception_handler(EmbeddingProviderError, unified_error_handler)
    app.add_exception_handler(VectorStoreError, unified_error_handler)
    app.add_exception_handler(RetrieverError, unified_error_handler)
    app.add_exception_handler(LLMProviderError, unified_error_handler)
    app.add_exception_handler(SQLAlchemyError, unified_error_handler)
    app.add_exception_handler(Exception, unified_error_handler)
