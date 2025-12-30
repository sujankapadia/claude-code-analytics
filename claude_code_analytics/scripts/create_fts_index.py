#!/usr/bin/env python3
"""
Create FTS5 (Full-Text Search) index for Claude Code conversations.

This script:
1. Creates FTS5 virtual tables in SQLite
2. Indexes message content and tool results for fast search
3. Supports boolean queries, phrase matching, and advanced search
"""

import sqlite3
import logging
from pathlib import Path
import sys

from claude_code_analytics import config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


FTS_SCHEMA = """
-- ============================================================================
-- FTS5 VIRTUAL TABLES
-- ============================================================================
--
-- SECURITY NOTE: FTS5 queries accept user input via parameterized queries (?).
-- While this prevents SQL injection, it does NOT prevent FTS5 syntax errors.
-- User-supplied queries with invalid syntax (unmatched quotes, invalid operators)
-- will cause sqlite3.OperationalError exceptions.
--
-- All code using MATCH queries should handle these errors gracefully with
-- try-except blocks and provide helpful error messages to users.
-- ============================================================================

-- Drop existing tables if they exist
DROP TABLE IF EXISTS fts_messages;
DROP TABLE IF EXISTS fts_tool_uses;

-- FTS5 table for message content
CREATE VIRTUAL TABLE fts_messages USING fts5(
    content,                    -- Message text content
    role,                       -- user or assistant
    project_name,               -- For filtering
    session_id,                 -- For grouping results
    message_id UNINDEXED,       -- Don't index, just store
    timestamp UNINDEXED,        -- Don't index, just store
    message_index UNINDEXED,    -- Don't index, just store
    tokenize = 'porter unicode61'  -- Better tokenization for code
);

-- FTS5 table for tool uses (commands, file paths, results)
CREATE VIRTUAL TABLE fts_tool_uses USING fts5(
    tool_name,                  -- Name of the tool
    tool_input,                 -- Input parameters (JSON)
    tool_result,                -- Result content
    project_name,               -- For filtering
    session_id,                 -- For grouping
    tool_use_id UNINDEXED,      -- Don't index, just store
    timestamp UNINDEXED,        -- Don't index, just store
    tokenize = 'porter unicode61'
);
"""


def create_fts_index(db_path: str):
    """
    Create FTS5 indexes in the database.

    Args:
        db_path: Path to SQLite database
    """
    logger.info("Creating FTS5 indexes...")
    logger.info(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)

    try:
        # Create FTS5 tables
        logger.info("Creating FTS5 virtual tables...")
        conn.executescript(FTS_SCHEMA)
        logger.info("Created fts_messages and fts_tool_uses tables")

        # Populate fts_messages from messages table
        logger.info("Populating fts_messages...")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO fts_messages (
                rowid, content, role, project_name, session_id,
                message_id, timestamp, message_index
            )
            SELECT
                m.message_id,
                m.content,
                m.role,
                p.project_name,
                m.session_id,
                m.message_id,
                m.timestamp,
                m.message_index
            FROM messages m
            JOIN sessions s ON m.session_id = s.session_id
            JOIN projects p ON s.project_id = p.project_id
            WHERE m.content IS NOT NULL AND LENGTH(m.content) > 0
        """)

        message_count = cursor.rowcount
        logger.info(f"Indexed {message_count:,} messages")

        # Populate fts_tool_uses from tool_uses table
        logger.info("Populating fts_tool_uses...")

        cursor.execute("""
            INSERT INTO fts_tool_uses (
                rowid, tool_name, tool_input, tool_result, project_name,
                session_id, tool_use_id, timestamp
            )
            SELECT
                t.rowid,
                t.tool_name,
                t.tool_input,
                t.tool_result,
                p.project_name,
                t.session_id,
                t.tool_use_id,
                t.timestamp
            FROM tool_uses t
            JOIN sessions s ON t.session_id = s.session_id
            JOIN projects p ON s.project_id = p.project_id
        """)

        tool_count = cursor.rowcount
        logger.info(f"Indexed {tool_count:,} tool uses")

        conn.commit()

        # Show statistics
        logger.info("FTS5 Index Statistics:")
        logger.info(f"  Messages indexed: {message_count:,}")
        logger.info(f"  Tool uses indexed: {tool_count:,}")

        # Calculate index size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size_bytes = cursor.fetchone()[0]
        db_size_mb = db_size_bytes / (1024 * 1024)
        logger.info(f"  Total database size: {db_size_mb:.1f} MB")

        logger.info("FTS5 indexing complete!")
        logger.info("Search features available:")
        logger.info("  Boolean: 'async AND error'")
        logger.info("  Phrase: '\"promise rejection\"'")
        logger.info("  Exclude: 'typescript NOT react'")
        logger.info("  Wildcard: 'data*'")
        logger.info("  Column: 'role:user async'")

    except Exception as e:
        logger.error(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point."""
    # Use config for database path
    db_path = config.DATABASE_PATH

    # Check if database exists
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.info("Run import_conversations.py first to create and populate the database.")
        sys.exit(1)

    # Create FTS index
    try:
        create_fts_index(str(db_path))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
