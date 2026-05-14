# Test Spec: test_import_service.py

## Purpose
Tests for the import service, focusing on SQLite thread safety (Fixes #13).

## Test Cases

### TestImportServiceThreadSafety
- `test_import_single_session_creates_own_connection` — Verifies `import_single_session` creates and closes its own SQLite connection (safe for thread executor use)
- `test_run_import_creates_connection_in_thread` — Verifies `run_import` completes and imports at least 1 session (assertion uses > 0, not >= 0)

### TestToolResultBackfill
- `test_incremental_import_backfills_tool_result` — Verifies that when a tool_use is imported without its tool_result, a subsequent incremental import backfills the result (Fixes #28)

## Changes
- 2026-03-14: Added json import at module level for backfill test
- 2026-03-14: Fix assertion — tool_result is empty string not NULL when no result provided
- 2026-03-20: Strengthen run_import assertion from >= 0 to > 0 to catch silent failures
- 2026-05-14: Prepend `{"entrypoint": "cli", ...}` marker to all three fixture JSONLs (sample_session_file, run_import test fixture, backfill fixture phase1+phase2) so they pass the new session_filter (#70). Real interactive Claude Code sessions always emit this marker as the first event.

## Notes
- DB schema has CHECK constraint: role IN ('user', 'assistant') — test data must use 'user' not 'human'
- Fixture JSONLs must include an interactive-session marker as the first event (`{"entrypoint": "cli"}`), or the import_service's session_filter will reject them as SDK subprocess sessions and `import_single_session` will return None.
