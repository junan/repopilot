"""Unit tests for the planning model client and plan schema."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents import (
    FakeModelClient,
    ImplementationPlan,
    OpenAIModelClient,
    PlanRequest,
)


def test_plan_schema_ignores_extra_model_fields() -> None:
    plan = ImplementationPlan.model_validate(
        {
            "findings": ["Handler ignores idempotency keys"],
            "files_to_change": ["booking/handler.py"],
            "steps": ["Look up prior reservation by key"],
            "risks": ["Need regression coverage"],
            "confidence": 0.99,
            "raw_thoughts": "ignore me",
        }
    )

    assert plan.findings == ["Handler ignores idempotency keys"]
    assert plan.files_to_change == ["booking/handler.py"]
    assert not hasattr(plan, "confidence")
    assert plan.model_dump() == {
        "findings": ["Handler ignores idempotency keys"],
        "files_to_change": ["booking/handler.py"],
        "steps": ["Look up prior reservation by key"],
        "risks": ["Need regression coverage"],
    }


def test_fake_model_client_returns_configured_plan() -> None:
    expected = ImplementationPlan(
        findings=["Duplicate bookings on retry"],
        files_to_change=["booking/handler.py", "booking/store.py"],
        steps=["Add key lookup", "Return existing reservation"],
        risks=["Race conditions without locking"],
    )
    client = FakeModelClient(plan=expected)
    request = PlanRequest(
        task_description="Fix duplicate reservations on retry",
        repository_context="booking/handler.py accepts idempotency_key",
    )

    plan = client.create_plan(request)

    assert plan == expected
    assert client.calls == [request]


def test_openai_model_client_parses_structured_json_response() -> None:
    payload = (
        '{"findings":["Ignores key"],'
        '"files_to_change":["booking/handler.py"],'
        '"steps":["Reuse reservation"],'
        '"risks":["None"],'
        '"extra":"drop-me"}'
    )
    fake_openai = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
                )
            )
        )
    )
    client = OpenAIModelClient(api_key="test-key", client=fake_openai)  # type: ignore[arg-type]

    plan = client.create_plan(
        PlanRequest(task_description="Fix booking retries")
    )

    assert plan.findings == ["Ignores key"]
    assert plan.files_to_change == ["booking/handler.py"]
    assert plan.steps == ["Reuse reservation"]
    assert plan.risks == ["None"]


def test_openai_model_client_requires_api_key_without_injected_client() -> None:
    with pytest.raises(ValueError, match="api_key"):
        OpenAIModelClient(api_key="")
