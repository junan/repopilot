"""Bounded repository list, read, and search tools."""

from __future__ import annotations

from pathlib import Path

from app.tools.errors import PathPolicyError
from app.tools.path_policy import (
    DEFAULT_MAX_FILE_BYTES,
    is_secret_like_name,
    resolve_workspace_path,
)
from app.tools.types import (
    FileTreeEntry,
    FileTreeResult,
    ReadFileResult,
    SearchMatch,
    SearchResult,
)

DEFAULT_MAX_DEPTH = 8
DEFAULT_MAX_ENTRIES = 200
DEFAULT_MAX_READ_BYTES = 100_000
DEFAULT_MAX_MATCHES = 50

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
    }
)


def list_files(
    workspace_root: Path,
    relative_path: str = ".",
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> FileTreeResult:
    """Return a bounded file tree under ``relative_path``."""
    _validate_positive(max_depth=max_depth, max_entries=max_entries)
    root = workspace_root.resolve()
    start = _resolve_existing_dir(root, relative_path)

    entries: list[FileTreeEntry] = []

    for directory, dir_depth in _walk_directories(start, root, max_depth):
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name.lower())
        except OSError:
            continue

        for child in children:
            if len(entries) >= max_entries:
                return FileTreeResult(entries=entries, truncated=True)

            name = child.name
            if name in _SKIP_DIR_NAMES or is_secret_like_name(name):
                continue

            rel = _relative_posix(child, root)
            if child.is_symlink():
                continue
            if child.is_dir():
                if dir_depth >= max_depth:
                    continue
                entries.append(FileTreeEntry(path=rel, kind="directory"))
            elif child.is_file():
                entries.append(FileTreeEntry(path=rel, kind="file"))

    return FileTreeResult(entries=entries, truncated=False)


def read_file(
    workspace_root: Path,
    relative_path: str,
    *,
    max_bytes: int = DEFAULT_MAX_READ_BYTES,
) -> ReadFileResult:
    """Read a workspace file with a returned-content byte cap."""
    _validate_positive(max_bytes=max_bytes)
    root = workspace_root.resolve()
    resolved = resolve_workspace_path(
        root,
        relative_path,
        max_file_bytes=DEFAULT_MAX_FILE_BYTES,
    )
    if not resolved.is_file():
        raise PathPolicyError(f"not a file: {relative_path}")

    data = resolved.read_bytes()
    truncated = len(data) > max_bytes
    chunk = data[:max_bytes]
    content = chunk.decode("utf-8", errors="replace")
    return ReadFileResult(
        path=_relative_posix(resolved, root),
        content=content,
        byte_count=len(chunk),
        truncated=truncated,
    )


def search_text(
    workspace_root: Path,
    query: str,
    *,
    relative_path: str = ".",
    max_matches: int = DEFAULT_MAX_MATCHES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> SearchResult:
    """Search workspace text files for ``query`` with hard match and depth caps."""
    if not query:
        raise PathPolicyError("search query must not be empty")
    _validate_positive(
        max_matches=max_matches,
        max_depth=max_depth,
        max_file_bytes=max_file_bytes,
    )

    root = workspace_root.resolve()
    start = _resolve_existing_dir(root, relative_path)
    matches: list[SearchMatch] = []

    for directory, _dir_depth in _walk_directories(start, root, max_depth):
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name.lower())
        except OSError:
            continue

        for child in children:
            if len(matches) >= max_matches:
                return SearchResult(query=query, matches=matches, truncated=True)

            name = child.name
            if name in _SKIP_DIR_NAMES or is_secret_like_name(name):
                continue
            if child.is_symlink() or not child.is_file():
                continue
            if child.stat().st_size > max_file_bytes:
                continue

            rel = _relative_posix(child, root)
            try:
                text = child.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "\x00" in text:
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                if query not in line:
                    continue
                matches.append(
                    SearchMatch(path=rel, line_number=line_number, line=line.rstrip())
                )
                if len(matches) >= max_matches:
                    return SearchResult(
                        query=query,
                        matches=matches,
                        truncated=True,
                    )

    return SearchResult(query=query, matches=matches, truncated=False)


def _resolve_existing_dir(workspace_root: Path, relative_path: str) -> Path:
    if relative_path in ("", "."):
        if not workspace_root.is_dir():
            raise PathPolicyError(
                f"workspace root is not a directory: {workspace_root}"
            )
        return workspace_root

    resolved = resolve_workspace_path(workspace_root, relative_path)
    if not resolved.is_dir():
        raise PathPolicyError(f"not a directory: {relative_path}")
    return resolved


def _walk_directories(
    start: Path,
    workspace_root: Path,
    max_depth: int,
) -> list[tuple[Path, int]]:
    """Breadth-first directories under start, with depth relative to start."""
    queue: list[tuple[Path, int]] = [(start, 0)]
    seen: list[tuple[Path, int]] = []
    index = 0
    while index < len(queue):
        directory, depth = queue[index]
        index += 1
        seen.append((directory, depth))
        if depth >= max_depth:
            continue
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name.lower())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or child.is_symlink():
                continue
            if child.name in _SKIP_DIR_NAMES or is_secret_like_name(child.name):
                continue
            if not child.resolve().is_relative_to(workspace_root):
                continue
            queue.append((child, depth + 1))
    return seen


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _validate_positive(**limits: int) -> None:
    for name, value in limits.items():
        if value < 1:
            raise ValueError(f"{name} must be >= 1")
