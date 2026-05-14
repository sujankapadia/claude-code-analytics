"""Cleanup script: remove Claude Agent SDK subprocess sessions from the DB.

For each session in the DB, look up its source JSONL on disk under
~/.claude/projects/<project_id>/<session_id>.jsonl and delete the session if:

  - The JSONL no longer exists, OR
  - The JSONL is an SDK subprocess session (first event is queue-operation
    rather than entrypoint == "cli")

Foreign-key cascade handles cleanup of messages, tool_uses, and bookmarks.

Usage:
    python -m claude_code_analytics.scripts.cleanup_sdk_sessions [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from claude_code_analytics import config
from claude_code_analytics.services.session_filter import is_interactive_session


def find_jsonl(project_id: str, session_id: str) -> Path | None:
    """Locate the JSONL for a (project_id, session_id) under ~/.claude/projects/.

    Returns the path if it exists, else None. Subagent sessions live one level
    deeper under <project_id>/<parent_session_id>/subagents/<agent>.jsonl, so
    we check both the top-level and the recursive glob.
    """
    project_dir = config.CLAUDE_CODE_PROJECTS_DIR / project_id
    if not project_dir.exists():
        return None

    direct = project_dir / f"{session_id}.jsonl"
    if direct.exists():
        return direct

    # Subagent JSONLs are nested
    matches = list(project_dir.glob(f"**/{session_id}.jsonl"))
    return matches[0] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove SDK subprocess and orphaned sessions from the DB."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without making any changes",
    )
    parser.add_argument(
        "--db-path",
        default=str(config.DATABASE_PATH),
        help=f"Path to the SQLite database (default: {config.DATABASE_PATH})",
    )
    args = parser.parse_args()

    db_path = args.db_path
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT session_id, project_id FROM sessions")
    rows = cursor.fetchall()
    print(f"Scanning {len(rows)} sessions...")

    # Track (session_id, project_id) pairs so deletion matches the same key
    # we used to classify, rather than session_id alone.
    to_delete_sdk: list[tuple[str, str]] = []
    to_delete_orphan: list[tuple[str, str]] = []

    for session_id, project_id in rows:
        jsonl = find_jsonl(project_id, session_id)
        if jsonl is None:
            to_delete_orphan.append((session_id, project_id))
        elif not is_interactive_session(jsonl):
            to_delete_sdk.append((session_id, project_id))

    print(f"  SDK subprocess sessions: {len(to_delete_sdk)}")
    print(f"  Orphaned sessions (no JSONL on disk): {len(to_delete_orphan)}")
    total = len(to_delete_sdk) + len(to_delete_orphan)
    if total == 0:
        print("Nothing to clean up.")
        return 0

    if args.dry_run:
        print("\n[DRY RUN] No changes made. Re-run without --dry-run to delete.")
        return 0

    # Delete each row by both session_id and project_id (defense in depth —
    # session_id is the PK today but matching on the same key we classified
    # with is safer if the schema ever changes).
    all_pairs = to_delete_sdk + to_delete_orphan
    cursor.executemany(
        "DELETE FROM sessions WHERE session_id = ? AND project_id = ?",
        all_pairs,
    )
    conn.commit()
    conn.close()

    print(f"\nDeleted {total} sessions (FK cascade removed associated rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
