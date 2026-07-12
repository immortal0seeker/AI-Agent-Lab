from fastapi import APIRouter, Depends

from app.api.dependencies import get_model_registry
from app.providers.llm.registry import ModelRegistry
from app.schemas.model import ModelRead


router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelRead])
def list_models(
    registry: ModelRegistry = Depends(get_model_registry),
) -> list[ModelRead]:
    return [ModelRead.model_validate(model) for model in registry.list_models()]
