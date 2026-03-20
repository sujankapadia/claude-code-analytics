"""Tests for analysis router security features (SSRF validation, localhost restriction)."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

from claude_code_analytics.api.routers.analysis import router, validate_base_url

# ---------------------------------------------------------------------------
# Unit tests for validate_base_url
# ---------------------------------------------------------------------------


class TestValidateBaseUrl:
    """SSRF validation for user-supplied base_url values."""

    def test_accepts_ollama_localhost(self):
        result = validate_base_url("http://localhost:11434/v1")
        assert result == "http://localhost:11434/v1"

    def test_accepts_lm_studio_localhost(self):
        result = validate_base_url("http://localhost:1234/v1")
        assert result == "http://localhost:1234/v1"

    def test_accepts_vllm_localhost(self):
        result = validate_base_url("http://localhost:8001/v1")
        assert result == "http://localhost:8001/v1"

    def test_accepts_openrouter(self):
        result = validate_base_url("https://openrouter.ai/api/v1")
        assert result == "https://openrouter.ai/api/v1"

    def test_rejects_file_scheme(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("file:///etc/passwd")
        assert exc_info.value.status_code == 422
        assert "scheme" in exc_info.value.detail.lower()

    def test_rejects_ftp_scheme(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("ftp://example.com/data")
        assert exc_info.value.status_code == 422
        assert "scheme" in exc_info.value.detail.lower()

    def test_rejects_cloud_metadata_ip(self):
        """169.254.169.254 is a link-local address used by cloud metadata services."""
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("http://169.254.169.254/latest/meta-data")
        assert exc_info.value.status_code == 422
        assert "private" in exc_info.value.detail.lower() or "link" in exc_info.value.detail.lower()

    def test_rejects_no_hostname(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("http:///path/only")
        assert exc_info.value.status_code == 422
        assert "hostname" in exc_info.value.detail.lower()

    def test_rejects_private_ip_10(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("http://10.0.0.1/v1")
        assert exc_info.value.status_code == 422
        assert "private" in exc_info.value.detail.lower()

    def test_rejects_private_ip_192_168(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("http://192.168.1.1/v1")
        assert exc_info.value.status_code == 422
        assert "private" in exc_info.value.detail.lower()

    def test_rejects_localhost_on_disallowed_port(self):
        """Localhost is only allowed on known local-provider ports."""
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("http://localhost:9999/v1")
        assert exc_info.value.status_code == 422
        assert "loopback" in exc_info.value.detail.lower()

    def test_rejects_localhost_default_port(self):
        """http://localhost/ uses port 80, which is not in the allowed set."""
        with pytest.raises(HTTPException) as exc_info:
            validate_base_url("http://localhost/")
        assert exc_info.value.status_code == 422
        assert "loopback" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Integration tests for /api/analysis/publish localhost restriction
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with just the analysis router."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


def _wrap_with_client_ip(app: ASGIApp, host: str) -> ASGIApp:
    """Wrap an ASGI app to inject a specific client IP into every HTTP request."""

    async def wrapper(scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            scope["client"] = (host, 12345)
        await app(scope, receive, send)

    return wrapper


class TestPublishLocalhostRestriction:
    """The /api/analysis/publish endpoint must reject non-localhost callers."""

    def test_publish_rejects_non_localhost(self):
        """A request from a non-loopback IP should get 403."""
        app = _make_app()
        remote_app = _wrap_with_client_ip(app, "203.0.113.1")
        client = TestClient(remote_app)

        response = client.post(
            "/api/analysis/publish",
            json={
                "analysis_content": "test content",
                "description": "test",
            },
        )
        assert response.status_code == 403
        assert "localhost" in response.json()["detail"].lower()

    def test_publish_allows_localhost(self):
        """A request from 127.0.0.1 should NOT get 403 (may fail for other reasons)."""
        app = _make_app()
        local_app = _wrap_with_client_ip(app, "127.0.0.1")
        client = TestClient(local_app)

        # Patch GITHUB_TOKEN to None so we get a 400 instead of actual publishing
        with patch("claude_code_analytics.config.GITHUB_TOKEN", None):
            response = client.post(
                "/api/analysis/publish",
                json={
                    "analysis_content": "test content",
                    "description": "test",
                },
            )
            assert response.status_code != 403
            assert response.status_code == 400
            assert "GITHUB_TOKEN" in response.json()["detail"]

    def test_publish_allows_ipv6_localhost(self):
        """A request from ::1 should also be allowed."""
        app = _make_app()
        local_app = _wrap_with_client_ip(app, "::1")
        client = TestClient(local_app)

        with patch("claude_code_analytics.config.GITHUB_TOKEN", None):
            response = client.post(
                "/api/analysis/publish",
                json={
                    "analysis_content": "test content",
                    "description": "test",
                },
            )
            assert response.status_code != 403
            assert response.status_code == 400
