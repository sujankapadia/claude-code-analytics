"""Tests for FastAPI application (app.py)."""

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with a frontend/dist so the SPA fallback registers."""
    import claude_code_analytics.api.app

    app_file = Path(claude_code_analytics.api.app.__file__)
    dist_dir = app_file.parent.parent.parent / "frontend" / "dist"

    # In CI, frontend/dist doesn't exist — create a minimal one
    created_dist = False
    if not dist_dir.is_dir():
        (dist_dir / "assets").mkdir(parents=True)
        (dist_dir / "index.html").write_text("<html><body>test</body></html>")
        created_dist = True

    try:
        from claude_code_analytics.api.app import create_app

        app = create_app()

        @asynccontextmanager
        async def _noop_lifespan(a: FastAPI):
            yield

        app.router.lifespan_context = _noop_lifespan
        yield TestClient(app)
    finally:
        if created_dist:
            shutil.rmtree(dist_dir, ignore_errors=True)


class TestSPAFallback:
    """Tests for the SPA catch-all route."""

    def test_api_path_returns_404(self, client):
        """Unmatched /api/ paths should return 404 JSON, not index.html."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "API endpoint not found: /api/nonexistent"

    def test_non_api_path_serves_spa(self, client):
        """Non-API paths should serve index.html via the SPA fallback."""
        response = client.get("/sessions/abc123")
        assert response.status_code == 200
        assert "<html" in response.text
