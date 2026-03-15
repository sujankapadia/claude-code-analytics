# Test Spec: test_import_service.py

## Purpose
Tests for the import service, focusing on SQLite thread safety (Fixes #13).

## Test Cases

### TestImportServiceThreadSafety
- `test_import_single_session_creates_own_connection` — Verifies `import_single_session` creates and closes its own SQLite connection (safe for thread executor use)
- `test_run_import_creates_connection_in_thread` — Verifies `run_import` does not pass connections across thread boundaries

### TestToolResultBackfill
- `test_incremental_import_backfills_tool_result` — Verifies that when a tool_use is imported without its tool_result, a subsequent incremental import backfills the result (Fixes #28)

## Changes
- 2026-03-14: Added json import at module level for backfill test
- 2026-03-14: Fix assertion — tool_result is empty string not NULL when no result provided

## Notes
- DB schema has CHECK constraint: role IN ('user', 'assistant') — test data must use 'user' not 'human'
