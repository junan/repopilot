"""Authorized repository access helpers."""

from app.repositories.allowlist import is_allowlisted, normalize_repo_url
from app.repositories.clone import CloneResult, clone_repository
from app.repositories.errors import (
    InvalidCommitPinError,
    RepositoryCloneError,
    RepositoryError,
    RepositoryNotAllowlistedError,
)

__all__ = [
    "CloneResult",
    "InvalidCommitPinError",
    "RepositoryCloneError",
    "RepositoryError",
    "RepositoryNotAllowlistedError",
    "clone_repository",
    "is_allowlisted",
    "normalize_repo_url",
]
