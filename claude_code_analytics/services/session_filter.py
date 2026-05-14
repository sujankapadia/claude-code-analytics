"""Filter for distinguishing interactive Claude Code sessions from SDK subprocesses.

SDK-spawned subprocesses (Claude Agent SDK) write JSONL files to ~/.claude/projects/
identically to interactive sessions, but they are not user-driven and would inflate
analytics if treated as real sessions.

The reliable signal is in the first event of the JSONL:
    - Interactive sessions start with a rich event including ``"entrypoint": "cli"``
    - SDK subprocess sessions start with ``"type": "queue-operation"`` and lack
      the ``entrypoint`` field
"""

import json
from pathlib import Path


def is_interactive_session(jsonl_path: Path) -> bool:
    """Return True if the JSONL file represents an interactive Claude Code session.

    SDK-spawned subprocess sessions return False and should be excluded from
    import / analytics.

    Behavior on edge cases:
        - Missing or unreadable file -> False (treat as not importable)
        - Empty file -> False
        - Malformed first JSON line -> False
        - First event with ``entrypoint == "cli"`` -> True
        - First event with ``type == "queue-operation"`` -> False
        - Anything else -> False (be conservative; don't import unknown formats)
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

    return event.get("entrypoint") == "cli"
