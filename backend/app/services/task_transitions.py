"""Pure status transition rules for engineering tasks."""

from __future__ import annotations

from app.models.task import TaskStatus
from app.services.errors import IllegalTaskTransitionError

ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset(
        {
            TaskStatus.PLANNING,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.PLANNING: frozenset(
        {
            TaskStatus.EXECUTING,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.EXECUTING: frozenset(
        {
            TaskStatus.VALIDATING,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.VALIDATING: frozenset(
        {
            TaskStatus.AWAITING_APPROVAL,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.AWAITING_APPROVAL: frozenset(
        {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def can_transition(current: TaskStatus, new: TaskStatus) -> bool:
    """Return whether moving from current to new is allowed."""
    return new in ALLOWED_TRANSITIONS[current]


def validate_transition(current: TaskStatus, new: TaskStatus) -> None:
    """Raise when the requested status change is illegal."""
    if not can_transition(current, new):
        raise IllegalTaskTransitionError(current=current, new=new)
