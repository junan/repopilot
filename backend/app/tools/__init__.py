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
from app.tools.registry import (
    DEFAULT_MAX_RESULT_CHARS,
    InvalidToolArgumentsError,
    ToolCallResult,
    ToolRegistry,
    ToolRegistryError,
    UnknownToolError,
)
from app.tools.repo_tools import list_files, read_file, search_text
from app.tools.schemas import ListFilesArgs, ReadFileArgs, SearchTextArgs
from app.tools.types import (
    FileTreeEntry,
    FileTreeResult,
    ReadFileResult,
    SearchMatch,
    SearchResult,
)

__all__ = [
    "DEFAULT_MAX_FILE_BYTES",
    "DEFAULT_MAX_RESULT_CHARS",
    "AbsolutePathError",
    "FileTreeEntry",
    "FileTreeResult",
    "InvalidToolArgumentsError",
    "ListFilesArgs",
    "OversizedFileError",
    "PathPolicyError",
    "PathTraversalError",
    "ReadFileArgs",
    "ReadFileResult",
    "SearchMatch",
    "SearchResult",
    "SearchTextArgs",
    "SecretPathError",
    "SymlinkEscapeError",
    "ToolCallResult",
    "ToolRegistry",
    "ToolRegistryError",
    "UnknownToolError",
    "is_secret_like_name",
    "list_files",
    "read_file",
    "resolve_workspace_path",
    "search_text",
]
