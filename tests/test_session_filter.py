"""Tests for session_filter.is_interactive_session."""

import json

from claude_code_analytics.services.session_filter import is_interactive_session


def _write_jsonl(tmp_path, name, lines):
    p = tmp_path / name
    with open(p, "w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return p


def test_interactive_session_with_entrypoint_recognized(tmp_path):
    """Real interactive session with entrypoint marker is accepted."""
    p = _write_jsonl(
        tmp_path,
        "interactive.jsonl",
        [
            {
                "entrypoint": "cli",
                "userType": "external",
                "version": "2.1.81",
                "cwd": "/some/dir",
                "sessionId": "abc",
            }
        ],
    )
    assert is_interactive_session(p) is True


def test_interactive_session_with_snapshot_event_recognized(tmp_path):
    """Real interactive sessions can start with file-history-snapshot."""
    p = _write_jsonl(
        tmp_path,
        "snapshot.jsonl",
        [
            {
                "type": "file-history-snapshot",
                "messageId": "abc",
                "snapshot": {"trackedFileBackups": {}},
            }
        ],
    )
    assert is_interactive_session(p) is True


def test_interactive_session_with_permission_mode_recognized(tmp_path):
    """Real interactive sessions can start with permission-mode."""
    p = _write_jsonl(
        tmp_path,
        "perm.jsonl",
        [{"type": "permission-mode", "permissionMode": "default", "sessionId": "abc"}],
    )
    assert is_interactive_session(p) is True


def test_sdk_subprocess_rejected(tmp_path):
    """A JSONL starting with queue-operation is an SDK subprocess."""
    p = _write_jsonl(
        tmp_path,
        "sdk.jsonl",
        [
            {
                "type": "queue-operation",
                "operation": "enqueue",
                "sessionId": "abc",
                "content": "instructions...",
            }
        ],
    )
    assert is_interactive_session(p) is False


def test_missing_file_rejected(tmp_path):
    """Missing files are not importable."""
    assert is_interactive_session(tmp_path / "nonexistent.jsonl") is False


def test_empty_file_rejected(tmp_path):
    """Empty files are not importable."""
    p = tmp_path / "empty.jsonl"
    p.touch()
    assert is_interactive_session(p) is False


def test_malformed_first_line_rejected(tmp_path):
    """A non-JSON first line is rejected (don't import unknown formats)."""
    p = tmp_path / "bad.jsonl"
    p.write_text("not json at all\n")
    assert is_interactive_session(p) is False


def test_first_event_array_rejected(tmp_path):
    """A JSON value that isn't a dict at line 1 is rejected."""
    p = tmp_path / "array.jsonl"
    p.write_text("[1, 2, 3]\n")
    assert is_interactive_session(p) is False
