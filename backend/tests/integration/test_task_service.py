"""Integration tests for TaskService against PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from app.models import TaskStatus
from app.services import IdempotencyConflictError, TaskNotFoundError, TaskService
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_create_starts_as_pending(db_session: Session) -> None:
    service = TaskService(db_session)

    result = service.create("Investigate duplicate bookings")

    assert result.created is True
    task = result.task
    assert isinstance(task.id, uuid.UUID)
    assert task.description == "Investigate duplicate bookings"
    assert task.status is TaskStatus.PENDING
    assert task.idempotency_key is None


def test_get_returns_created_task(db_session: Session) -> None:
    service = TaskService(db_session)
    created = service.create("Fix flaky auth test").task

    fetched = service.get(created.id)

    assert fetched.id == created.id
    assert fetched.description == created.description


def test_get_missing_task_raises_typed_error(db_session: Session) -> None:
    service = TaskService(db_session)
    missing_id = uuid.uuid4()

    with pytest.raises(TaskNotFoundError) as exc_info:
        service.get(missing_id)

    assert exc_info.value.task_id == missing_id


def test_list_returns_newest_first(db_session: Session) -> None:
    service = TaskService(db_session)
    first = service.create("first task").task
    second = service.create("second task").task

    tasks = service.list()

    assert {task.id for task in tasks} >= {first.id, second.id}
    assert [task.created_at for task in tasks] == sorted(
        (task.created_at for task in tasks),
        reverse=True,
    )


def test_idempotent_create_replays_same_body(db_session: Session) -> None:
    service = TaskService(db_session)
    key = "booking-fix-1"
    first = service.create("same description", idempotency_key=key)

    replayed = service.create("same description", idempotency_key=key)

    assert first.created is True
    assert replayed.created is False
    assert replayed.task.id == first.task.id
    assert replayed.task.description == first.task.description


def test_idempotent_create_rejects_different_body(db_session: Session) -> None:
    service = TaskService(db_session)
    key = "booking-fix-2"
    service.create("original description", idempotency_key=key)

    with pytest.raises(IdempotencyConflictError) as exc_info:
        service.create("different description", idempotency_key=key)

    assert exc_info.value.idempotency_key == key
