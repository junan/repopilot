"""Environment-based application settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RepoPilot"
    environment: str = "local"
    database_url: str = Field(..., description="PostgreSQL connection URL")
    openai_api_key: str | None = Field(
        default=None,
        description="Optional OpenAI API key for planning calls",
    )
    openai_model: str = Field(
        default="gpt-4.1-mini",
        description="OpenAI model used for structured planning",
    )

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_postgres(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("database_url must not be empty")
        allowed_prefixes = (
            "postgresql://",
            "postgresql+psycopg://",
            "postgres://",
        )
        if not normalized.startswith(allowed_prefixes):
            raise ValueError("database_url must be a PostgreSQL URL")
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for the current process."""
    return Settings()
