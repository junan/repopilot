"""Normalize and check allowlisted repository URLs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from urllib.parse import unquote, urlparse


def normalize_repo_url(url: str) -> str:
    """Return a canonical repository URL for allowlist comparison."""
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("repository URL must not be empty")

    if cleaned.startswith("file:"):
        return _normalize_file_url(cleaned)

    normalized = cleaned.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[: -len(".git")]
    return normalized


def is_allowlisted(repository_url: str, allowlist: Sequence[str]) -> bool:
    """Return whether ``repository_url`` matches an allowlisted entry."""
    target = normalize_repo_url(repository_url)
    allowed = {normalize_repo_url(entry) for entry in allowlist if entry.strip()}
    return target in allowed


def _normalize_file_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        raise ValueError(f"unsupported repository URL scheme: {parsed.scheme}")

    path = Path(unquote(parsed.path)).expanduser()
    # file://localhost/tmp/repo and file:///tmp/repo both appear with path /tmp/repo
    resolved = path.resolve()
    return resolved.as_uri()
