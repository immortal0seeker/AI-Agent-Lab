import os
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.rag.processing_limits import DocumentProcessingLimits


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Lab Backend", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(
        default="sqlite:///./ai_agent_lab.db",
        alias="DATABASE_URL",
    )
    qdrant_url: str = Field(
        default="http://localhost:6333",
        alias="QDRANT_URL",
    )
    backend_cors_origins: str = Field(
        default="http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )
    openai_compatible_base_url: str = Field(
        default="",
        alias="OPENAI_COMPATIBLE_BASE_URL",
    )
    openai_compatible_api_key: SecretStr | None = Field(
        default=None,
        alias="OPENAI_COMPATIBLE_API_KEY",
    )
    openai_compatible_model: str = Field(
        default="",
        alias="OPENAI_COMPATIBLE_MODEL",
    )
    openai_compatible_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        alias="OPENAI_COMPATIBLE_TIMEOUT_SECONDS",
    )
    embedding_provider: str = Field(
        default="openai_compatible",
        alias="EMBEDDING_PROVIDER",
    )
    openai_compatible_embedding_base_url: str = Field(
        default="",
        alias="OPENAI_COMPATIBLE_EMBEDDING_BASE_URL",
    )
    openai_compatible_embedding_api_key: SecretStr | None = Field(
        default=None,
        alias="OPENAI_COMPATIBLE_EMBEDDING_API_KEY",
    )
    openai_compatible_embedding_model: str = Field(
        default="",
        alias="OPENAI_COMPATIBLE_EMBEDDING_MODEL",
    )
    openai_compatible_embedding_dimension: int | None = Field(
        default=None,
        gt=0,
        le=65_536,
        alias="OPENAI_COMPATIBLE_EMBEDDING_DIMENSION",
    )
    openai_compatible_embedding_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        le=3600,
        allow_inf_nan=False,
        alias="OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS",
    )
    agent_run_timeout_seconds: float = Field(
        default=120.0,
        gt=0,
        le=3600,
        allow_inf_nan=False,
        alias="AGENT_RUN_TIMEOUT_SECONDS",
    )
    model_registry_path: Path | None = Field(
        default=None,
        alias="MODEL_REGISTRY_PATH",
    )
    document_storage_root: Path = Field(
        default=BACKEND_ROOT / "uploads",
        alias="DOCUMENT_STORAGE_ROOT",
    )
    document_max_upload_bytes: int = Field(
        default=20_971_520,
        gt=0,
        le=1_073_741_824,
        alias="DOCUMENT_MAX_UPLOAD_BYTES",
    )
    document_max_files_per_knowledge_base: int = Field(
        default=50,
        gt=0,
        le=10_000,
        alias="DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE",
    )
    document_max_pdf_pages: int = Field(
        default=500,
        gt=0,
        le=10_000,
        alias="DOCUMENT_MAX_PDF_PAGES",
    )
    document_max_extracted_characters: int = Field(
        default=10_000_000,
        gt=0,
        le=100_000_000,
        alias="DOCUMENT_MAX_EXTRACTED_CHARACTERS",
    )
    document_max_markdown_structures: int = Field(
        default=20_000,
        gt=0,
        le=100_000,
        alias="DOCUMENT_MAX_MARKDOWN_STRUCTURES",
    )
    document_max_chunks: int = Field(
        default=10_000,
        gt=0,
        le=100_000,
        alias="DOCUMENT_MAX_CHUNKS",
    )
    rag_chunk_size: int = Field(
        default=1000,
        ge=100,
        le=10_000,
        alias="RAG_CHUNK_SIZE",
    )
    rag_chunk_overlap: int = Field(
        default=150,
        ge=0,
        le=2_000,
        alias="RAG_CHUNK_OVERLAP",
    )

    @field_validator("model_registry_path", mode="before")
    @classmethod
    def normalize_blank_model_registry_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("embedding_provider")
    @classmethod
    def normalize_embedding_provider(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("embedding provider must not be blank")
        if len(normalized) > 100:
            raise ValueError(
                "embedding provider must be at most 100 characters"
            )
        return normalized

    @field_validator("document_storage_root", mode="before")
    @classmethod
    def resolve_document_storage_root(cls, value: object) -> Path:
        if isinstance(value, str) and not value.strip():
            raise ValueError("document storage root must not be blank")
        try:
            path = Path(value)  # type: ignore[arg-type]
        except TypeError as exc:
            raise ValueError("document storage root must be a path") from exc
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return Path(os.path.abspath(path))

    @model_validator(mode="after")
    def validate_rag_chunk_window(self) -> Self:
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError(
                "RAG chunk overlap must be smaller than chunk size"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def backend_cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def document_processing_limits(self) -> DocumentProcessingLimits:
        return DocumentProcessingLimits(
            max_pdf_pages=self.document_max_pdf_pages,
            max_extracted_characters=self.document_max_extracted_characters,
            max_markdown_structures=self.document_max_markdown_structures,
            max_chunks=self.document_max_chunks,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
