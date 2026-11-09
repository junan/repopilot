"""Integration tests for Alembic upgrade and downgrade."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.db.base import Base
from app.models import Task  # noqa: F401 — register metadata
from sqlalchemy import Engine, inspect, text

pytestmark = pytest.mark.integration

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


@pytest.fixture
def migrated_database(
    engine: Engine,
    database_url: str,
) -> Generator[Engine]:
    """Reset schema and point Alembic at the test database URL."""
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()

    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        Base.metadata.create_all(engine)

        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        get_settings.cache_clear()


def test_upgrade_creates_tasks_table(migrated_database: Engine) -> None:
    command.upgrade(_alembic_config(), "head")

    inspector = inspect(migrated_database)
    assert "tasks" in inspector.get_table_names()

    columns = {column["name"] for column in inspector.get_columns("tasks")}
    assert columns == {
        "id",
        "description",
        "status",
        "idempotency_key",
        "created_at",
        "updated_at",
    }

    unique_constraints = inspector.get_unique_constraints("tasks")
    assert any(
        constraint["column_names"] == ["idempotency_key"]
        for constraint in unique_constraints
    )


def test_downgrade_drops_tasks_table(migrated_database: Engine) -> None:
    command.upgrade(_alembic_config(), "head")
    command.downgrade(_alembic_config(), "base")

    inspector = inspect(migrated_database)
    assert "tasks" not in inspector.get_table_names()
