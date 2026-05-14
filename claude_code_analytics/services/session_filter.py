"""Filter for distinguishing interactive Claude Code sessions from SDK subprocesses.

SDK-spawned subprocesses (Claude Agent SDK) write JSONL files to ~/.claude/projects/
identically to interactive sessions, but they are not user-driven and would inflate
analytics if treated as real sessions.

The reliable signal is the SDK's input-queueing mechanism: SDK subprocesses
emit a ``{"type": "queue-operation", "operation": "enqueue", ...}`` event as
their first JSONL entry. Real interactive sessions can start with many
different event types (snapshot, permission-mode, progress, hook events, etc.)
depending on Claude Code version and configured hooks, but never with a
queue-operation enqueue.
"""

import json
from pathlib import Path


def is_interactive_session(jsonl_path: Path) -> bool:
    """Return True if the JSONL file represents an interactive Claude Code session.

    SDK-spawned subprocess sessions return False and should be excluded from
    import / analytics.

    Behavior:
        - First event with ``type == "queue-operation"`` -> False (SDK)
        - Any other valid first event -> True (interactive)

    Edge cases (all return False — treat as not importable):
        - Missing or unreadable file
        - Empty file
        - Malformed first JSON line
        - First JSON value isn't an object
    """
    try:
        with open(jsonl_path) as f:
            first_line = f.readline().strip()
    except (OSError, FileNotFoundError):
        return False

    if not first_line:
        return False

    try:
        event = json.loads(first_line)
    except json.JSONDecodeError:
        return False

    if not isinstance(event, dict):
        return False

    return event.get("type") != "queue-operation"
