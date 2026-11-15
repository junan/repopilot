"""Errors raised while enforcing repository path policy."""

from __future__ import annotations


class PathPolicyError(ValueError):
    """Base class for workspace path policy violations."""


class AbsolutePathError(PathPolicyError):
    """Raised when a path is absolute instead of workspace-relative."""


class PathTraversalError(PathPolicyError):
    """Raised when a path contains ``..`` or otherwise escapes the workspace."""


class SymlinkEscapeError(PathPolicyError):
    """Raised when a symlink resolves outside the workspace root."""


class SecretPathError(PathPolicyError):
    """Raised when a path looks like a secret or credential file."""


class OversizedFileError(PathPolicyError):
    """Raised when a file exceeds the configured size limit."""
