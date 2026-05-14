# Test Spec: test_session_filter

## Purpose
Tests for `session_filter.is_interactive_session()` — distinguishes interactive Claude Code sessions from SDK-spawned subprocess sessions by inspecting the first event of the JSONL transcript.

Fixes #70 (filter SDK subprocess sessions).

## Test Cases

- `test_interactive_session_with_entrypoint_recognized` — JSONL whose first event has `entrypoint == "cli"` returns True
- `test_interactive_session_with_snapshot_event_recognized` — JSONL starting with a `file-history-snapshot` event returns True (real Claude Code can start with many event types)
- `test_interactive_session_with_permission_mode_recognized` — JSONL starting with a `permission-mode` event returns True
- `test_sdk_subprocess_rejected` — JSONL starting with `{"type": "queue-operation"}` returns False
- `test_missing_file_rejected` — Missing file returns False (treat as not importable)
- `test_empty_file_rejected` — Empty file returns False
- `test_malformed_first_line_rejected` — Non-JSON first line returns False
- `test_first_event_array_rejected` — JSON value that isn't a dict returns False

## Changes
- 2026-05-14: Initial spec
- 2026-05-14: Inverted detection: only reject `type == "queue-operation"`, accept all other event types. Initial filter (require `entrypoint == "cli"`) was too strict — only ~6/169 real interactive sessions had that field as the first-event marker.

## Notes
- Detection signal: SDK subprocesses always emit `{"type": "queue-operation", "operation": "enqueue"}` as their first event. Real interactive sessions can start with many event types (snapshot, permission-mode, progress, hook events, parent message, etc.) depending on Claude Code version and hooks.
- The filter is permissive: any first event that isn't `queue-operation` is treated as interactive.
