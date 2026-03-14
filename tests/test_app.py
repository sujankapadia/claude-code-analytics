"""Tests for FastAPI application (app.py)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked lifespan (no file watcher)."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from claude_code_analytics.api.app import create_app

    app = create_app()

    # Override lifespan to no-op for testing
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    app.router.lifespan_context = _noop_lifespan

    return TestClient(app)


class TestSPAFallback:
    """Tests for the SPA catch-all route."""

    def test_api_path_returns_404(self, client):
        """Unmatched /api/ paths should return 404 JSON, not index.html."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "API endpoint not found: /api/nonexistent"

    def test_registered_api_route_still_works(self, client):
        """Registered API routes should still work normally."""
        response = client.get("/api/projects")
        # Should return 200 (or another valid status), not 404
        assert response.status_code != 404 or "API endpoint not found" not in response.text

    def test_non_api_path_serves_spa(self, client):
        """Non-API paths should not be caught by the API guard."""
        response = client.get("/sessions/abc123")
        # The important thing is it does NOT match as an API route
        assert "API endpoint not found" not in response.text
