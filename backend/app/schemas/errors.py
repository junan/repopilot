"""Shared API error response schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Stable error payload returned by the HTTP API."""

    code: str = Field(..., description="Machine-stable error code")
    message: str = Field(..., description="Human-readable error message")
