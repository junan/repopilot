"""Structured responses for repository inspection tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FileTreeEntry(BaseModel):
    """One node in a bounded workspace file tree."""

    path: str
    kind: Literal["file", "directory"]


class FileTreeResult(BaseModel):
    """Result of listing files under a workspace path."""

    entries: list[FileTreeEntry] = Field(default_factory=list)
    truncated: bool = False


class ReadFileResult(BaseModel):
    """Result of reading a single workspace file."""

    path: str
    content: str
    byte_count: int
    truncated: bool = False


class SearchMatch(BaseModel):
    """One text match inside a workspace file."""

    path: str
    line_number: int
    line: str


class SearchResult(BaseModel):
    """Result of a bounded workspace text search."""

    query: str
    matches: list[SearchMatch] = Field(default_factory=list)
    truncated: bool = False
