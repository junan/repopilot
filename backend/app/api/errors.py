"""HTTP exception handlers with a stable error JSON shape."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.errors import ErrorResponse
from app.services.errors import IdempotencyConflictError, TaskNotFoundError


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Attach domain and validation error handlers to the app."""

    @app.exception_handler(TaskNotFoundError)
    async def task_not_found_handler(
        _request: Request,
        exc: TaskNotFoundError,
    ) -> JSONResponse:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "task_not_found",
            str(exc),
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        _request: Request,
        exc: IdempotencyConflictError,
    ) -> JSONResponse:
        return _error_response(
            status.HTTP_409_CONFLICT,
            "idempotency_conflict",
            str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        message = _validation_message(exc)
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            message,
        )


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Request validation failed"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    detail = first.get("msg", "Invalid value")
    if location:
        return f"{location}: {detail}"
    return str(detail)
