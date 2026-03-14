# Test Spec: test_app.py

## Purpose
Tests for the FastAPI application factory and SPA fallback routing.

## Test Cases

### TestSPAFallback
- `test_api_path_returns_404` — Verifies unmatched `/api/` paths return 404 JSON instead of serving index.html (Fixes #10)
- `test_non_api_path_serves_spa` — Verifies non-API paths serve index.html via SPA fallback

## Notes
- The SPA fallback only registers when frontend/dist exists, so the fixture creates a temp dist dir
- Tests must work in CI where no real DB exists

## Changes
- 2026-03-14: Removed unused imports (AsyncMock, patch)
- 2026-03-14: Fixed CI failures — create temp frontend/dist and mock DB path
