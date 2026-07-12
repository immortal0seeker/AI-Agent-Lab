from collections.abc import AsyncIterator, Mapping
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.factory import create_openai_compatible_provider
from app.providers.llm.registry import ModelRegistry, load_default_registry
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService


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


@lru_cache
def get_model_registry() -> ModelRegistry:
    return load_default_registry()


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
