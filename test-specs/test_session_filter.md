# Test Spec: test_session_filter

## Purpose
Tests for `session_filter.is_interactive_session()` — distinguishes interactive Claude Code sessions from SDK-spawned subprocess sessions by inspecting the first event of the JSONL transcript.

Fixes #70 (filter SDK subprocess sessions).

## Test Cases

- `test_interactive_session_recognized` — JSONL whose first event has `entrypoint == "cli"` returns True
- `test_sdk_subprocess_rejected` — JSONL starting with `{"type": "queue-operation"}` returns False
- `test_missing_file_rejected` — Missing file returns False (treat as not importable)
- `test_empty_file_rejected` — Empty file returns False
- `test_malformed_first_line_rejected` — Non-JSON first line returns False
- `test_unknown_entrypoint_rejected` — Unknown `entrypoint` value returns False (be conservative)
- `test_first_event_array_rejected` — JSON value that isn't a dict returns False

## Notes
- Detection signal: interactive sessions emit a rich first event with `entrypoint`, `userType`, `version`, `cwd`, `gitBranch`. SDK subprocesses start with the SDK's `queue-operation` enqueue event and lack `entrypoint`.
- Function is conservative: anything other than `entrypoint == "cli"` returns False, so unknown formats won't be silently imported.
