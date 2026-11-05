"""Unit tests for database session helpers."""

from app.db.session import normalize_database_url


def test_normalize_plain_postgresql_url() -> None:
    assert (
        normalize_database_url(
            "postgresql://repopilot:repopilot@localhost:5432/repopilot"
        )
        == "postgresql+psycopg://repopilot:repopilot@localhost:5432/repopilot"
    )


def test_normalize_postgres_scheme() -> None:
    assert (
        normalize_database_url("postgres://user:pass@db:5432/app")
        == "postgresql+psycopg://user:pass@db:5432/app"
    )


def test_normalize_leaves_psycopg_url_unchanged() -> None:
    url = "postgresql+psycopg://repopilot:repopilot@localhost:5432/repopilot"
    assert normalize_database_url(url) == url
