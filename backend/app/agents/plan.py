"""Structured implementation plan returned by the model client."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImplementationPlan(BaseModel):
    """Auditable plan grounded in repository investigation."""

    model_config = ConfigDict(extra="ignore")

    findings: list[str] = Field(default_factory=list)
    files_to_change: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    """Inputs for a structured planning call."""

    model_config = ConfigDict(extra="ignore")

    task_description: str = Field(min_length=1)
    repository_context: str = ""


class ToolCallRequest(BaseModel):
    """Model-proposed tool invocation. Arguments are validated by the registry."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
