"""Integration tests for AgentRun and RunStep models."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AgentRun,
    AgentRunStatus,
    RunStep,
    RunStepStatus,
    Task,
)

pytestmark = pytest.mark.integration


def test_run_belongs_to_task_with_usage_defaults(db_session: Session) -> None:
    task = Task(description="Investigate duplicate bookings")
    db_session.add(task)
    db_session.flush()

    run = AgentRun(task_id=task.id, attempt=1)
    db_session.add(run)
    db_session.flush()

    assert run.status is AgentRunStatus.PENDING
    assert run.prompt_tokens == 0
    assert run.completion_tokens == 0
    assert run.cost_usd == Decimal("0")
    assert run.checkpoint is None
    assert run.task_id == task.id


def test_steps_are_ordered_by_sequence(db_session: Session) -> None:
    task = Task(description="plan then search")
    run = AgentRun(task=task, attempt=1)
    db_session.add_all(
        [
            task,
            run,
            RunStep(
                run=run,
                sequence=2,
                action="search_text",
                status=RunStepStatus.SUCCEEDED,
            ),
            RunStep(
                run=run,
                sequence=1,
                action="list_files",
                status=RunStepStatus.SUCCEEDED,
            ),
        ]
    )
    db_session.flush()
    db_session.refresh(run)

    assert [step.sequence for step in run.steps] == [1, 2]
    assert [step.action for step in run.steps] == ["list_files", "search_text"]


def test_step_sequence_must_be_unique_per_run(db_session: Session) -> None:
    task = Task(description="duplicate sequence")
    run = AgentRun(task=task, attempt=1)
    db_session.add_all(
        [
            task,
            run,
            RunStep(run=run, sequence=1, action="list_files"),
        ]
    )
    db_session.flush()

    db_session.add(RunStep(run=run, sequence=1, action="read_file"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_task_attempt_must_be_unique(db_session: Session) -> None:
    task = Task(description="duplicate attempt")
    db_session.add(task)
    db_session.flush()

    db_session.add(AgentRun(task_id=task.id, attempt=1))
    db_session.flush()

    db_session.add(AgentRun(task_id=task.id, attempt=1))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_run_stores_token_and_cost_fields(db_session: Session) -> None:
    task = Task(description="usage accounting")
    run = AgentRun(
        task=task,
        attempt=1,
        status=AgentRunStatus.RUNNING,
        prompt_tokens=120,
        completion_tokens=40,
        cost_usd=Decimal("0.012500"),
        checkpoint='{"phase":"planning"}',
    )
    db_session.add_all([task, run])
    db_session.flush()

    assert run.prompt_tokens == 120
    assert run.completion_tokens == 40
    assert run.cost_usd == Decimal("0.012500")
    assert run.checkpoint == '{"phase":"planning"}'
