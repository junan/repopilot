"""Pydantic argument schemas for registered repository tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.tools.path_policy import DEFAULT_MAX_FILE_BYTES
from app.tools.repo_tools import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_MATCHES,
    DEFAULT_MAX_READ_BYTES,
)


class ListFilesArgs(BaseModel):
    """Arguments for the list_files tool."""

    model_config = ConfigDict(extra="forbid")

    relative_path: str = "."
    max_depth: int = Field(default=DEFAULT_MAX_DEPTH, ge=1, le=32)
    max_entries: int = Field(default=DEFAULT_MAX_ENTRIES, ge=1, le=2000)


class ReadFileArgs(BaseModel):
    """Arguments for the read_file tool."""

    model_config = ConfigDict(extra="forbid")

    relative_path: str = Field(min_length=1)
    max_bytes: int = Field(
        default=DEFAULT_MAX_READ_BYTES,
        ge=1,
        le=DEFAULT_MAX_FILE_BYTES,
    )


class SearchTextArgs(BaseModel):
    """Arguments for the search_text tool."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    relative_path: str = "."
    max_matches: int = Field(default=DEFAULT_MAX_MATCHES, ge=1, le=500)
    max_depth: int = Field(default=DEFAULT_MAX_DEPTH, ge=1, le=32)
    max_file_bytes: int = Field(default=DEFAULT_MAX_FILE_BYTES, ge=1, le=5_000_000)
