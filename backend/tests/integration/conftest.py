"""Fixtures for PostgreSQL-backed integration tests."""

import os

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_engine_from_settings
from app.models import Task  # noqa: F401 — register metadata


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://repopilot:repopilot@localhost:55432/repopilot",
    )


@pytest.fixture(scope="session")
def engine(database_url: str) -> Engine:
    settings = Settings(_env_file=None, database_url=database_url)
    engine = create_engine_from_settings(settings)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="session", autouse=True)
def require_postgres(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
