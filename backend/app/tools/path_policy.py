"""Resolve and validate paths inside a repository workspace."""

from __future__ import annotations

from pathlib import Path

from app.tools.errors import (
    AbsolutePathError,
    OversizedFileError,
    PathPolicyError,
    PathTraversalError,
    SecretPathError,
    SymlinkEscapeError,
)

DEFAULT_MAX_FILE_BYTES = 1_000_000

_SECRET_BASENAMES = frozenset(
    {
        ".env",
        ".npmrc",
        ".pypirc",
        "credentials.json",
        "id_ed25519",
        "id_rsa",
        "service_account.json",
    }
)
_SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


def is_secret_like_name(name: str) -> bool:
    """Return whether a path component looks like a secret filename."""
    lowered = name.lower()
    if lowered in _SECRET_BASENAMES or lowered.startswith(".env."):
        return True
    return lowered.endswith(_SECRET_SUFFIXES)


def resolve_workspace_path(
    workspace_root: Path,
    relative_path: str,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> Path:
    """Resolve ``relative_path`` under ``workspace_root`` or raise a policy error.

    Rejects absolute paths, ``..`` segments, symlink escapes, secret-like names,
    and existing files larger than ``max_file_bytes``.
    """
    if max_file_bytes < 1:
        raise ValueError("max_file_bytes must be >= 1")

    if relative_path is None or not str(relative_path).strip():
        raise PathPolicyError("path must not be empty")
    if "\x00" in relative_path:
        raise PathPolicyError("path must not contain null bytes")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise AbsolutePathError(f"absolute paths are not allowed: {relative_path}")

    if any(part == ".." for part in candidate.parts):
        raise PathTraversalError(f"path traversal is not allowed: {relative_path}")

    for part in candidate.parts:
        if part in ("", "."):
            continue
        if is_secret_like_name(part):
            raise SecretPathError(f"secret-like path is not allowed: {relative_path}")

    root = workspace_root.resolve()
    if not root.exists() or not root.is_dir():
        raise PathPolicyError(f"workspace root is not a directory: {workspace_root}")

    resolved = root.joinpath(candidate).resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise SymlinkEscapeError(
            f"path resolves outside workspace: {relative_path}"
        )

    if resolved.exists() and resolved.is_file():
        size = resolved.stat().st_size
        if size > max_file_bytes:
            raise OversizedFileError(
                f"file exceeds size limit ({size} > {max_file_bytes} bytes): "
                f"{relative_path}"
            )

    return resolved
