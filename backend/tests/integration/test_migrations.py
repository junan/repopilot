"""Integration tests for Alembic upgrade and downgrade."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from app.core.config import get_settings
from app.db.base import Base
from app.models import AgentRun, RunStep, Task  # noqa: F401 — register metadata

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


def test_upgrade_creates_task_run_and_step_tables(migrated_database: Engine) -> None:
    command.upgrade(_alembic_config(), "head")

    inspector = inspect(migrated_database)
    tables = set(inspector.get_table_names())
    assert {"tasks", "agent_runs", "run_steps"} <= tables

    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    assert task_columns == {
        "id",
        "description",
        "status",
        "idempotency_key",
        "created_at",
        "updated_at",
    }

    run_columns = {column["name"] for column in inspector.get_columns("agent_runs")}
    assert run_columns == {
        "id",
        "task_id",
        "attempt",
        "status",
        "checkpoint",
        "prompt_tokens",
        "completion_tokens",
        "cost_usd",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
    }

    step_columns = {column["name"] for column in inspector.get_columns("run_steps")}
    assert step_columns == {
        "id",
        "run_id",
        "sequence",
        "action",
        "status",
        "result",
        "created_at",
        "started_at",
        "finished_at",
    }

    run_uniques = inspector.get_unique_constraints("agent_runs")
    assert any(
        sorted(constraint["column_names"]) == ["attempt", "task_id"]
        for constraint in run_uniques
    )

    step_uniques = inspector.get_unique_constraints("run_steps")
    assert any(
        sorted(constraint["column_names"]) == ["run_id", "sequence"]
        for constraint in step_uniques
    )


def test_downgrade_to_base_drops_all_app_tables(migrated_database: Engine) -> None:
    command.upgrade(_alembic_config(), "head")
    command.downgrade(_alembic_config(), "base")

    inspector = inspect(migrated_database)
    tables = set(inspector.get_table_names())
    assert "tasks" not in tables
    assert "agent_runs" not in tables
    assert "run_steps" not in tables


def test_downgrade_one_revision_keeps_tasks(migrated_database: Engine) -> None:
    command.upgrade(_alembic_config(), "head")
    command.downgrade(_alembic_config(), "20251105_0001")

    inspector = inspect(migrated_database)
    tables = set(inspector.get_table_names())
    assert "tasks" in tables
    assert "agent_runs" not in tables
    assert "run_steps" not in tables
