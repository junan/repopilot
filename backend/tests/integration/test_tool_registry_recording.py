"""Integration tests for tool calls recorded as run steps."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, RunStep, RunStepStatus, Task
from app.tools import (
    InvalidToolArgumentsError,
    ToolRegistry,
    UnknownToolError,
)
from tests.support.sample_repo import BOOKING_SAMPLE_REPO

pytestmark = pytest.mark.integration


def _run(db_session: Session) -> AgentRun:
    task = Task(description="Inspect booking sample")
    run = AgentRun(task=task, attempt=1)
    db_session.add_all([task, run])
    db_session.flush()
    return run


def test_successful_tool_call_is_recorded_as_step(db_session: Session) -> None:
    run = _run(db_session)
    registry = ToolRegistry(BOOKING_SAMPLE_REPO)

    outcome = registry.call_and_record(
        name="search_text",
        arguments={"query": "idempotency_key"},
        session=db_session,
        run=run,
    )

    assert outcome.step is not None
    assert outcome.step.sequence == 1
    assert outcome.step.action == "search_text"
    assert outcome.step.status is RunStepStatus.SUCCEEDED
    assert outcome.step.result is not None
    payload = json.loads(outcome.step.result)
    assert any(match["path"] == "booking/handler.py" for match in payload["matches"])

    steps = db_session.scalars(
        select(RunStep).where(RunStep.run_id == run.id).order_by(RunStep.sequence)
    ).all()
    assert len(steps) == 1


def test_unknown_tool_records_failed_step_without_handler(
    db_session: Session,
) -> None:
    run = _run(db_session)
    registry = ToolRegistry(BOOKING_SAMPLE_REPO)

    with pytest.raises(UnknownToolError):
        registry.call_and_record(
            name="apply_patch",
            arguments={},
            session=db_session,
            run=run,
        )

    step = db_session.scalars(select(RunStep).where(RunStep.run_id == run.id)).one()
    assert step.status is RunStepStatus.FAILED
    assert step.action == "apply_patch"
    assert "Unknown tool" in (step.result or "")


def test_invalid_arguments_record_failed_step(db_session: Session) -> None:
    run = _run(db_session)
    registry = ToolRegistry(BOOKING_SAMPLE_REPO)

    with pytest.raises(InvalidToolArgumentsError):
        registry.call_and_record(
            name="read_file",
            arguments={"relative_path": ""},
            session=db_session,
            run=run,
        )

    step = db_session.scalars(select(RunStep).where(RunStep.run_id == run.id)).one()
    assert step.status is RunStepStatus.FAILED
    assert "Invalid arguments" in (step.result or "")


def test_result_is_size_limited(db_session: Session) -> None:
    run = _run(db_session)
    registry = ToolRegistry(BOOKING_SAMPLE_REPO)

    outcome = registry.call_and_record(
        name="read_file",
        arguments={"relative_path": "booking/handler.py"},
        session=db_session,
        run=run,
        max_result_chars=40,
    )

    assert outcome.step is not None
    assert outcome.step.result is not None
    assert len(outcome.step.result) <= 40
    assert outcome.step.result.endswith("...[truncated]")
