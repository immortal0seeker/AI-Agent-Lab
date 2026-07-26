from pathlib import Path

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
    assert settings.qdrant_url == "http://localhost:6333"


def test_settings_accepts_qdrant_url_override() -> None:
    settings = Settings(
        _env_file=None,
        QDRANT_URL="http://qdrant.internal:6333",
    )

    assert settings.qdrant_url == "http://qdrant.internal:6333"


def test_settings_default_document_upload_limits() -> None:
    settings = Settings(_env_file=None)

    assert settings.document_storage_root.is_absolute()
    assert settings.document_storage_root.name == "uploads"
    assert settings.document_max_upload_bytes == 20_971_520
    assert settings.document_max_files_per_knowledge_base == 50


def test_settings_resolves_relative_document_storage_from_backend() -> None:
    settings = Settings(
        _env_file=None,
        DOCUMENT_STORAGE_ROOT="runtime_uploads",
    )

    assert settings.document_storage_root.is_absolute()
    assert settings.document_storage_root.name == "runtime_uploads"
    assert settings.document_storage_root.parent.name == "backend"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("DOCUMENT_MAX_UPLOAD_BYTES", 0),
        ("DOCUMENT_MAX_UPLOAD_BYTES", 1_073_741_825),
        ("DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE", 0),
        ("DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE", 10_001),
    ],
)
def test_settings_rejects_invalid_document_upload_limits(
    field_name: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})


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
