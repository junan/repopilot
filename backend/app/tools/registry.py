"""Typed tool registry with validation and run-step recording."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AgentRun, RunStep, RunStepStatus
from app.tools.repo_tools import list_files, read_file, search_text
from app.tools.schemas import ListFilesArgs, ReadFileArgs, SearchTextArgs

DEFAULT_MAX_RESULT_CHARS = 8_000

Handler = Callable[[BaseModel], BaseModel]


class ToolRegistryError(ValueError):
    """Base class for tool registry failures."""


class UnknownToolError(ToolRegistryError):
    """Raised when a tool name is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Unknown tool: {name}")


class InvalidToolArgumentsError(ToolRegistryError):
    """Raised when tool arguments fail schema validation."""

    def __init__(self, name: str, details: str) -> None:
        self.name = name
        self.details = details
        super().__init__(f"Invalid arguments for tool {name}: {details}")


@dataclass(frozen=True)
class ToolSpec:
    """Registered tool metadata."""

    name: str
    args_model: type[BaseModel]
    handler: Handler


@dataclass(frozen=True)
class ToolCallResult:
    """Outcome of a validated tool invocation."""

    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    step: RunStep | None = None


class ToolRegistry:
    """Validate and execute allowlisted repository tools."""

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        self._tools: dict[str, ToolSpec] = {}
        self._register_defaults()

    def names(self) -> frozenset[str]:
        return frozenset(self._tools)

    def call(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolCallResult:
        """Validate arguments and execute a tool without persisting a run step."""
        spec, parsed = self._validate(name, arguments or {})
        result_model = spec.handler(parsed)
        return ToolCallResult(
            name=name,
            arguments=parsed.model_dump(),
            result=result_model.model_dump(mode="json"),
        )

    def call_and_record(
        self,
        *,
        name: str,
        arguments: dict[str, Any] | None = None,
        session: Session,
        run: AgentRun,
        max_result_chars: int = DEFAULT_MAX_RESULT_CHARS,
    ) -> ToolCallResult:
        """Validate, execute, and append a size-limited result as a run step."""
        if max_result_chars < 1:
            raise ValueError("max_result_chars must be >= 1")

        raw_arguments = arguments or {}
        sequence = _next_sequence(session, run.id)
        step = RunStep(
            run_id=run.id,
            sequence=sequence,
            action=name,
            status=RunStepStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        session.add(step)
        session.flush()

        try:
            # Fail closed before the tool handler runs.
            spec, parsed = self._validate(name, raw_arguments)
            try:
                result_model = spec.handler(parsed)
            except Exception as exc:
                step.status = RunStepStatus.FAILED
                step.result = _dump_limited({"error": str(exc)}, max_result_chars)
                raise

            payload = result_model.model_dump(mode="json")
            step.status = RunStepStatus.SUCCEEDED
            step.result = _dump_limited(payload, max_result_chars)
            return ToolCallResult(
                name=name,
                arguments=parsed.model_dump(),
                result=payload,
                step=step,
            )
        except (UnknownToolError, InvalidToolArgumentsError) as exc:
            step.status = RunStepStatus.FAILED
            step.result = _dump_limited({"error": str(exc)}, max_result_chars)
            raise
        finally:
            step.finished_at = datetime.now(UTC)
            session.flush()

    def _validate(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> tuple[ToolSpec, BaseModel]:
        try:
            spec = self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(name) from exc

        try:
            parsed = spec.args_model.model_validate(arguments)
        except ValidationError as exc:
            raise InvalidToolArgumentsError(name, str(exc)) from exc
        return spec, parsed

    def _register_defaults(self) -> None:
        workspace = self._workspace_root

        def handle_list(args: BaseModel) -> BaseModel:
            assert isinstance(args, ListFilesArgs)
            return list_files(
                workspace,
                args.relative_path,
                max_depth=args.max_depth,
                max_entries=args.max_entries,
            )

        def handle_read(args: BaseModel) -> BaseModel:
            assert isinstance(args, ReadFileArgs)
            return read_file(
                workspace,
                args.relative_path,
                max_bytes=args.max_bytes,
            )

        def handle_search(args: BaseModel) -> BaseModel:
            assert isinstance(args, SearchTextArgs)
            return search_text(
                workspace,
                args.query,
                relative_path=args.relative_path,
                max_matches=args.max_matches,
                max_depth=args.max_depth,
                max_file_bytes=args.max_file_bytes,
            )

        for spec in (
            ToolSpec("list_files", ListFilesArgs, handle_list),
            ToolSpec("read_file", ReadFileArgs, handle_read),
            ToolSpec("search_text", SearchTextArgs, handle_search),
        ):
            self._tools[spec.name] = spec


def _next_sequence(session: Session, run_id: UUID) -> int:
    current = session.scalar(
        select(func.coalesce(func.max(RunStep.sequence), 0)).where(
            RunStep.run_id == run_id
        )
    )
    return int(current or 0) + 1


def _dump_limited(payload: dict[str, Any], max_chars: int) -> str:
    text = json.dumps(payload, ensure_ascii=True, default=str)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 15] + "...[truncated]"
