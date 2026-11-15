"""Errors for authorized repository cloning."""

from __future__ import annotations


class RepositoryError(Exception):
    """Base class for repository authorization and clone failures."""


class RepositoryNotAllowlistedError(RepositoryError):
    """Raised when a repository URL is not on the allowlist."""

    def __init__(self, repository_url: str) -> None:
        self.repository_url = repository_url
        super().__init__(f"Repository URL is not allowlisted: {repository_url}")


class InvalidCommitPinError(RepositoryError):
    """Raised when the pinned commit is not a full SHA."""

    def __init__(self, commit_sha: str) -> None:
        self.commit_sha = commit_sha
        super().__init__(f"Commit pin must be a 40-character SHA: {commit_sha}")


class RepositoryCloneError(RepositoryError):
    """Raised when git clone or checkout fails."""
