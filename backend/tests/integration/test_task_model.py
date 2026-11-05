"""Integration tests for the Task ORM model against PostgreSQL."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus

pytestmark = pytest.mark.integration


def test_task_defaults_to_pending(db_session: Session) -> None:
    task = Task(description="Investigate duplicate bookings")
    db_session.add(task)
    db_session.flush()

    assert isinstance(task.id, uuid.UUID)
    assert task.status is TaskStatus.PENDING
    assert task.idempotency_key is None
    assert task.created_at is not None
    assert task.updated_at is not None


def test_task_requires_description(db_session: Session) -> None:
    task = Task(description=None)  # type: ignore[arg-type]
    db_session.add(task)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_idempotency_key_must_be_unique(db_session: Session) -> None:
    db_session.add(
        Task(
            description="first",
            idempotency_key="booking-fix-1",
        )
    )
    db_session.flush()

    db_session.add(
        Task(
            description="second",
            idempotency_key="booking-fix-1",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_all_task_statuses_persist(db_session: Session) -> None:
    for status in TaskStatus:
        task = Task(
            description=f"task in {status.value}",
            status=status,
            idempotency_key=f"status-{status.value}",
        )
        db_session.add(task)

    db_session.flush()

    stored = {
        task.idempotency_key: task.status
        for task in db_session.scalars(select(Task)).all()
    }
    for status in TaskStatus:
        assert stored[f"status-{status.value}"] is status
