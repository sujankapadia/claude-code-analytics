#!/usr/bin/env python3
"""
Create FTS5 (Full-Text Search) index for Claude Code conversations.

This script:
1. Creates FTS5 virtual tables in SQLite
2. Indexes message content and tool results for fast search
3. Supports boolean queries, phrase matching, and advanced search
"""

import sqlite3
from pathlib import Path
import sys


FTS_SCHEMA = """
-- ============================================================================
-- FTS5 VIRTUAL TABLES
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
    print("🚀 Creating FTS5 indexes...")
    print(f"📊 Database: {db_path}\n")

    conn = sqlite3.connect(db_path)

    try:
        # Create FTS5 tables
        print("1️⃣  Creating FTS5 virtual tables...")
        conn.executescript(FTS_SCHEMA)
        print("   ✅ Created fts_messages and fts_tool_uses tables\n")

        # Populate fts_messages from messages table
        print("2️⃣  Populating fts_messages...")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO fts_messages (
                content, role, project_name, session_id,
                message_id, timestamp, message_index
            )
            SELECT
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
        print(f"   ✅ Indexed {message_count:,} messages\n")

        # Populate fts_tool_uses from tool_uses table
        print("3️⃣  Populating fts_tool_uses...")

        cursor.execute("""
            INSERT INTO fts_tool_uses (
                tool_name, tool_input, tool_result, project_name,
                session_id, tool_use_id, timestamp
            )
            SELECT
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
        print(f"   ✅ Indexed {tool_count:,} tool uses\n")

        conn.commit()

        # Show statistics
        print("📊 FTS5 Index Statistics:")
        print(f"   Messages indexed: {message_count:,}")
        print(f"   Tool uses indexed: {tool_count:,}")

        # Calculate index size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size_bytes = cursor.fetchone()[0]
        db_size_mb = db_size_bytes / (1024 * 1024)
        print(f"   Total database size: {db_size_mb:.1f} MB")

        print("\n✅ FTS5 indexing complete!")
        print("\n💡 Search features available:")
        print("   • Boolean: 'async AND error'")
        print("   • Phrase: '\"promise rejection\"'")
        print("   • Exclude: 'typescript NOT react'")
        print("   • Wildcard: 'data*'")
        print("   • Column: 'role:user async'")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point."""
    # Default database path
    home = Path.home()
    db_path = home / "claude-conversations" / "conversations.db"

    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Run import_conversations.py first to create the database.")
        sys.exit(1)

    # Create FTS index
    try:
        create_fts_index(str(db_path))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
