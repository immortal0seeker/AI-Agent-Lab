from collections.abc import AsyncIterator, Mapping
from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.agents import SimpleAgentService
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.db.session_callbacks import (
    discard_async_rollback_callbacks,
    register_async_session_finalizer,
    run_async_rollback_callbacks,
    run_async_session_finalizers,
)
from app.knowledge import DocumentStorage
from app.providers.embedding import EmbeddingProvider
from app.providers.embedding.factory import create_embedding_provider
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.factory import create_openai_compatible_provider
from app.providers.llm.registry import ModelRegistry, load_default_registry
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.document_service import DocumentService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.tools import ToolRegistry
from app.tools.builtin import register_builtin_tools
from app.rag.vectorstores import (
    VectorStore,
    create_qdrant_vector_store,
)


async def get_db_session() -> AsyncIterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
        discard_async_rollback_callbacks(session)
    except Exception:
        session.rollback()
        await run_async_rollback_callbacks(session)
        raise
    finally:
        await run_async_session_finalizers(session)
        session.close()


def get_session_factory() -> sessionmaker[Session]:
    return SessionLocal


@lru_cache
def _load_model_registry(configured_path: str | None) -> ModelRegistry:
    if configured_path is None:
        return load_default_registry()
    return ModelRegistry.from_file(Path(configured_path))


def get_model_registry(
    settings: Settings = Depends(get_settings),
) -> ModelRegistry:
    configured_path = settings.model_registry_path
    cache_key = (
        None
        if configured_path is None
        else str(configured_path.expanduser().resolve())
    )
    return _load_model_registry(cache_key)


def get_llm_providers(
    settings: Settings = Depends(get_settings),
) -> Mapping[str, BaseLLMProvider]:
    return {
        "openai_compatible": create_openai_compatible_provider(settings),
    }


def get_conversation_service(
    session: Session = Depends(get_db_session, scope="function"),
) -> ConversationService:
    return ConversationService(session)


def get_knowledge_base_service(
    session: Session = Depends(get_db_session, scope="function"),
) -> KnowledgeBaseService:
    return KnowledgeBaseService(session)


def get_embedding_provider(
    settings: Settings = Depends(get_settings),
) -> EmbeddingProvider:
    return create_embedding_provider(settings)


def get_vector_store(
    session: Session = Depends(get_db_session, scope="function"),
    settings: Settings = Depends(get_settings),
) -> VectorStore:
    store = create_qdrant_vector_store(settings)
    register_async_session_finalizer(session, store.close)
    return store


def get_document_service(
    session: Session = Depends(get_db_session, scope="function"),
    settings: Settings = Depends(get_settings),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> DocumentService:
    storage = DocumentStorage(
        settings.document_storage_root,
        max_upload_bytes=settings.document_max_upload_bytes,
    )
    return DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=(
            settings.document_max_files_per_knowledge_base
        ),
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        processing_limits=settings.document_processing_limits,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def get_chat_service(
    session: Session = Depends(get_db_session, scope="function"),
    registry: ModelRegistry = Depends(get_model_registry),
    providers: Mapping[str, BaseLLMProvider] = Depends(get_llm_providers),
) -> ChatService:
    return ChatService(session, registry=registry, providers=providers)


def get_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    return registry


def get_simple_agent_service(
    session: Session = Depends(get_db_session, scope="function"),
    registry: ModelRegistry = Depends(get_model_registry),
    providers: Mapping[str, BaseLLMProvider] = Depends(get_llm_providers),
    tools: ToolRegistry = Depends(get_tool_registry),
    settings: Settings = Depends(get_settings),
) -> SimpleAgentService:
    return SimpleAgentService(
        session,
        registry=registry,
        providers=providers,
        tools=tools,
        run_timeout_seconds=settings.agent_run_timeout_seconds,
    )


def get_agent_service(
    session: Session = Depends(get_db_session, scope="function"),
) -> AgentService:
    return AgentService(session)
