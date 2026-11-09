"""Typed errors for task service operations."""

from __future__ import annotations

import uuid

from app.models.task import TaskStatus


class TaskServiceError(Exception):
    """Base class for task service failures."""


class TaskNotFoundError(TaskServiceError):
    """Raised when a task id does not exist."""

    def __init__(self, task_id: uuid.UUID) -> None:
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class IdempotencyConflictError(TaskServiceError):
    """Raised when an idempotency key is reused with a different request body."""

    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(
            "Idempotency key already used with a different request body: "
            f"{idempotency_key}"
        )


class IllegalTaskTransitionError(TaskServiceError):
    """Raised when a status change is not allowed by the transition map."""

    def __init__(self, current: TaskStatus, new: TaskStatus) -> None:
        self.current = current
        self.new = new
        super().__init__(f"Illegal task transition: {current.value} -> {new.value}")
