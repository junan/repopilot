"""HTTP routes for engineering tasks."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.deps import get_task_service
from app.schemas.errors import ErrorResponse
from app.schemas.tasks import TaskCreate, TaskResponse
from app.services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def create_task(
    body: TaskCreate,
    response: Response,
    service: Annotated[TaskService, Depends(get_task_service)],
    idempotency_key: Annotated[str | None, Header()] = None,
) -> TaskResponse:
    """Create a task, or replay a prior create for the same Idempotency-Key."""
    result = service.create(body.description, idempotency_key=idempotency_key)
    if result.created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
    return TaskResponse.model_validate(result.task)


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
) -> list[TaskResponse]:
    """List tasks newest-first."""
    return [TaskResponse.model_validate(task) for task in service.list()]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def get_task(
    task_id: uuid.UUID,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Retrieve a single task by id."""
    return TaskResponse.model_validate(service.get(task_id))
