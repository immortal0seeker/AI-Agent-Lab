from collections.abc import AsyncIterator, Mapping
from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.agents import SimpleAgentService
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.factory import create_openai_compatible_provider
from app.providers.llm.registry import ModelRegistry, load_default_registry
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.tools import ToolRegistry
from app.tools.builtin import register_builtin_tools


async def get_db_session() -> AsyncIterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
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
