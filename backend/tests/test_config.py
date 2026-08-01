from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_document_service, get_simple_agent_service
from app.core.config import Settings
from app.providers.llm.registry import ModelRegistry
from app.tools import ToolRegistry


def test_settings_default_agent_run_timeout_is_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.agent_run_timeout_seconds == 120.0
    assert settings.model_registry_path is None
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection_name == "ai_agent_lab_chunks"
    assert settings.qdrant_timeout_seconds == 10


def test_settings_default_embedding_provider_configuration_is_lazy() -> None:
    settings = Settings(_env_file=None)

    assert settings.embedding_provider == "openai_compatible"
    assert settings.openai_compatible_embedding_base_url == ""
    assert settings.openai_compatible_embedding_api_key is None
    assert settings.openai_compatible_embedding_model == ""
    assert settings.openai_compatible_embedding_dimension is None
    assert settings.openai_compatible_embedding_timeout_seconds == 30.0


def test_settings_accepts_embedding_provider_overrides() -> None:
    settings = Settings(
        _env_file=None,
        EMBEDDING_PROVIDER=" openai_compatible ",
        OPENAI_COMPATIBLE_EMBEDDING_BASE_URL="https://provider.example/v1",
        OPENAI_COMPATIBLE_EMBEDDING_API_KEY="synthetic-secret",
        OPENAI_COMPATIBLE_EMBEDDING_MODEL="example-embedding-model",
        OPENAI_COMPATIBLE_EMBEDDING_DIMENSION=1024,
        OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS=45.5,
    )

    assert settings.embedding_provider == "openai_compatible"
    assert settings.openai_compatible_embedding_dimension == 1024
    assert settings.openai_compatible_embedding_timeout_seconds == 45.5


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("EMBEDDING_PROVIDER", ""),
        ("EMBEDDING_PROVIDER", "   "),
        ("EMBEDDING_PROVIDER", "x" * 101),
        ("OPENAI_COMPATIBLE_EMBEDDING_DIMENSION", 0),
        ("OPENAI_COMPATIBLE_EMBEDDING_DIMENSION", 65_537),
        ("OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS", 0),
        ("OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS", 3601),
        ("OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS", float("nan")),
        ("OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS", float("inf")),
    ],
)
def test_settings_rejects_invalid_embedding_provider_configuration(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})


def test_settings_accepts_qdrant_url_override() -> None:
    settings = Settings(
        _env_file=None,
        QDRANT_URL="http://qdrant.internal:6333",
        QDRANT_COLLECTION_NAME="project_chunks-v1",
        QDRANT_TIMEOUT_SECONDS=45,
    )

    assert settings.qdrant_url == "http://qdrant.internal:6333"
    assert settings.qdrant_collection_name == "project_chunks-v1"
    assert settings.qdrant_timeout_seconds == 45


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("QDRANT_URL", ""),
        ("QDRANT_URL", "ftp://localhost:6333"),
        ("QDRANT_URL", "http://user:password@localhost:6333"),
        ("QDRANT_URL", "http://localhost:6333?token=synthetic"),
        ("QDRANT_URL", "http://localhost:6333#fragment"),
        ("QDRANT_COLLECTION_NAME", ""),
        ("QDRANT_COLLECTION_NAME", "bad/name"),
        ("QDRANT_COLLECTION_NAME", "x" * 256),
        ("QDRANT_TIMEOUT_SECONDS", 0),
        ("QDRANT_TIMEOUT_SECONDS", 301),
        ("QDRANT_TIMEOUT_SECONDS", True),
        ("QDRANT_TIMEOUT_SECONDS", float("nan")),
        ("QDRANT_TIMEOUT_SECONDS", float("inf")),
    ],
)
def test_settings_rejects_invalid_qdrant_configuration(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})


def test_settings_default_document_upload_limits() -> None:
    settings = Settings(_env_file=None)

    assert settings.document_storage_root.is_absolute()
    assert settings.document_storage_root.name == "uploads"
    assert settings.document_max_upload_bytes == 20_971_520
    assert settings.document_max_files_per_knowledge_base == 50


def test_settings_default_rag_chunk_bounds() -> None:
    settings = Settings(_env_file=None)

    assert settings.rag_chunk_size == 1000
    assert settings.rag_chunk_overlap == 150


def test_settings_default_document_processing_limits() -> None:
    settings = Settings(_env_file=None)

    assert settings.document_max_pdf_pages == 500
    assert settings.document_max_extracted_characters == 10_000_000
    assert settings.document_max_markdown_structures == 20_000
    assert settings.document_max_chunks == 10_000
    assert settings.document_processing_limits.max_pdf_pages == 500


def test_settings_resolves_relative_document_storage_from_backend() -> None:
    settings = Settings(
        _env_file=None,
        DOCUMENT_STORAGE_ROOT="runtime_uploads",
    )

    assert settings.document_storage_root.is_absolute()
    assert settings.document_storage_root.name == "runtime_uploads"
    assert settings.document_storage_root.parent.name == "backend"


def test_settings_preserves_document_storage_root_symlink(
    tmp_path: Path,
) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    link = tmp_path / "uploads-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    settings = Settings(
        _env_file=None,
        DOCUMENT_STORAGE_ROOT=str(link),
    )

    assert settings.document_storage_root == link.absolute()
    assert settings.document_storage_root.is_symlink()


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


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("DOCUMENT_MAX_PDF_PAGES", 0),
        ("DOCUMENT_MAX_PDF_PAGES", 10_001),
        ("DOCUMENT_MAX_EXTRACTED_CHARACTERS", 0),
        ("DOCUMENT_MAX_EXTRACTED_CHARACTERS", 100_000_001),
        ("DOCUMENT_MAX_MARKDOWN_STRUCTURES", 0),
        ("DOCUMENT_MAX_MARKDOWN_STRUCTURES", 100_001),
        ("DOCUMENT_MAX_CHUNKS", 0),
        ("DOCUMENT_MAX_CHUNKS", 100_001),
    ],
)
def test_settings_rejects_invalid_document_processing_limits(
    field_name: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})


def test_document_dependency_passes_configured_processing_limits() -> None:
    settings = Settings(
        _env_file=None,
        DOCUMENT_MAX_PDF_PAGES=7,
        DOCUMENT_MAX_EXTRACTED_CHARACTERS=700,
        DOCUMENT_MAX_MARKDOWN_STRUCTURES=70,
        DOCUMENT_MAX_CHUNKS=17,
    )
    session = Session()
    try:
        service = get_document_service(session=session, settings=settings)

        assert service._ingestion._processing_limits == (
            settings.document_processing_limits
        )
    finally:
        session.close()


@pytest.mark.parametrize(
    ("size", "overlap"),
    [
        (99, 0),
        (10_001, 0),
        (1000, -1),
        (1000, 1000),
        (1000, 2001),
    ],
)
def test_settings_rejects_invalid_rag_chunk_bounds(
    size: int,
    overlap: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            RAG_CHUNK_SIZE=size,
            RAG_CHUNK_OVERLAP=overlap,
        )


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
