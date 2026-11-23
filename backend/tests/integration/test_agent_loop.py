"""Integration tests for the budgeted planning agent loop."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.agents import (
    AgentLoop,
    AgentLoopBudget,
    FakeModelClient,
    ImplementationPlan,
    ToolCallRequest,
    get_task_plan,
)
from app.models import AgentRunStatus, Task
from tests.support.sample_repo import BOOKING_SAMPLE_REPO

pytestmark = pytest.mark.integration


def _task(db_session: Session) -> Task:
    task = Task(description="Fix duplicate reservations on retry")
    db_session.add(task)
    db_session.flush()
    return task


def test_loop_plans_uses_tools_and_stores_final_plan(db_session: Session) -> None:
    task = _task(db_session)
    final = ImplementationPlan(
        findings=["create_reservation ignores idempotency_key"],
        files_to_change=["booking/handler.py"],
        steps=["Return existing reservation for repeated keys"],
        risks=["Concurrent retries still need locking"],
    )
    client = FakeModelClient(
        final_plan=final,
        tool_calls=[
            ToolCallRequest(
                name="search_text",
                arguments={"query": "idempotency_key"},
            ),
            ToolCallRequest(
                name="read_file",
                arguments={"relative_path": "booking/handler.py"},
            ),
        ],
    )
    loop = AgentLoop(
        session=db_session,
        model_client=client,
        workspace_root=BOOKING_SAMPLE_REPO,
    )

    result = loop.run(task.id)

    assert result.failure_reason is None
    assert result.run.status is AgentRunStatus.SUCCEEDED
    assert result.plan == final
    actions = [step.action for step in result.steps]
    assert actions[0] == "create_plan"
    assert "search_text" in actions
    assert "read_file" in actions
    assert actions[-1] == "final_plan"

    # Tool results are fed back as context data for the final plan call.
    assert len(client.calls) == 2
    assert "tool:search_text" in client.calls[1].repository_context
    assert "booking/handler.py" in client.calls[1].repository_context

    view = get_task_plan(db_session, task.id)
    assert view.run_id == result.run.id
    assert view.plan == final
    assert [step.action for step in view.steps] == actions


def test_tool_call_budget_stops_run_as_failed(db_session: Session) -> None:
    task = _task(db_session)
    client = FakeModelClient(
        tool_calls=[
            ToolCallRequest(name="list_files", arguments={}),
            ToolCallRequest(
                name="search_text",
                arguments={"query": "reservation"},
            ),
        ]
    )
    loop = AgentLoop(
        session=db_session,
        model_client=client,
        workspace_root=BOOKING_SAMPLE_REPO,
        budget=AgentLoopBudget(max_tool_calls=1, max_steps=20),
    )

    result = loop.run(task.id)

    assert result.run.status is AgentRunStatus.FAILED
    assert result.plan is None
    assert result.failure_reason is not None
    assert "tool-call budget exceeded" in result.failure_reason
    assert any(step.action == "budget_exceeded" for step in result.steps)
    assert sum(1 for step in result.steps if step.action == "list_files") == 1
    assert all(step.action != "search_text" for step in result.steps)


def test_step_budget_stops_before_final_plan(db_session: Session) -> None:
    task = _task(db_session)
    client = FakeModelClient(
        tool_calls=[ToolCallRequest(name="list_files", arguments={})]
    )
    # create_plan + list_files + final_plan would be 3 steps; cap at 2.
    loop = AgentLoop(
        session=db_session,
        model_client=client,
        workspace_root=BOOKING_SAMPLE_REPO,
        budget=AgentLoopBudget(max_steps=2, max_tool_calls=5),
    )

    result = loop.run(task.id)

    assert result.run.status is AgentRunStatus.FAILED
    assert "step budget exceeded" in (result.failure_reason or "")
    assert all(step.action != "final_plan" for step in result.steps)


def test_cost_budget_stops_after_usage_accumulates(db_session: Session) -> None:
    task = _task(db_session)
    client = FakeModelClient(
        tool_calls=[ToolCallRequest(name="list_files", arguments={})],
        cost_usd=Decimal("0.50"),
    )
    loop = AgentLoop(
        session=db_session,
        model_client=client,
        workspace_root=BOOKING_SAMPLE_REPO,
        budget=AgentLoopBudget(max_cost_usd=Decimal("0.25"), max_steps=20),
    )

    result = loop.run(task.id)

    assert result.run.status is AgentRunStatus.FAILED
    assert "cost budget exceeded" in (result.failure_reason or "")


def test_runtime_budget_can_fail_run(db_session: Session) -> None:
    task = _task(db_session)
    client = FakeModelClient()
    loop = AgentLoop(
        session=db_session,
        model_client=client,
        workspace_root=BOOKING_SAMPLE_REPO,
        budget=AgentLoopBudget(max_runtime_seconds=0.0, max_steps=20),
    )

    result = loop.run(task.id)

    assert result.run.status is AgentRunStatus.FAILED
    assert "runtime budget exceeded" in (result.failure_reason or "")


def test_get_task_plan_without_runs(db_session: Session) -> None:
    task = _task(db_session)

    view = get_task_plan(db_session, task.id)

    assert view.run_id is None
    assert view.plan is None
    assert view.steps == []
