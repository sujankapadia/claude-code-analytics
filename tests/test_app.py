"""Tests for FastAPI application (app.py)."""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with a frontend/dist so the SPA fallback registers.

    Patches file_watcher.start/stop to avoid real filesystem watching and
    catch-up imports, while keeping the real lifespan logic exercised.
    """
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
        with (
            patch.object(
                claude_code_analytics.api.app.file_watcher, "start", new_callable=AsyncMock
            ),
            patch.object(
                claude_code_analytics.api.app.file_watcher, "stop", new_callable=AsyncMock
            ),
        ):
            from claude_code_analytics.api.app import create_app

            app = create_app()
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
        assert "<body>" in response.text

    def test_real_api_route_resolves(self):
        """Real API routes should still resolve when the SPA catch-all is registered."""
        import claude_code_analytics.api.app
        from claude_code_analytics.api.dependencies import get_db_service

        app_file = Path(claude_code_analytics.api.app.__file__)
        dist_dir = app_file.parent.parent.parent / "frontend" / "dist"

        created_dist = False
        if not dist_dir.is_dir():
            (dist_dir / "assets").mkdir(parents=True)
            (dist_dir / "index.html").write_text("<html><body>test</body></html>")
            created_dist = True

        try:
            with (
                patch.object(
                    claude_code_analytics.api.app.file_watcher, "start", new_callable=AsyncMock
                ),
                patch.object(
                    claude_code_analytics.api.app.file_watcher, "stop", new_callable=AsyncMock
                ),
            ):
                from claude_code_analytics.api.app import create_app

                app = create_app()

                # Override DB dependency with a mock that returns empty results
                mock_db = MagicMock()
                mock_db.get_project_summaries.return_value = []
                app.dependency_overrides[get_db_service] = lambda: mock_db

                with TestClient(app) as c:
                    response = c.get("/api/projects")
                    assert response.status_code == 200
                    assert response.json() == []
        finally:
            if created_dist:
                shutil.rmtree(dist_dir, ignore_errors=True)
