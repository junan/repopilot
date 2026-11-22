"""Unit tests for typed tool registry validation and execution."""

from __future__ import annotations

import pytest

from app.tools import (
    InvalidToolArgumentsError,
    ToolRegistry,
    UnknownToolError,
)
from tests.support.sample_repo import BOOKING_SAMPLE_REPO


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry(BOOKING_SAMPLE_REPO)


def test_registry_exposes_step13_tools(registry: ToolRegistry) -> None:
    assert registry.names() == frozenset({"list_files", "read_file", "search_text"})


def test_unknown_tool_fails_before_execution(registry: ToolRegistry) -> None:
    with pytest.raises(UnknownToolError, match="shell"):
        registry.call("shell", {"command": "rm -rf /"})


def test_invalid_arguments_fail_before_execution(registry: ToolRegistry) -> None:
    with pytest.raises(InvalidToolArgumentsError):
        registry.call("read_file", {"relative_path": ""})

    with pytest.raises(InvalidToolArgumentsError):
        registry.call("list_files", {"max_depth": 0})

    with pytest.raises(InvalidToolArgumentsError):
        registry.call("search_text", {"query": "x", "unexpected": True})


def test_list_files_via_registry_finds_booking_handler(
    registry: ToolRegistry,
) -> None:
    outcome = registry.call("list_files", {})

    paths = {entry["path"] for entry in outcome.result["entries"]}
    assert "booking/handler.py" in paths
    assert "tests/test_booking.py" in paths


def test_read_file_via_registry(registry: ToolRegistry) -> None:
    outcome = registry.call(
        "read_file",
        {"relative_path": "booking/handler.py"},
    )

    assert "idempotency_key" in outcome.result["content"]
    assert outcome.arguments["relative_path"] == "booking/handler.py"


def test_search_text_via_registry(registry: ToolRegistry) -> None:
    outcome = registry.call("search_text", {"query": "idempotency_key"})

    paths = {match["path"] for match in outcome.result["matches"]}
    assert "booking/handler.py" in paths
    assert "tests/test_booking.py" in paths
