import json
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)


DEFAULT_MODEL_CONFIG_PATH = Path(__file__).with_name("models.json")


class ModelRegistryError(RuntimeError):
    """模型注册表配置无法安全加载。"""


NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: NonEmptyString
    model: NonEmptyString
    display_name: NonEmptyString
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_json: bool = False
    input_price_per_1m: Decimal | None = Field(default=None, ge=0)
    output_price_per_1m: Decimal | None = Field(default=None, ge=0)


class ModelRegistryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[ModelInfo]


class ModelRegistry:
    def __init__(self, models: list[ModelInfo]) -> None:
        self._models = list(models)
        self._models_by_key: dict[tuple[str, str], ModelInfo] = {}
        for model in self._models:
            key = (model.provider, model.model)
            if key in self._models_by_key:
                raise ModelRegistryError(
                    f"Duplicate model registration: {model.provider}/{model.model}"
                )
            self._models_by_key[key] = model

    @classmethod
    def from_file(cls, path: Path) -> "ModelRegistry":
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ModelRegistryError(
                f"Unable to read model registry: {path}"
            ) from exc

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ModelRegistryError(
                f"Invalid model registry JSON: {path}"
            ) from exc

        try:
            config = ModelRegistryConfig.model_validate(payload)
        except ValidationError as exc:
            raise ModelRegistryError(
                f"Invalid model registry configuration: {path}: {exc}"
            ) from exc
        return cls(config.models)

    def list_models(self, provider: str | None = None) -> list[ModelInfo]:
        if provider is None:
            return list(self._models)
        return [model for model in self._models if model.provider == provider]

    def get_model(self, provider: str, model: str) -> ModelInfo | None:
        return self._models_by_key.get((provider, model))


def load_default_registry() -> ModelRegistry:
    return ModelRegistry.from_file(DEFAULT_MODEL_CONFIG_PATH)
