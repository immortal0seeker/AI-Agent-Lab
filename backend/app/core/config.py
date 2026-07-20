from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Lab Backend", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(
        default="sqlite:///./ai_agent_lab.db",
        alias="DATABASE_URL",
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

    @field_validator("model_registry_path", mode="before")
    @classmethod
    def normalize_blank_model_registry_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

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
