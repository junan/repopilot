"""FastAPI application factory."""

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.tasks import router as tasks_router
from app.core.config import Settings, get_settings
from app.db.session import create_engine_from_settings, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved = settings or get_settings()
    app = FastAPI(title=resolved.app_name)
    app.state.settings = resolved

    engine = create_engine_from_settings(resolved)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    register_exception_handlers(app)
    app.include_router(tasks_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": resolved.app_name,
            "environment": resolved.environment,
        }

    return app
