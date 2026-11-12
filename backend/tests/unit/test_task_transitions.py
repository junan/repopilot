"""Unit tests for the pure task status transition map."""

import pytest

from app.models import TaskStatus
from app.services import (
    ALLOWED_TRANSITIONS,
    IllegalTaskTransitionError,
    can_transition,
    validate_transition,
)


def test_happy_path_transitions_are_allowed() -> None:
    path = [
        TaskStatus.PENDING,
        TaskStatus.PLANNING,
        TaskStatus.EXECUTING,
        TaskStatus.VALIDATING,
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.COMPLETED,
    ]
    for current, new in zip(path, path[1:], strict=False):
        assert can_transition(current, new)
        validate_transition(current, new)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (TaskStatus.PENDING, TaskStatus.CANCELLED),
        (TaskStatus.PENDING, TaskStatus.FAILED),
        (TaskStatus.PLANNING, TaskStatus.CANCELLED),
        (TaskStatus.EXECUTING, TaskStatus.FAILED),
        (TaskStatus.VALIDATING, TaskStatus.CANCELLED),
        (TaskStatus.AWAITING_APPROVAL, TaskStatus.FAILED),
    ],
)
def test_failure_and_cancel_from_active_states(
    current: TaskStatus,
    new: TaskStatus,
) -> None:
    assert can_transition(current, new)
    validate_transition(current, new)


@pytest.mark.parametrize(
    "terminal",
    [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
)
def test_terminal_states_have_no_outgoing_transitions(terminal: TaskStatus) -> None:
    assert ALLOWED_TRANSITIONS[terminal] == frozenset()
    for status in TaskStatus:
        assert not can_transition(terminal, status)


def test_illegal_transition_raises_typed_error() -> None:
    with pytest.raises(IllegalTaskTransitionError) as exc_info:
        validate_transition(TaskStatus.PENDING, TaskStatus.COMPLETED)

    error = exc_info.value
    assert error.current is TaskStatus.PENDING
    assert error.new is TaskStatus.COMPLETED
    assert "PENDING -> COMPLETED" in str(error)


def test_skipping_ahead_is_illegal() -> None:
    assert not can_transition(TaskStatus.PENDING, TaskStatus.EXECUTING)
    assert not can_transition(TaskStatus.PLANNING, TaskStatus.VALIDATING)
    assert not can_transition(TaskStatus.EXECUTING, TaskStatus.COMPLETED)
