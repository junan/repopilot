"""ASGI tests for the health endpoint."""

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://repopilot:repopilot@localhost:5432/repopilot",
    )
    return TestClient(create_app(settings))


def test_health_returns_ok() -> None:
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "RepoPilot",
        "environment": "local",
    }


def test_unknown_route_returns_404() -> None:
    response = _client().get("/does-not-exist")

    assert response.status_code == 404
