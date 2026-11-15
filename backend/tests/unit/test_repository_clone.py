"""Unit tests for allowlisted repository cloning using the booking fixture."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from app.repositories import (
    InvalidCommitPinError,
    RepositoryCloneError,
    RepositoryNotAllowlistedError,
    clone_repository,
    is_allowlisted,
    normalize_repo_url,
)
from tests.support.sample_repo import BOOKING_SAMPLE_REPO


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def local_git_repo(tmp_path: Path) -> tuple[str, str, Path]:
    """Copy the booking sample into a local git repo and return url, sha, path."""
    source = BOOKING_SAMPLE_REPO
    repo_path = tmp_path / "booking-origin"
    shutil.copytree(
        source,
        repo_path,
        ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__"),
    )

    _git(repo_path, "init", "-b", "main")
    _git(repo_path, "config", "user.email", "repopilot-tests@example.com")
    _git(repo_path, "config", "user.name", "RepoPilot Tests")
    _git(repo_path, "add", ".")
    _git(repo_path, "commit", "-m", "initial booking sample")
    sha = _git(repo_path, "rev-parse", "HEAD")
    return repo_path.resolve().as_uri(), sha, repo_path


def test_normalize_file_url_is_stable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    uri = repo.resolve().as_uri()

    assert normalize_repo_url(uri) == uri
    assert normalize_repo_url(uri + "/") == uri


def test_is_allowlisted_requires_exact_normalized_match(tmp_path: Path) -> None:
    allowed = (tmp_path / "allowed").resolve().as_uri()
    other = (tmp_path / "other").resolve().as_uri()

    assert is_allowlisted(allowed, [allowed])
    assert not is_allowlisted(other, [allowed])


def test_clone_allowlisted_local_repo_at_pinned_commit(
    local_git_repo: tuple[str, str, Path],
    tmp_path: Path,
) -> None:
    repo_url, sha, _origin = local_git_repo
    workspace_root = tmp_path / "workspaces"
    task_id = uuid.uuid4()

    result = clone_repository(
        repository_url=repo_url,
        commit_sha=sha,
        workspace_root=workspace_root,
        task_id=task_id,
        allowlist=[repo_url],
    )

    assert result.commit_sha == sha
    assert result.workspace_path == workspace_root / str(task_id) / "repo"
    assert (result.workspace_path / "booking" / "handler.py").is_file()
    assert (result.workspace_path / "tests" / "test_booking.py").is_file()
    assert _git(result.workspace_path, "rev-parse", "HEAD") == sha


def test_refuse_repository_not_on_allowlist(
    local_git_repo: tuple[str, str, Path],
    tmp_path: Path,
) -> None:
    repo_url, sha, _origin = local_git_repo

    with pytest.raises(RepositoryNotAllowlistedError):
        clone_repository(
            repository_url=repo_url,
            commit_sha=sha,
            workspace_root=tmp_path / "workspaces",
            task_id=uuid.uuid4(),
            allowlist=["file:///tmp/not-the-booking-sample"],
        )


def test_refuse_short_commit_pin(
    local_git_repo: tuple[str, str, Path],
    tmp_path: Path,
) -> None:
    repo_url, sha, _origin = local_git_repo

    with pytest.raises(InvalidCommitPinError):
        clone_repository(
            repository_url=repo_url,
            commit_sha=sha[:12],
            workspace_root=tmp_path / "workspaces",
            task_id=uuid.uuid4(),
            allowlist=[repo_url],
        )


def test_unknown_commit_raises_clone_error(
    local_git_repo: tuple[str, str, Path],
    tmp_path: Path,
) -> None:
    repo_url, _sha, _origin = local_git_repo
    missing = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    with pytest.raises(RepositoryCloneError):
        clone_repository(
            repository_url=repo_url,
            commit_sha=missing,
            workspace_root=tmp_path / "workspaces",
            task_id=uuid.uuid4(),
            allowlist=[repo_url],
        )
