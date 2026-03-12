"""Import service extracted from scripts/import_conversations.py.

Provides incremental import with inline FTS updates (no full rebuild needed).
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from claude_code_analytics import config
from claude_code_analytics.api.services.event_bus import EventBus
from claude_code_analytics.scripts.import_conversations import (
    decode_project_name,
    extract_text_from_content,
    extract_tool_result_content,
    import_project,
    normalize_timestamp,
    parse_jsonl_file,
)

logger = logging.getLogger(__name__)


def import_single_session(
    session_path: Path, db_path: Optional[str] = None
) -> Optional[tuple[int, int]]:
    """Import a single session JSONL file with incremental FTS updates.

    Args:
        session_path: Path to the .jsonl session file
        db_path: Optional database path

    Returns:
        Tuple of (message_count, tool_use_count) or None if nothing imported
    """
    if db_path is None:
        db_path = str(config.DATABASE_PATH)

    if not session_path.exists() or session_path.suffix != ".jsonl":
        return None

    # Derive project_id from parent directory
    project_id = session_path.parent.name
    project_name = decode_project_name(project_id)
    session_id = session_path.stem

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = conn.cursor()

        # Ensure project exists
        cursor.execute(
            "INSERT OR IGNORE INTO projects (project_id, project_name) VALUES (?, ?)",
            (project_id, project_name),
        )

        # Check current max message index
        cursor.execute(
            "SELECT MAX(message_index) FROM messages WHERE session_id = ?",
            (session_id,),
        )
        result = cursor.fetchone()
        max_index = result[0] if result and result[0] is not None else -1

        entries = parse_jsonl_file(session_path)
        if not entries:
            return None

        # Parse all messages to get correct indices
        messages = []
        tool_uses = {}
        tool_results = {}

        for entry in entries:
            timestamp = normalize_timestamp(entry.get("ts") or entry.get("timestamp"))

            if "message" in entry:
                msg = entry["message"]
                content = msg.get("content")
                usage = msg.get("usage", {})
                cache_creation = usage.get("cache_creation", {})
                current_index = len(messages)

                messages.append(
                    {
                        "role": msg.get("role"),
                        "content": content,
                        "timestamp": timestamp,
                        "usage": {
                            "input_tokens": usage.get("input_tokens"),
                            "output_tokens": usage.get("output_tokens"),
                            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
                            "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
                            "cache_ephemeral_5m_tokens": cache_creation.get(
                                "ephemeral_5m_input_tokens"
                            ),
                            "cache_ephemeral_1h_tokens": cache_creation.get(
                                "ephemeral_1h_input_tokens"
                            ),
                        },
                    }
                )

                if isinstance(content, list) and current_index > max_index:
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "tool_use":
                                tool_id = item.get("id")
                                if tool_id:
                                    tool_uses[tool_id] = {
                                        "name": item.get("name"),
                                        "input": item.get("input"),
                                        "timestamp": timestamp,
                                        "message_index": current_index,
                                    }
                            elif item.get("type") == "tool_result":
                                tool_id = item.get("tool_use_id")
                                if tool_id:
                                    tool_results[tool_id] = {
                                        "content": item.get("content"),
                                        "is_error": item.get("is_error", False),
                                    }

        if not messages:
            return None

        new_messages = [msg for idx, msg in enumerate(messages) if idx > max_index]
        if not new_messages and max_index >= 0:
            return None

        is_incremental = max_index >= 0
        start_time = messages[0]["timestamp"]
        end_time = messages[-1]["timestamp"]
        total_message_count = len(messages)

        if is_incremental:
            cursor.execute("SELECT COUNT(*) FROM tool_uses WHERE session_id = ?", (session_id,))
            existing_tool_count = cursor.fetchone()[0]
            total_tool_count = existing_tool_count + len(tool_uses)
        else:
            total_tool_count = len(tool_uses)

        # Insert or update session
        if is_incremental:
            cursor.execute(
                "UPDATE sessions SET end_time = ?, message_count = ?, tool_use_count = ? WHERE session_id = ?",
                (end_time, total_message_count, total_tool_count, session_id),
            )
        else:
            try:
                cursor.execute(
                    "INSERT INTO sessions (session_id, project_id, start_time, end_time, message_count, tool_use_count) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        project_id,
                        start_time,
                        end_time,
                        total_message_count,
                        total_tool_count,
                    ),
                )
            except sqlite3.IntegrityError:
                return None

        # Insert messages and FTS entries in same transaction
        message_rows = []
        for idx, msg in enumerate(messages):
            if idx <= max_index:
                continue

            content_text = extract_text_from_content(msg["content"])
            usage = msg.get("usage", {})
            message_rows.append(
                (
                    session_id,
                    idx,
                    msg["role"],
                    content_text,
                    msg["timestamp"],
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("cache_creation_input_tokens"),
                    usage.get("cache_read_input_tokens"),
                    usage.get("cache_ephemeral_5m_tokens"),
                    usage.get("cache_ephemeral_1h_tokens"),
                )
            )

        if message_rows:
            cursor.executemany(
                """INSERT INTO messages (
                    session_id, message_index, role, content, timestamp,
                    input_tokens, output_tokens, cache_creation_input_tokens,
                    cache_read_input_tokens, cache_ephemeral_5m_tokens, cache_ephemeral_1h_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                message_rows,
            )

            # Insert FTS entries for new messages
            # Get the rowids of newly inserted messages
            cursor.execute(
                "SELECT message_id, content, role, session_id, timestamp, message_index FROM messages WHERE session_id = ? AND message_index > ?",
                (session_id, max_index),
            )
            for row in cursor.fetchall():
                try:
                    cursor.execute(
                        "INSERT INTO fts_messages (rowid, content, role, project_name, session_id, message_id, timestamp, message_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (row[0], row[1], row[2], project_name, row[3], row[0], row[4], row[5]),
                    )
                except sqlite3.OperationalError:
                    # FTS table might not exist yet
                    break

        # Insert tool uses and FTS entries
        tool_rows = []
        for tool_id, tool_data in tool_uses.items():
            tool_result_data = tool_results.get(tool_id, {})
            tool_result_content = extract_tool_result_content(tool_result_data.get("content", ""))
            tool_rows.append(
                (
                    tool_id,
                    session_id,
                    tool_data["message_index"],
                    tool_data["name"],
                    json.dumps(tool_data["input"]) if tool_data["input"] else None,
                    tool_result_content,
                    tool_result_data.get("is_error", False),
                    tool_data["timestamp"],
                )
            )

        if tool_rows:
            cursor.executemany(
                "INSERT OR IGNORE INTO tool_uses (tool_use_id, session_id, message_index, tool_name, tool_input, tool_result, is_error, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                tool_rows,
            )

            # Insert FTS entries for new tool uses
            for row in tool_rows:
                tool_use_id = row[0]
                cursor.execute("SELECT rowid FROM tool_uses WHERE tool_use_id = ?", (tool_use_id,))
                rowid_row = cursor.fetchone()
                if rowid_row:
                    try:
                        cursor.execute(
                            "INSERT OR IGNORE INTO fts_tool_uses (rowid, tool_name, tool_input, tool_result, project_name, session_id, tool_use_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                rowid_row[0],
                                row[3],
                                row[4],
                                row[5],
                                project_name,
                                session_id,
                                tool_use_id,
                                row[7],
                            ),
                        )
                    except sqlite3.OperationalError:
                        break

        conn.commit()
        return (len(new_messages), len(tool_uses))

    except Exception:
        conn.rollback()
        logger.exception(f"Failed to import session {session_path.name}")
        return None
    finally:
        conn.close()


async def run_import(event_bus: EventBus, db_path: Optional[str] = None) -> dict[str, Any]:
    """Run a full import, publishing progress events.

    Args:
        event_bus: EventBus for progress updates
        db_path: Optional database path

    Returns:
        Summary dict with counts
    """
    import asyncio

    if db_path is None:
        db_path = str(config.DATABASE_PATH)

    source_path = config.CLAUDE_CODE_PROJECTS_DIR
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_path}")

    # Auto-create database if needed
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        from claude_code_analytics.scripts.create_database import create_database

        create_database(db_path)

    project_dirs = [d for d in source_path.iterdir() if d.is_dir()]
    total_projects = 0
    total_sessions = 0
    total_messages = 0
    total_tool_uses = 0

    loop = asyncio.get_event_loop()

    for i, project_dir in enumerate(project_dirs):
        await event_bus.publish(
            {
                "type": "import_progress",
                "project": decode_project_name(project_dir.name),
                "current": i + 1,
                "total": len(project_dirs),
            }
        )

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            sessions, messages, tool_uses = await loop.run_in_executor(
                None, import_project, project_dir, conn
            )
            conn.commit()
            if sessions > 0:
                total_projects += 1
                total_sessions += sessions
                total_messages += messages
                total_tool_uses += tool_uses
        except Exception:
            conn.rollback()
            logger.exception(f"Error importing project {project_dir.name}")
        finally:
            conn.close()

    # Rebuild FTS index after full import
    if total_messages > 0:
        from claude_code_analytics.scripts.create_fts_index import create_fts_index

        await loop.run_in_executor(None, create_fts_index, db_path)

    summary = {
        "projects": total_projects,
        "sessions": total_sessions,
        "messages": total_messages,
        "tool_uses": total_tool_uses,
    }

    await event_bus.publish({"type": "import_complete", **summary})
    return summary
