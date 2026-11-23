"""Budgeted planning loop: plan → tool calls → final plan."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.agents.model_client import ModelClient
from app.agents.plan import ImplementationPlan, PlanRequest
from app.models import AgentRun, AgentRunStatus, RunStep, RunStepStatus, Task
from app.services.errors import TaskNotFoundError
from app.tools.registry import DEFAULT_MAX_RESULT_CHARS, ToolRegistry


@dataclass(frozen=True)
class AgentLoopBudget:
    """Hard caps enforced by the application, not the model."""

    max_tool_calls: int = 5
    max_steps: int = 12
    max_runtime_seconds: float = 60.0
    max_prompt_tokens: int = 100_000
    max_cost_usd: Decimal = Decimal("1.000000")


@dataclass(frozen=True)
class AgentLoopResult:
    """Outcome of a budgeted planning run."""

    run: AgentRun
    plan: ImplementationPlan | None
    steps: list[RunStep]
    failure_reason: str | None = None


@dataclass(frozen=True)
class TaskPlanView:
    """Stored plan and steps for a task's latest agent run."""

    task_id: UUID
    run_id: UUID | None
    run_status: AgentRunStatus | None
    plan: ImplementationPlan | None
    steps: list[RunStep]
    failure_reason: str | None = None


class AgentLoop:
    """Runs a bounded investigate-and-plan loop for one task."""

    def __init__(
        self,
        *,
        session: Session,
        model_client: ModelClient,
        workspace_root: Path,
        budget: AgentLoopBudget | None = None,
        max_result_chars: int = DEFAULT_MAX_RESULT_CHARS,
    ) -> None:
        self._session = session
        self._model = model_client
        self._registry = ToolRegistry(workspace_root)
        self._budget = budget or AgentLoopBudget()
        self._max_result_chars = max_result_chars

    def run(self, task_id: UUID, *, attempt: int = 1) -> AgentLoopResult:
        task = self._session.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        run = AgentRun(
            task_id=task.id,
            attempt=attempt,
            status=AgentRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._session.add(run)
        self._session.flush()

        started = time.monotonic()
        context_chunks: list[str] = []
        plan: ImplementationPlan | None = None
        failure_reason: str | None = None

        try:
            failure_reason = self._budget_failure(
                run,
                started=started,
                extra_steps=1,
                tool_calls_done=0,
                pending_tool_calls=0,
            )
            if failure_reason is None:
                plan = self._record_plan(
                    run,
                    task_description=task.description,
                    repository_context="",
                    action="create_plan",
                )
                context_chunks.append(_plan_context("initial_plan", plan))
                failure_reason = self._budget_failure(
                    run,
                    started=started,
                    extra_steps=0,
                    tool_calls_done=0,
                    pending_tool_calls=0,
                )

            proposals: list = []
            if failure_reason is None:
                request = PlanRequest(
                    task_description=task.description,
                    repository_context="\n\n".join(context_chunks),
                )
                proposals = self._model.propose_tool_calls(request)
                self._apply_usage(run)

            tool_calls_done = 0
            for proposal in proposals:
                if failure_reason is not None:
                    break
                failure_reason = self._budget_failure(
                    run,
                    started=started,
                    extra_steps=1,
                    tool_calls_done=tool_calls_done,
                    pending_tool_calls=1,
                )
                if failure_reason is not None:
                    break

                outcome = self._registry.call_and_record(
                    name=proposal.name,
                    arguments=proposal.arguments,
                    session=self._session,
                    run=run,
                    max_result_chars=self._max_result_chars,
                )
                tool_calls_done += 1
                # Tool output is observation data only; it never grants permissions.
                context_chunks.append(
                    _tool_context(outcome.name, outcome.arguments, outcome.result)
                )

            if failure_reason is None:
                failure_reason = self._budget_failure(
                    run,
                    started=started,
                    extra_steps=1,
                    tool_calls_done=tool_calls_done,
                    pending_tool_calls=0,
                )

            if failure_reason is None:
                plan = self._record_plan(
                    run,
                    task_description=task.description,
                    repository_context="\n\n".join(context_chunks),
                    action="final_plan",
                )
                run.status = AgentRunStatus.SUCCEEDED
                run.checkpoint = plan.model_dump_json()
            else:
                self._fail_run(run, failure_reason)
        except Exception as exc:
            failure_reason = f"agent_loop_error: {exc}"
            self._fail_run(run, failure_reason)
        finally:
            run.finished_at = datetime.now(UTC)
            self._session.flush()

        steps = list(
            self._session.scalars(
                select(RunStep)
                .where(RunStep.run_id == run.id)
                .order_by(RunStep.sequence)
            ).all()
        )
        succeeded = run.status is AgentRunStatus.SUCCEEDED
        return AgentLoopResult(
            run=run,
            plan=plan if succeeded else None,
            steps=steps,
            failure_reason=failure_reason,
        )

    def _record_plan(
        self,
        run: AgentRun,
        *,
        task_description: str,
        repository_context: str,
        action: str,
    ) -> ImplementationPlan:
        request = PlanRequest(
            task_description=task_description,
            repository_context=repository_context,
        )
        plan = self._model.create_plan(request)
        self._apply_usage(run)

        step = RunStep(
            run_id=run.id,
            sequence=_next_sequence(self._session, run.id),
            action=action,
            status=RunStepStatus.SUCCEEDED,
            result=plan.model_dump_json(),
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        self._session.add(step)
        self._session.flush()
        return plan

    def _apply_usage(self, run: AgentRun) -> None:
        prompt_tokens, completion_tokens, cost_usd = self._model.last_usage()
        run.prompt_tokens += prompt_tokens
        run.completion_tokens += completion_tokens
        run.cost_usd = Decimal(run.cost_usd) + Decimal(cost_usd)
        self._session.flush()

    def _budget_failure(
        self,
        run: AgentRun,
        *,
        started: float,
        extra_steps: int,
        tool_calls_done: int,
        pending_tool_calls: int,
    ) -> str | None:
        budget = self._budget
        elapsed = time.monotonic() - started
        if elapsed > budget.max_runtime_seconds:
            return (
                f"runtime budget exceeded ({elapsed:.3f}s > "
                f"{budget.max_runtime_seconds}s)"
            )

        current_steps = _step_count(self._session, run.id)
        if current_steps + extra_steps > budget.max_steps:
            return (
                f"step budget exceeded ({current_steps + extra_steps} > "
                f"{budget.max_steps})"
            )

        if tool_calls_done + pending_tool_calls > budget.max_tool_calls:
            return (
                "tool-call budget exceeded "
                f"({tool_calls_done + pending_tool_calls} > {budget.max_tool_calls})"
            )

        if run.prompt_tokens > budget.max_prompt_tokens:
            return (
                f"token budget exceeded ({run.prompt_tokens} > "
                f"{budget.max_prompt_tokens})"
            )

        if Decimal(run.cost_usd) > budget.max_cost_usd:
            return f"cost budget exceeded ({run.cost_usd} > {budget.max_cost_usd})"

        return None

    def _fail_run(self, run: AgentRun, reason: str) -> None:
        run.status = AgentRunStatus.FAILED
        run.checkpoint = json.dumps({"failure_reason": reason})
        action = (
            "budget_exceeded" if "budget exceeded" in reason else "agent_loop_failed"
        )
        self._session.add(
            RunStep(
                run_id=run.id,
                sequence=_next_sequence(self._session, run.id),
                action=action,
                status=RunStepStatus.FAILED,
                result=json.dumps({"error": reason}),
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )
        )
        self._session.flush()


def get_task_plan(session: Session, task_id: UUID) -> TaskPlanView:
    """Return the latest stored plan and steps for a task."""
    task = session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError(task_id)

    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.task_id == task_id)
        .options(selectinload(AgentRun.steps))
        .order_by(AgentRun.attempt.desc(), AgentRun.created_at.desc())
        .limit(1)
    )
    if run is None:
        return TaskPlanView(
            task_id=task_id,
            run_id=None,
            run_status=None,
            plan=None,
            steps=[],
        )

    plan: ImplementationPlan | None = None
    failure_reason: str | None = None
    if run.checkpoint:
        try:
            payload = json.loads(run.checkpoint)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and "failure_reason" in payload:
            failure_reason = str(payload["failure_reason"])
        else:
            try:
                plan = ImplementationPlan.model_validate_json(run.checkpoint)
            except Exception:
                plan = None

    steps = sorted(run.steps, key=lambda step: step.sequence)
    return TaskPlanView(
        task_id=task_id,
        run_id=run.id,
        run_status=run.status,
        plan=plan,
        steps=steps,
        failure_reason=failure_reason,
    )


def _step_count(session: Session, run_id: UUID) -> int:
    count = session.scalar(
        select(func.count()).select_from(RunStep).where(RunStep.run_id == run_id)
    )
    return int(count or 0)


def _next_sequence(session: Session, run_id: UUID) -> int:
    current = session.scalar(
        select(func.coalesce(func.max(RunStep.sequence), 0)).where(
            RunStep.run_id == run_id
        )
    )
    return int(current or 0) + 1


def _plan_context(label: str, plan: ImplementationPlan) -> str:
    return f"[{label}]\n{plan.model_dump_json()}"


def _tool_context(name: str, arguments: dict, result: dict) -> str:
    return (
        f"[tool:{name}]\n"
        f"arguments={json.dumps(arguments, ensure_ascii=True)}\n"
        f"result={json.dumps(result, ensure_ascii=True)}"
    )
