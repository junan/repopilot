"""Narrow model-client interface for structured planning calls."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openai import OpenAI

from app.agents.plan import ImplementationPlan, PlanRequest

_SYSTEM_PROMPT = """\
You are RepoPilot's planning assistant.
Return a JSON object with exactly these keys:
findings, files_to_change, steps, risks.
Each value must be an array of short strings.
Ground the plan in the provided repository context.
Do not invent file paths that are absent from the context.
"""


@runtime_checkable
class ModelClient(Protocol):
    """Client that turns a task into a structured implementation plan."""

    def create_plan(self, request: PlanRequest) -> ImplementationPlan:
        """Produce an implementation plan for the given request."""


class FakeModelClient:
    """Deterministic client used by tests instead of a live model API."""

    def __init__(self, plan: ImplementationPlan | None = None) -> None:
        self.plan = plan or ImplementationPlan(
            findings=["Sample finding"],
            files_to_change=["booking/handler.py"],
            steps=["Inspect handler", "Add idempotency check"],
            risks=["Tests may still fail if store lookup is wrong"],
        )
        self.calls: list[PlanRequest] = []

    def create_plan(self, request: PlanRequest) -> ImplementationPlan:
        self.calls.append(request)
        return self.plan


class OpenAIModelClient:
    """Production client that requests a structured plan from OpenAI."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4.1-mini",
        client: OpenAI | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("api_key is required unless a client is provided")
        self._model = model
        self._client = client or OpenAI(api_key=api_key)

    def create_plan(self, request: PlanRequest) -> ImplementationPlan:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(request)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned an empty plan response")
        return ImplementationPlan.model_validate_json(content)


def _user_prompt(request: PlanRequest) -> str:
    context = request.repository_context.strip() or "(no repository context provided)"
    return (
        f"Task:\n{request.task_description.strip()}\n\n"
        f"Repository context:\n{context}\n"
    )
