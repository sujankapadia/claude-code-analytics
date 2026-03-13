"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from claude_code_analytics.api.services.event_bus import EventBus
from claude_code_analytics.api.services.file_watcher import FileWatcher

logger = logging.getLogger(__name__)

# Module-level singletons accessible to routers
event_bus = EventBus()
file_watcher = FileWatcher(event_bus)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown: file watcher lifecycle."""
    await file_watcher.start()
    logger.info("File watcher started")
    yield
    await file_watcher.stop()
    logger.info("File watcher stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Claude Code Analytics API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for local React dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from claude_code_analytics.api.routers import (
        analysis,
        analytics,
        events,
        examples,
        import_data,
        projects,
        search,
        sessions,
    )

    app.include_router(projects.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(examples.router, prefix="/api")
    app.include_router(import_data.router, prefix="/api")
    app.include_router(events.router, prefix="/api")

    # Serve frontend static files if built
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
