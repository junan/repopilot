"""FastAPI application factory."""

from fastapi import FastAPI

from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved = settings or get_settings()
    app = FastAPI(title=resolved.app_name)
    app.state.settings = resolved

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": resolved.app_name,
            "environment": resolved.environment,
        }

    return app
