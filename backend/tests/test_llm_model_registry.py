import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.dependencies import get_model_registry
from app.core.config import Settings
from app.providers.llm.registry import (
    ModelInfo,
    ModelRegistry,
    ModelRegistryError,
    load_default_registry,
)


def make_model(
    *,
    provider: str,
    model: str,
    display_name: str,
) -> ModelInfo:
    return ModelInfo(
        provider=provider,
        model=model,
        display_name=display_name,
        supports_streaming=True,
        supports_tools=False,
        supports_json=False,
    )


def test_default_registry_lists_example_model() -> None:
    registry = load_default_registry()

    assert registry.list_models() == [
        ModelInfo(
            provider="openai_compatible",
            model="example-model",
            display_name="Example OpenAI-Compatible Model",
            supports_streaming=True,
            supports_tools=False,
            supports_json=False,
            input_price_per_1m=None,
            output_price_per_1m=None,
        )
    ]
    assert [model for model in registry.list_models() if model.supports_tools] == []


def test_dependency_loads_configured_local_registry(tmp_path: Path) -> None:
    config_path = write_registry(
        tmp_path / "models.local.json",
        {
            "models": [
                {
                    "provider": "openai_compatible",
                    "model": "synthetic-tool-model",
                    "display_name": "Synthetic Tool Model",
                    "supports_streaming": True,
                    "supports_tools": True,
                    "supports_json": False,
                    "input_price_per_1m": None,
                    "output_price_per_1m": None,
                }
            ]
        },
    )
    settings = Settings(
        _env_file=None,
        MODEL_REGISTRY_PATH=config_path,
    )

    registry = get_model_registry(settings=settings)

    assert [model.model for model in registry.list_models()] == [
        "synthetic-tool-model"
    ]
    assert registry.list_models()[0].supports_tools is True


def test_tracked_local_registry_example_is_tool_capable() -> None:
    example_path = (
        Path(__file__).parents[1]
        / "app"
        / "providers"
        / "llm"
        / "models.local.example.json"
    )

    registry = ModelRegistry.from_file(example_path)

    assert len(registry.list_models()) == 1
    assert registry.list_models()[0].supports_tools is True
    assert "replace-with" in registry.list_models()[0].model


def test_registry_filters_models_by_provider_in_configuration_order() -> None:
    first = make_model(
        provider="provider-a",
        model="model-1",
        display_name="First",
    )
    second = make_model(
        provider="provider-b",
        model="model-2",
        display_name="Second",
    )
    third = make_model(
        provider="provider-a",
        model="model-3",
        display_name="Third",
    )
    registry = ModelRegistry([first, second, third])

    assert registry.list_models(provider="provider-a") == [first, third]


def test_registry_gets_exact_model_or_none() -> None:
    model = make_model(
        provider="provider-a",
        model="model-1",
        display_name="First",
    )
    registry = ModelRegistry([model])

    assert registry.get_model("provider-a", "model-1") == model
    assert registry.get_model("provider-a", "missing") is None


def test_list_models_returns_a_defensive_copy() -> None:
    model = make_model(
        provider="provider-a",
        model="model-1",
        display_name="First",
    )
    registry = ModelRegistry([model])

    listed = registry.list_models()
    listed.clear()

    assert registry.list_models() == [model]


def test_model_info_accepts_non_negative_decimal_prices() -> None:
    model = ModelInfo(
        provider="provider-a",
        model="model-1",
        display_name="Priced Model",
        supports_streaming=True,
        supports_tools=False,
        supports_json=False,
        input_price_per_1m=Decimal("0.25"),
        output_price_per_1m=Decimal("0.50"),
    )

    assert model.input_price_per_1m == Decimal("0.25")
    assert model.output_price_per_1m == Decimal("0.50")


def write_registry(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_registry_rejects_duplicate_provider_and_model() -> None:
    model = make_model(
        provider="provider-a",
        model="model-1",
        display_name="First",
    )

    with pytest.raises(
        ModelRegistryError,
        match="Duplicate model registration: provider-a/model-1",
    ):
        ModelRegistry([model, model.model_copy(update={"display_name": "Duplicate"})])


def test_registry_wraps_unreadable_file_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(ModelRegistryError, match="Unable to read model registry"):
        ModelRegistry.from_file(missing_path)


def test_registry_wraps_invalid_json_error(tmp_path: Path) -> None:
    config_path = tmp_path / "models.json"
    config_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ModelRegistryError, match="Invalid model registry JSON"):
        ModelRegistry.from_file(config_path)


@pytest.mark.parametrize(
    "model_override",
    [
        {"unknown_capability": True},
        {"provider": "   "},
        {"input_price_per_1m": -1},
    ],
)
def test_registry_rejects_invalid_model_configuration(
    tmp_path: Path,
    model_override: dict[str, object],
) -> None:
    model = {
        "provider": "provider-a",
        "model": "model-1",
        "display_name": "First",
        "supports_streaming": True,
        "supports_tools": False,
        "supports_json": False,
        **model_override,
    }
    config_path = write_registry(tmp_path / "models.json", {"models": [model]})

    with pytest.raises(
        ModelRegistryError,
        match="Invalid model registry configuration",
    ):
        ModelRegistry.from_file(config_path)


def test_model_info_is_immutable() -> None:
    model = make_model(
        provider="provider-a",
        model="model-1",
        display_name="First",
    )

    with pytest.raises(ValidationError):
        model.model = "changed"
