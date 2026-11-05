"""Unit tests for environment settings."""

import pytest
from app.core.config import Settings, get_settings
from pydantic import ValidationError


def test_defaults_when_database_url_provided() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://repopilot:repopilot@localhost:5432/repopilot",
    )

    assert settings.app_name == "RepoPilot"
    assert settings.environment == "local"
    assert settings.database_url.startswith("postgresql://")


def test_custom_values_override_defaults() -> None:
    settings = Settings(
        _env_file=None,
        app_name="RepoPilot Test",
        environment="test",
        database_url="postgresql+psycopg://user:pass@db:5432/repopilot",
    )

    assert settings.app_name == "RepoPilot Test"
    assert settings.environment == "test"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/repopilot"


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "database_url" in str(exc_info.value)


def test_empty_database_url_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, database_url="   ")

    assert "database_url" in str(exc_info.value)


def test_non_postgres_database_url_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, database_url="mysql://localhost/repopilot")

    assert "PostgreSQL" in str(exc_info.value)


def test_get_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://repopilot:repopilot@localhost:5432/repopilot",
    )
    monkeypatch.setenv("APP_NAME", "FromEnv")
    monkeypatch.setenv("ENVIRONMENT", "ci")

    settings = get_settings()

    assert settings.app_name == "FromEnv"
    assert settings.environment == "ci"
    get_settings.cache_clear()
