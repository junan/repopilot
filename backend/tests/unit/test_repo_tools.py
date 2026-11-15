"""Unit tests for bounded repository list, read, and search tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.tools import (
    AbsolutePathError,
    PathTraversalError,
    list_files,
    read_file,
    search_text,
)
from tests.support.sample_repo import BOOKING_SAMPLE_REPO


@pytest.fixture
def workspace() -> Path:
    return BOOKING_SAMPLE_REPO


def test_list_files_finds_booking_handler_and_tests(workspace: Path) -> None:
    result = list_files(workspace)

    paths = {entry.path for entry in result.entries}
    assert "booking/handler.py" in paths
    assert "booking/store.py" in paths
    assert "tests/test_booking.py" in paths
    assert result.truncated is False


def test_read_file_returns_booking_handler(workspace: Path) -> None:
    result = read_file(workspace, "booking/handler.py")

    assert result.path == "booking/handler.py"
    assert "create_reservation" in result.content
    assert "idempotency_key" in result.content
    assert result.truncated is False


def test_search_text_finds_handler_and_regression_test(workspace: Path) -> None:
    result = search_text(workspace, "idempotency_key")

    paths = {match.path for match in result.matches}
    assert "booking/handler.py" in paths
    assert "tests/test_booking.py" in paths
    assert any(
        "test_retry_with_same_idempotency_key_does_not_duplicate" in match.line
        or "idempotency_key" in match.line
        for match in result.matches
    )


def test_read_rejects_path_traversal(workspace: Path) -> None:
    with pytest.raises(PathTraversalError):
        read_file(workspace, "../README.md")


def test_list_rejects_absolute_path(workspace: Path) -> None:
    with pytest.raises(AbsolutePathError):
        list_files(workspace, str(workspace / "booking"))


def test_search_rejects_path_traversal(workspace: Path) -> None:
    with pytest.raises(PathTraversalError):
        search_text(workspace, "BookingService", relative_path="../")


def test_list_respects_max_entries(workspace: Path) -> None:
    result = list_files(workspace, max_entries=2)

    assert len(result.entries) == 2
    assert result.truncated is True


def test_read_truncates_to_max_bytes(workspace: Path, tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "note.txt").write_text("abcdef", encoding="utf-8")

    result = read_file(root, "note.txt", max_bytes=3)

    assert result.content == "abc"
    assert result.byte_count == 3
    assert result.truncated is True


def test_search_respects_max_matches(workspace: Path) -> None:
    result = search_text(workspace, "reservation", max_matches=1)

    assert len(result.matches) == 1
    assert result.truncated is True
