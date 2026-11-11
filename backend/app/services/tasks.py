"""Task create, list, and get operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.services.errors import IdempotencyConflictError, TaskNotFoundError


@dataclass(frozen=True)
class CreateTaskResult:
    """Outcome of a create-or-replay operation."""

    task: Task
    created: bool


class TaskService:
    """Application service for persisted engineering tasks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        description: str,
        *,
        idempotency_key: str | None = None,
    ) -> CreateTaskResult:
        """Create a task, or replay a prior create for the same idempotency key."""
        if idempotency_key is not None:
            existing = self._find_by_idempotency_key(idempotency_key)
            if existing is not None:
                if existing.description != description:
                    raise IdempotencyConflictError(idempotency_key)
                return CreateTaskResult(task=existing, created=False)

        task = Task(
            description=description,
            status=TaskStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        self._session.add(task)
        self._session.flush()
        return CreateTaskResult(task=task, created=True)

    def get(self, task_id: uuid.UUID) -> Task:
        """Return a task by id or raise TaskNotFoundError."""
        task = self._session.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def list(self) -> list[Task]:
        """Return tasks newest-first."""
        statement = select(Task).order_by(Task.created_at.desc(), Task.id.desc())
        return list(self._session.scalars(statement).all())

    def _find_by_idempotency_key(self, idempotency_key: str) -> Task | None:
        statement = select(Task).where(Task.idempotency_key == idempotency_key)
        return self._session.scalar(statement)
