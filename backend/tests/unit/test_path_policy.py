"""Unit tests for workspace path policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.tools import (
    AbsolutePathError,
    OversizedFileError,
    PathPolicyError,
    PathTraversalError,
    SecretPathError,
    SymlinkEscapeError,
    resolve_workspace_path,
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "booking").mkdir()
    (root / "booking" / "handler.py").write_text("print('ok')\n", encoding="utf-8")
    return root


def test_resolve_allows_relative_file_inside_workspace(workspace: Path) -> None:
    resolved = resolve_workspace_path(workspace, "booking/handler.py")

    assert resolved == (workspace / "booking" / "handler.py").resolve()
    assert resolved.is_file()


def test_reject_absolute_path(workspace: Path) -> None:
    absolute = str((workspace / "booking" / "handler.py").resolve())

    with pytest.raises(AbsolutePathError):
        resolve_workspace_path(workspace, absolute)


def test_reject_parent_directory_segments(workspace: Path) -> None:
    with pytest.raises(PathTraversalError):
        resolve_workspace_path(workspace, "../outside.txt")

    with pytest.raises(PathTraversalError):
        resolve_workspace_path(workspace, "booking/../../outside.txt")


def test_reject_symlink_escape(workspace: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("leak", encoding="utf-8")
    escape_link = workspace / "escape.txt"
    escape_link.symlink_to(outside)

    with pytest.raises(SymlinkEscapeError):
        resolve_workspace_path(workspace, "escape.txt")


def test_allow_symlink_that_stays_inside_workspace(workspace: Path) -> None:
    target = workspace / "booking" / "handler.py"
    link = workspace / "handler-link.py"
    link.symlink_to(target)

    resolved = resolve_workspace_path(workspace, "handler-link.py")

    assert resolved == target.resolve()


@pytest.mark.parametrize(
    "relative_path",
    [
        ".env",
        "config/.env.local",
        "credentials.json",
        "certs/server.pem",
        "keys/id_rsa",
        "auth/service_account.json",
    ],
)
def test_reject_secret_like_filenames(workspace: Path, relative_path: str) -> None:
    path = workspace.joinpath(*Path(relative_path).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("secret", encoding="utf-8")

    with pytest.raises(SecretPathError):
        resolve_workspace_path(workspace, relative_path)


def test_reject_oversized_file(workspace: Path) -> None:
    big = workspace / "big.txt"
    big.write_bytes(b"x" * 128)

    with pytest.raises(OversizedFileError):
        resolve_workspace_path(workspace, "big.txt", max_file_bytes=64)


def test_reject_empty_path(workspace: Path) -> None:
    with pytest.raises(PathPolicyError):
        resolve_workspace_path(workspace, "   ")
