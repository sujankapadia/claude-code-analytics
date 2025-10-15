#!/usr/bin/env python3
"""
Import Claude Code conversation transcripts into SQLite database.

This script scans the ~/.claude/projects/ directory for JSONL transcript files
and imports them into the conversations.db SQLite database for analytics.

Usage:
    python3 import_conversations.py [--db PATH] [--source PATH]
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Import Claude Code conversation transcripts into SQLite database'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=str(Path.home() / 'claude-conversations' / 'conversations.db'),
        help='Path to SQLite database (default: ~/claude-conversations/conversations.db)'
    )
    parser.add_argument(
        '--source',
        type=str,
        default=str(Path.home() / '.claude' / 'projects'),
        help='Path to Claude projects directory (default: ~/.claude/projects/)'
    )
    return parser.parse_args()


def decode_project_name(project_id: str) -> str:
    """
    Convert encoded project directory name to human-readable path.

    Example: "-Users-skapadia-dev-personal-monolog" -> "/Users/skapadia/dev/personal/monolog"

    Args:
        project_id: Encoded directory name

    Returns:
        Human-readable project path
    """
    if project_id.startswith('-'):
        # Remove leading dash and replace remaining dashes with slashes
        parts = project_id[1:].split('-')
        return '/' + '/'.join(parts)
    return project_id


def extract_text_from_content(content: Any) -> str:
    """
    Extract text content from message content array.

    Content can be:
    - A string (simple text)
    - A list of objects with 'type' and 'text' fields
    - Mixed content with tool_use/tool_result entries (skip these)

    Args:
        content: Content field from message

    Returns:
        Extracted text content
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text' and 'text' in item:
                    text_parts.append(item['text'])
            elif isinstance(item, str):
                text_parts.append(item)
        return '\n'.join(text_parts)

    return str(content)


def extract_tool_result_content(content: Any) -> str:
    """
    Extract content from tool result.

    Tool result content can be:
    - A string
    - A list of objects with 'type' and 'text' fields

    Args:
        content: Content field from tool result

    Returns:
        Extracted text content
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if 'text' in item:
                    text_parts.append(item['text'])
                elif 'content' in item:
                    text_parts.append(str(item['content']))
            elif isinstance(item, str):
                text_parts.append(item)
        return '\n'.join(text_parts)

    return str(content)


def parse_jsonl_file(file_path: Path) -> List[Dict]:
    """
    Parse a JSONL file and return list of entries.

    Args:
        file_path: Path to JSONL file

    Returns:
        List of parsed JSON objects
    """
    entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"  ⚠️  Skipping invalid JSON on line {line_num}: {e}")
                    continue
    except Exception as e:
        logger.error(f"  ❌ Error reading file {file_path}: {e}")
        return []

    return entries


def process_session(
    session_file: Path,
    project_id: str,
    conn: sqlite3.Connection
) -> Tuple[int, int]:
    """
    Process a single session JSONL file and import into database.

    Args:
        session_file: Path to session JSONL file
        project_id: Project ID this session belongs to
        conn: Database connection

    Returns:
        Tuple of (message_count, tool_use_count)
    """
    # Extract session_id from filename (remove .jsonl extension)
    session_id = session_file.stem

    # Check if session already imported
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    if cursor.fetchone():
        logger.debug(f"    Skipping session {session_id} (already imported)")
        return (0, 0)

    # Parse JSONL file
    entries = parse_jsonl_file(session_file)
    if not entries:
        logger.warning(f"    ⚠️  No entries found in {session_file.name}")
        return (0, 0)

    # Extract messages, tool uses, and tool results
    # This follows the same logic as pretty-print-transcript.py
    messages = []
    tool_uses = {}
    tool_results = {}

    for entry in entries:
        # Extract timestamp - could be 'ts' (milliseconds) or 'timestamp' (ISO string)
        timestamp = entry.get('ts') or entry.get('timestamp')

        # Message entry
        if 'message' in entry:
            msg = entry['message']
            content = msg.get('content')

            # Extract token usage for assistant messages
            usage = msg.get('usage', {})
            cache_creation = usage.get('cache_creation', {})

            messages.append({
                'role': msg.get('role'),
                'content': content,
                'timestamp': timestamp,
                'usage': {
                    'input_tokens': usage.get('input_tokens'),
                    'output_tokens': usage.get('output_tokens'),
                    'cache_creation_input_tokens': usage.get('cache_creation_input_tokens'),
                    'cache_read_input_tokens': usage.get('cache_read_input_tokens'),
                    'cache_ephemeral_5m_tokens': cache_creation.get('ephemeral_5m_input_tokens'),
                    'cache_ephemeral_1h_tokens': cache_creation.get('ephemeral_1h_input_tokens'),
                }
            })

            # Extract tool uses and tool results from message content
            # (matches logic from pretty-print-transcript.py lines 54-96)
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        # Tool use embedded in message content
                        if item.get("type") == "tool_use":
                            tool_id = item.get("id")
                            if tool_id:
                                tool_uses[tool_id] = {
                                    'name': item.get("name"),
                                    'input': item.get("input"),
                                    'timestamp': timestamp
                                }

                        # Tool result embedded in message content
                        elif item.get("type") == "tool_result":
                            tool_id = item.get("tool_use_id")
                            if tool_id:
                                tool_results[tool_id] = {
                                    'content': item.get("content"),
                                    'is_error': item.get("is_error", False)
                                }

    # Calculate session metadata
    if not messages:
        logger.warning(f"    ⚠️  No messages found in {session_file.name}")
        return (0, 0)

    start_time = messages[0]['timestamp']
    end_time = messages[-1]['timestamp']
    message_count = len(messages)
    tool_use_count = len(tool_uses)

    # Insert session
    try:
        cursor.execute("""
            INSERT INTO sessions (session_id, project_id, start_time, end_time, message_count, tool_use_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, project_id, start_time, end_time, message_count, tool_use_count))
    except sqlite3.IntegrityError as e:
        logger.warning(f"    ⚠️  Session {session_id} already exists: {e}")
        return (0, 0)

    # Insert messages
    for idx, msg in enumerate(messages):
        content_text = extract_text_from_content(msg['content'])
        usage = msg.get('usage', {})
        cursor.execute("""
            INSERT INTO messages (
                session_id, message_index, role, content, timestamp,
                input_tokens, output_tokens, cache_creation_input_tokens,
                cache_read_input_tokens, cache_ephemeral_5m_tokens, cache_ephemeral_1h_tokens
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, idx, msg['role'], content_text, msg['timestamp'],
            usage.get('input_tokens'), usage.get('output_tokens'),
            usage.get('cache_creation_input_tokens'), usage.get('cache_read_input_tokens'),
            usage.get('cache_ephemeral_5m_tokens'), usage.get('cache_ephemeral_1h_tokens')
        ))

    # Insert tool uses with results
    for tool_id, tool_data in tool_uses.items():
        tool_result_data = tool_results.get(tool_id, {})
        tool_result_content = extract_tool_result_content(tool_result_data.get('content', ''))

        # Handle duplicate tool_use_ids across sessions (from resumed sessions)
        # Use INSERT OR IGNORE to skip duplicates
        cursor.execute("""
            INSERT OR IGNORE INTO tool_uses (tool_use_id, session_id, tool_name, tool_input, tool_result, is_error, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tool_id,
            session_id,
            tool_data['name'],
            json.dumps(tool_data['input']) if tool_data['input'] else None,
            tool_result_content,
            tool_result_data.get('is_error', False),
            tool_data['timestamp']
        ))

    return (message_count, tool_use_count)


def import_project(
    project_dir: Path,
    conn: sqlite3.Connection
) -> Tuple[int, int, int]:
    """
    Import all sessions from a project directory.

    Args:
        project_dir: Path to project directory
        conn: Database connection

    Returns:
        Tuple of (session_count, message_count, tool_use_count)
    """
    project_id = project_dir.name
    project_name = decode_project_name(project_id)

    logger.info(f"📂 Importing project: {project_name}")

    # Insert project (or ignore if exists)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO projects (project_id, project_name)
            VALUES (?, ?)
        """, (project_id, project_name))
    except sqlite3.IntegrityError:
        logger.debug(f"  Project {project_id} already exists")

    # Find all JSONL files
    jsonl_files = list(project_dir.glob('*.jsonl'))
    if not jsonl_files:
        logger.info(f"  No JSONL files found")
        return (0, 0, 0)

    # Process each session
    total_sessions = 0
    total_messages = 0
    total_tool_uses = 0

    for session_file in jsonl_files:
        logger.info(f"  📄 Importing session: {session_file.name}")
        try:
            msg_count, tool_count = process_session(session_file, project_id, conn)
            if msg_count > 0:
                total_sessions += 1
                total_messages += msg_count
                total_tool_uses += tool_count
                logger.info(f"    ✅ Imported {msg_count} messages, {tool_count} tool uses")
        except Exception as e:
            logger.error(f"    ❌ Error processing session: {e}", exc_info=True)
            continue

    return (total_sessions, total_messages, total_tool_uses)


def main():
    """Main entry point for the import script."""
    args = parse_arguments()

    # Validate paths
    db_path = Path(args.db)
    source_path = Path(args.source)

    if not db_path.exists():
        logger.error(f"❌ Database not found: {db_path}")
        logger.error("   Run create_database.py first to create the database.")
        sys.exit(1)

    if not source_path.exists():
        logger.error(f"❌ Source directory not found: {source_path}")
        sys.exit(1)

    logger.info("🚀 Starting conversation import...")
    logger.info(f"📊 Database: {db_path}")
    logger.info(f"📁 Source: {source_path}\n")

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # Find all project directories
        project_dirs = [d for d in source_path.iterdir() if d.is_dir()]

        if not project_dirs:
            logger.warning("⚠️  No project directories found")
            return

        logger.info(f"Found {len(project_dirs)} project(s)\n")

        # Import each project
        total_projects = 0
        total_sessions = 0
        total_messages = 0
        total_tool_uses = 0

        commit_counter = 0

        for project_dir in project_dirs:
            try:
                sessions, messages, tool_uses = import_project(project_dir, conn)

                if sessions > 0:
                    total_projects += 1
                    total_sessions += sessions
                    total_messages += messages
                    total_tool_uses += tool_uses

                    # Commit every 100 sessions for performance
                    commit_counter += sessions
                    if commit_counter >= 100:
                        conn.commit()
                        logger.debug(f"  💾 Committed batch")
                        commit_counter = 0

            except Exception as e:
                logger.error(f"❌ Error importing project {project_dir.name}: {e}", exc_info=True)
                continue

        # Final commit
        conn.commit()

        # Print summary
        logger.info("\n" + "="*60)
        logger.info("✅ Import complete!")
        logger.info("="*60)
        logger.info(f"📂 Projects imported:   {total_projects}")
        logger.info(f"💬 Sessions imported:   {total_sessions}")
        logger.info(f"📝 Messages imported:   {total_messages}")
        logger.info(f"🔧 Tool uses imported:  {total_tool_uses}")
        logger.info("="*60)

        # Show sample query
        if total_sessions > 0:
            logger.info("\nTo view imported data:")
            logger.info(f"  sqlite3 {db_path} 'SELECT * FROM project_summary;'")

    except Exception as e:
        logger.error(f"❌ Fatal error during import: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
