"""Request and response schemas for the task API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus

DESCRIPTION_MAX_LENGTH = 8000


class TaskCreate(BaseModel):
    """Body for creating an engineering task."""

    description: str = Field(min_length=1, max_length=DESCRIPTION_MAX_LENGTH)


class TaskResponse(BaseModel):
    """Serialized task returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    status: TaskStatus
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime
