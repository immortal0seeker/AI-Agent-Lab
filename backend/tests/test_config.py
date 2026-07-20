import pytest
from pydantic import ValidationError

from app.api.dependencies import get_simple_agent_service
from app.core.config import Settings
from app.providers.llm.registry import ModelRegistry
from app.tools import ToolRegistry


def test_settings_default_agent_run_timeout_is_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.agent_run_timeout_seconds == 120.0
    assert settings.model_registry_path is None


@pytest.mark.parametrize("value", ["", "   "])
def test_settings_treats_blank_model_registry_path_as_unset(value: str) -> None:
    settings = Settings(_env_file=None, MODEL_REGISTRY_PATH=value)

    assert settings.model_registry_path is None


@pytest.mark.parametrize(
    "value",
    [0, -1, 3601, float("nan"), float("inf")],
)
def test_settings_rejects_invalid_agent_run_timeout(value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, AGENT_RUN_TIMEOUT_SECONDS=value)


def test_agent_dependency_passes_configured_whole_run_timeout() -> None:
    settings = Settings(
        _env_file=None,
        AGENT_RUN_TIMEOUT_SECONDS=15.5,
    )

    service = get_simple_agent_service(
        session=object(),  # type: ignore[arg-type]
        registry=ModelRegistry([]),
        providers={},
        tools=ToolRegistry(),
        settings=settings,
    )

    assert service._run_timeout_seconds == 15.5
