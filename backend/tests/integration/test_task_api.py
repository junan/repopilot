"""Integration tests for the task HTTP API."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from app.api.deps import get_db
from app.core.config import Settings
from app.main import create_app
from app.schemas.tasks import DESCRIPTION_MAX_LENGTH
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db_session: Session, database_url: str) -> Generator[TestClient]:
    settings = Settings(_env_file=None, database_url=database_url)
    app = create_app(settings)

    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_task_returns_201(client: TestClient) -> None:
    response = client.post(
        "/tasks",
        json={"description": "Investigate duplicate bookings"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["description"] == "Investigate duplicate bookings"
    assert payload["status"] == "PENDING"
    assert payload["idempotency_key"] is None
    assert uuid.UUID(payload["id"])


def test_create_task_replay_returns_200(client: TestClient) -> None:
    headers = {"Idempotency-Key": "api-replay-1"}
    body = {"description": "same body"}

    first = client.post("/tasks", json=body, headers=headers)
    second = client.post("/tasks", json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_create_task_idempotency_conflict_returns_409(client: TestClient) -> None:
    headers = {"Idempotency-Key": "api-conflict-1"}
    client.post("/tasks", json={"description": "original"}, headers=headers)

    response = client.post(
        "/tasks",
        json={"description": "changed"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "idempotency_conflict",
        "message": (
            "Idempotency key already used with a different request body: "
            "api-conflict-1"
        ),
    }


def test_create_task_invalid_body_returns_422(client: TestClient) -> None:
    response = client.post("/tasks", json={"description": ""})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert "message" in payload


def test_create_task_description_too_long_returns_422(client: TestClient) -> None:
    response = client.post(
        "/tasks",
        json={"description": "x" * (DESCRIPTION_MAX_LENGTH + 1)},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_list_tasks_returns_created_tasks(client: TestClient) -> None:
    first = client.post("/tasks", json={"description": "first"}).json()
    second = client.post("/tasks", json={"description": "second"}).json()

    response = client.get("/tasks")

    assert response.status_code == 200
    tasks = response.json()
    ids = {task["id"] for task in tasks}
    assert first["id"] in ids
    assert second["id"] in ids
    created_ats = [task["created_at"] for task in tasks]
    assert created_ats == sorted(created_ats, reverse=True)


def test_get_task_returns_200(client: TestClient) -> None:
    created = client.post(
        "/tasks",
        json={"description": "fetch me"},
    ).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["description"] == "fetch me"


def test_get_missing_task_returns_404(client: TestClient) -> None:
    missing_id = uuid.uuid4()

    response = client.get(f"/tasks/{missing_id}")

    assert response.status_code == 404
    assert response.json() == {
        "code": "task_not_found",
        "message": f"Task not found: {missing_id}",
    }
