from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        return path.resolve()

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
