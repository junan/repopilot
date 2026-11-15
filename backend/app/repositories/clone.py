"""Clone allowlisted repositories at a pinned commit."""

from __future__ import annotations

import re
import shutil
import subprocess
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.repositories.allowlist import is_allowlisted, normalize_repo_url
from app.repositories.errors import (
    InvalidCommitPinError,
    RepositoryCloneError,
    RepositoryNotAllowlistedError,
)

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_GIT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class CloneResult:
    """Filesystem location of a cloned, pin-checked workspace."""

    repository_url: str
    commit_sha: str
    workspace_path: Path


def clone_repository(
    *,
    repository_url: str,
    commit_sha: str,
    workspace_root: Path,
    task_id: uuid.UUID | str,
    allowlist: Sequence[str],
) -> CloneResult:
    """Clone an allowlisted repository into a per-task workspace at ``commit_sha``."""
    if not _FULL_SHA.fullmatch(commit_sha):
        raise InvalidCommitPinError(commit_sha)

    normalized_url = normalize_repo_url(repository_url)
    if not is_allowlisted(normalized_url, allowlist):
        raise RepositoryNotAllowlistedError(normalized_url)

    destination = workspace_root / str(task_id) / "repo"
    if destination.exists():
        raise RepositoryCloneError(f"workspace already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        _run_git(["clone", "--", normalized_url, str(destination)])
        _run_git(["-C", str(destination), "checkout", "--force", commit_sha])
        head = _run_git(
            ["-C", str(destination), "rev-parse", "HEAD"]
        ).stdout.strip()
    except RepositoryCloneError:
        _cleanup(destination)
        raise

    if head != commit_sha:
        _cleanup(destination)
        raise RepositoryCloneError(
            f"checked out commit {head!r} does not match pin {commit_sha!r}"
        )

    return CloneResult(
        repository_url=normalized_url,
        commit_sha=commit_sha,
        workspace_path=destination,
    )


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise RepositoryCloneError("git executable not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepositoryCloneError(f"git timed out: {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        message = f"git {' '.join(args)} failed"
        if detail:
            message = f"{message}: {detail}"
        raise RepositoryCloneError(message) from exc


def _cleanup(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
