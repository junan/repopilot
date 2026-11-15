"""Repository tools and path safety helpers."""

from app.tools.errors import (
    AbsolutePathError,
    OversizedFileError,
    PathPolicyError,
    PathTraversalError,
    SecretPathError,
    SymlinkEscapeError,
)
from app.tools.path_policy import (
    DEFAULT_MAX_FILE_BYTES,
    is_secret_like_name,
    resolve_workspace_path,
)
from app.tools.repo_tools import list_files, read_file, search_text
from app.tools.types import (
    FileTreeEntry,
    FileTreeResult,
    ReadFileResult,
    SearchMatch,
    SearchResult,
)

__all__ = [
    "DEFAULT_MAX_FILE_BYTES",
    "AbsolutePathError",
    "FileTreeEntry",
    "FileTreeResult",
    "OversizedFileError",
    "PathPolicyError",
    "PathTraversalError",
    "ReadFileResult",
    "SearchMatch",
    "SearchResult",
    "SecretPathError",
    "SymlinkEscapeError",
    "is_secret_like_name",
    "list_files",
    "read_file",
    "resolve_workspace_path",
    "search_text",
]
