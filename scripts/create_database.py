#!/usr/bin/env python3
"""
Create SQLite database schema for Claude Code conversation analytics.

This script creates a normalized database schema for analyzing Claude Code
conversation transcripts. The schema includes tables for projects, sessions,
messages, and tool uses, along with indexes and summary views.

Usage:
    python3 create_database.py
"""

import sqlite3
import os
from pathlib import Path


# SQLite schema definition
SCHEMA_SQL = """
-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================
-- Stores information about each project (directory) containing conversations
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,        -- Encoded directory name from ~/.claude/projects/
    project_name TEXT NOT NULL,         -- Human-readable project name (derived from project_id)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SESSIONS TABLE
-- ============================================================================
-- Stores metadata about each conversation session (JSONL file)
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,        -- UUID from JSONL filename
    project_id TEXT NOT NULL,           -- Foreign key to projects table
    start_time TIMESTAMP,               -- Timestamp of first message
    end_time TIMESTAMP,                 -- Timestamp of last message
    message_count INTEGER DEFAULT 0,    -- Total number of messages in session
    tool_use_count INTEGER DEFAULT 0,   -- Total number of tool uses in session
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

-- ============================================================================
-- MESSAGES TABLE
-- ============================================================================
-- Stores individual messages (user and assistant) from conversations
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,           -- Foreign key to sessions table
    message_index INTEGER NOT NULL,     -- Order within session (0, 1, 2, ...)
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT,                       -- Full message text extracted from content array
    timestamp TIMESTAMP NOT NULL,       -- When message was sent

    -- Token usage fields (only populated for assistant messages)
    input_tokens INTEGER,               -- Total input tokens
    output_tokens INTEGER,              -- Total output tokens
    cache_creation_input_tokens INTEGER, -- Tokens used for cache creation
    cache_read_input_tokens INTEGER,    -- Tokens read from cache
    cache_ephemeral_5m_tokens INTEGER,  -- 5-minute ephemeral cache tokens
    cache_ephemeral_1h_tokens INTEGER,  -- 1-hour ephemeral cache tokens

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE(session_id, message_index)   -- Ensure no duplicate indices per session
);

-- ============================================================================
-- TOOL_USES TABLE
-- ============================================================================
-- Stores information about tool invocations and their results
CREATE TABLE IF NOT EXISTS tool_uses (
    tool_use_id TEXT PRIMARY KEY,       -- ID from toolUse entry (e.g., "toolu_...")
    session_id TEXT NOT NULL,           -- Foreign key to sessions table
    tool_name TEXT NOT NULL,            -- Tool name (Bash, Write, Edit, Read, etc.)
    tool_input TEXT,                    -- JSON string of input parameters
    tool_result TEXT,                   -- Result text from corresponding toolResult
    is_error BOOLEAN DEFAULT 0,         -- Boolean from toolResult
    timestamp TIMESTAMP NOT NULL,       -- When tool was invoked

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES
-- ============================================================================
-- Indexes to optimize common query patterns

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_end_time ON sessions(end_time);

-- Messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

-- Tool uses indexes
CREATE INDEX IF NOT EXISTS idx_tool_uses_session_id ON tool_uses(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_uses_tool_name ON tool_uses(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_uses_timestamp ON tool_uses(timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_uses_is_error ON tool_uses(is_error);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Project summary view - aggregated statistics per project
CREATE VIEW IF NOT EXISTS project_summary AS
SELECT
    p.project_id,
    p.project_name,
    COUNT(DISTINCT s.session_id) as total_sessions,
    MIN(s.start_time) as first_session,
    MAX(s.end_time) as last_session,
    COALESCE(SUM(s.message_count), 0) as total_messages,
    COALESCE(SUM(s.tool_use_count), 0) as total_tool_uses
FROM
    projects p
    LEFT JOIN sessions s ON p.project_id = s.project_id
GROUP BY
    p.project_id, p.project_name;

-- Session summary view - detailed statistics per session
CREATE VIEW IF NOT EXISTS session_summary AS
SELECT
    s.session_id,
    s.project_id,
    p.project_name,
    s.start_time,
    s.end_time,
    CAST((julianday(s.end_time) - julianday(s.start_time)) * 86400 AS INTEGER) as duration_seconds,
    s.message_count,
    s.tool_use_count,
    COUNT(DISTINCT CASE WHEN m.role = 'user' THEN m.message_id END) as user_message_count,
    COUNT(DISTINCT CASE WHEN m.role = 'assistant' THEN m.message_id END) as assistant_message_count
FROM
    sessions s
    INNER JOIN projects p ON s.project_id = p.project_id
    LEFT JOIN messages m ON s.session_id = m.session_id
GROUP BY
    s.session_id;

-- Tool usage summary - statistics by tool name
CREATE VIEW IF NOT EXISTS tool_usage_summary AS
SELECT
    tool_name,
    COUNT(*) as total_uses,
    SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as error_count,
    ROUND(SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as error_rate_percent,
    COUNT(DISTINCT session_id) as sessions_used_in,
    MIN(timestamp) as first_used,
    MAX(timestamp) as last_used
FROM
    tool_uses
GROUP BY
    tool_name
ORDER BY
    total_uses DESC;
"""


def create_database(db_path: str) -> None:
    """
    Create the SQLite database with the conversation analytics schema.

    Args:
        db_path: Path to the SQLite database file
    """
    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

    try:
        # Execute the schema SQL
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"✅ Database schema created successfully at: {db_path}")

        # Verify tables were created
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 Created tables: {', '.join(tables)}")

        # Verify views were created
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='view'
            ORDER BY name
        """)
        views = [row[0] for row in cursor.fetchall()]
        if views:
            print(f"👁️  Created views: {', '.join(views)}")

        # Verify indexes were created
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY name
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        if indexes:
            print(f"🔍 Created indexes: {len(indexes)} total")

    except sqlite3.Error as e:
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        conn.close()


def main():
    """Main entry point for the script."""
    # Default database path
    home_dir = Path.home()
    db_path = home_dir / "claude-conversations" / "conversations.db"

    print("🚀 Creating Claude Code conversation analytics database...")
    print(f"📍 Database location: {db_path}\n")

    # Create the database
    create_database(str(db_path))

    print(f"\n✨ Done! You can now populate the database with conversation data.")
    print(f"\nTo view the database:")
    print(f"  sqlite3 {db_path}")
    print(f"\nTo query the project summary:")
    print(f"  sqlite3 {db_path} 'SELECT * FROM project_summary;'")


if __name__ == "__main__":
    main()
