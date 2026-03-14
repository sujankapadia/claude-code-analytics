# Test Spec: test_app.py

## Purpose
Tests for the FastAPI application factory and SPA fallback routing.

## Test Cases

### TestSPAFallback
- `test_api_path_returns_404` — Verifies unmatched `/api/` paths return 404 JSON instead of serving index.html (Fixes #10)
- `test_registered_api_route_still_works` — Verifies registered API routes are not affected by the fallback guard
- `test_non_api_path_serves_spa` — Verifies non-API paths are not incorrectly caught by the API guard

## Changes
- 2026-03-14: Removed unused imports (AsyncMock, patch)
