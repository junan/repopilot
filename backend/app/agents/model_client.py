"""Narrow model-client interface for structured planning calls."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol, runtime_checkable

from openai import OpenAI

from app.agents.plan import ImplementationPlan, PlanRequest, ToolCallRequest

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
    """Client that plans and may propose allowlisted tool calls."""

    def create_plan(self, request: PlanRequest) -> ImplementationPlan:
        """Produce an implementation plan for the given request."""

    def propose_tool_calls(self, request: PlanRequest) -> list[ToolCallRequest]:
        """Propose tool calls. Output is data only; permissions stay in-app."""

    def last_usage(self) -> tuple[int, int, Decimal]:
        """Return prompt tokens, completion tokens, and cost for the last call."""


class FakeModelClient:
    """Deterministic client used by tests instead of a live model API."""

    def __init__(
        self,
        plan: ImplementationPlan | None = None,
        *,
        final_plan: ImplementationPlan | None = None,
        tool_calls: list[ToolCallRequest] | None = None,
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
        cost_usd: Decimal = Decimal("0.001"),
    ) -> None:
        self.initial_plan = plan or ImplementationPlan(
            findings=["Sample finding"],
            files_to_change=["booking/handler.py"],
            steps=["Inspect handler", "Add idempotency check"],
            risks=["Tests may still fail if store lookup is wrong"],
        )
        self.final_plan = final_plan or self.initial_plan
        self.tool_calls = list(tool_calls or [])
        self.calls: list[PlanRequest] = []
        self._tool_calls_served = False
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self._cost_usd = cost_usd
        self._last_usage = (0, 0, Decimal("0"))

    def create_plan(self, request: PlanRequest) -> ImplementationPlan:
        self.calls.append(request)
        self._last_usage = (
            self._prompt_tokens,
            self._completion_tokens,
            self._cost_usd,
        )
        if len(self.calls) == 1:
            return self.initial_plan
        return self.final_plan

    def propose_tool_calls(self, request: PlanRequest) -> list[ToolCallRequest]:
        self._last_usage = (0, 0, Decimal("0"))
        if self._tool_calls_served:
            return []
        self._tool_calls_served = True
        return list(self.tool_calls)

    def last_usage(self) -> tuple[int, int, Decimal]:
        return self._last_usage


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
        self._last_usage = (0, 0, Decimal("0"))

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
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        self._last_usage = (prompt_tokens, completion_tokens, Decimal("0"))
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned an empty plan response")
        return ImplementationPlan.model_validate_json(content)

    def propose_tool_calls(self, request: PlanRequest) -> list[ToolCallRequest]:
        """OpenAI function-calling proposals arrive in a later iteration."""
        self._last_usage = (0, 0, Decimal("0"))
        return []

    def last_usage(self) -> tuple[int, int, Decimal]:
        return self._last_usage


def _user_prompt(request: PlanRequest) -> str:
    context = request.repository_context.strip() or "(no repository context provided)"
    return (
        f"Task:\n{request.task_description.strip()}\n\n"
        f"Repository context:\n{context}\n"
    )
