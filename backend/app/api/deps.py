"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import session_scope
from app.services.tasks import TaskService


def get_db(request: Request) -> Generator[Session]:
    """Open a transactional session for the current request."""
    session_factory = request.app.state.session_factory
    with session_scope(session_factory) as session:
        yield session


def get_task_service(
    session: Annotated[Session, Depends(get_db)],
) -> TaskService:
    """Build a TaskService bound to the request session."""
    return TaskService(session)
