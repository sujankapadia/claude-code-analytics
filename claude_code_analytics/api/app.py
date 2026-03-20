"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
        active,
        analysis,
        analytics,
        bookmarks,
        events,
        import_data,
        projects,
        search,
        sessions,
        similar,
    )

    app.include_router(projects.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(import_data.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    app.include_router(active.router, prefix="/api")
    app.include_router(bookmarks.router, prefix="/api")
    app.include_router(similar.router, prefix="/api")

    # Serve frontend static files if built.
    # In development, the dist lives at <project-root>/frontend/dist.
    # In a pip-installed package, a pre-build step copies it to
    # claude_code_analytics/static/dist so it ships as package-data.
    frontend_dist = Path(__file__).parent.parent / "static" / "dist"
    if not frontend_dist.is_dir():
        # Fallback: development layout (repo root)
        frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        # Serve static assets (JS, CSS, fonts, etc.)
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        # SPA catch-all: serve index.html for any non-API route
        @app.get("/{full_path:path}")
        async def spa_fallback(request: Request, full_path: str):
            # Return 404 for unmatched API paths instead of serving the SPA
            if full_path.startswith("api/"):
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"API endpoint not found: /{full_path}"},
                )
            # Serve actual files if they exist (e.g., favicon.ico)
            if full_path:
                frontend_root = frontend_dist.resolve()
                file_path = (frontend_root / full_path).resolve()
                # Reject path traversal attempts (e.g., ../../etc/passwd)
                if not file_path.is_relative_to(frontend_root):
                    return JSONResponse(status_code=404, content={"detail": "Not found"})
                if file_path.is_file():
                    return FileResponse(file_path)
            return FileResponse(frontend_dist / "index.html")

    return app
