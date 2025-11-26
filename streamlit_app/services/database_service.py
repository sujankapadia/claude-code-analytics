"""Database service layer for conversation analytics."""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from streamlit_app.models import (
    Project,
    Session,
    Message,
    ToolUse,
    ProjectSummary,
    SessionSummary,
    ToolUsageSummary,
)


class DatabaseService:
    """Service for database operations."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database service.

        Args:
            db_path: Path to SQLite database. Defaults to ~/claude-conversations/conversations.db
        """
        if db_path is None:
            db_path = str(Path.home() / "claude-conversations" / "conversations.db")
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # =========================================================================
    # Project queries
    # =========================================================================

    def get_all_projects(self) -> List[Project]:
        """Get all projects."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY project_name")
        rows = cursor.fetchall()
        conn.close()
        return [Project(**dict(row)) for row in rows]

    def get_project_summaries(self) -> List[ProjectSummary]:
        """Get project summaries with aggregated statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM project_summary ORDER BY total_sessions DESC")
        rows = cursor.fetchall()
        conn.close()
        return [ProjectSummary(**dict(row)) for row in rows]

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a single project by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()
        return Project(**dict(row)) if row else None

    # =========================================================================
    # Session queries
    # =========================================================================

    def get_sessions_for_project(self, project_id: str) -> List[Session]:
        """Get all sessions for a project."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM sessions
            WHERE project_id = ?
            ORDER BY start_time DESC
            """,
            (project_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [Session(**dict(row)) for row in rows]

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a single session by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return Session(**dict(row)) if row else None

    def get_session_summaries(
        self, project_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[SessionSummary]:
        """
        Get session summaries with detailed statistics.

        Args:
            project_id: Optional filter by project
            limit: Optional limit on number of results

        Returns:
            List of session summaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM session_summary"
        params = []

        if project_id:
            query += " WHERE project_id = ?"
            params.append(project_id)

        query += " ORDER BY start_time DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [SessionSummary(**dict(row)) for row in rows]

    # =========================================================================
    # Message queries
    # =========================================================================

    def get_messages_for_session(self, session_id: str) -> List[Message]:
        """Get all messages for a session."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY message_index
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [Message(**dict(row)) for row in rows]

    def get_token_usage_for_session(self, session_id: str) -> Dict[str, int]:
        """
        Get aggregated token usage for a session.

        Returns:
            Dictionary with token usage statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cache_creation_input_tokens) as total_cache_creation,
                SUM(cache_read_input_tokens) as total_cache_read,
                SUM(cache_ephemeral_5m_tokens) as total_cache_5m,
                SUM(cache_ephemeral_1h_tokens) as total_cache_1h
            FROM messages
            WHERE session_id = ? AND role = 'assistant'
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "input_tokens": row["total_input_tokens"] or 0,
                "output_tokens": row["total_output_tokens"] or 0,
                "cache_creation_tokens": row["total_cache_creation"] or 0,
                "cache_read_tokens": row["total_cache_read"] or 0,
                "cache_5m_tokens": row["total_cache_5m"] or 0,
                "cache_1h_tokens": row["total_cache_1h"] or 0,
            }
        return {}

    # =========================================================================
    # Tool use queries
    # =========================================================================

    def get_tool_uses_for_session(self, session_id: str) -> List[ToolUse]:
        """Get all tool uses for a session."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM tool_uses
            WHERE session_id = ?
            ORDER BY timestamp
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [ToolUse(**dict(row)) for row in rows]

    def get_tool_usage_summary(self) -> List[ToolUsageSummary]:
        """Get aggregated tool usage statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tool_usage_summary")
        rows = cursor.fetchall()
        conn.close()
        return [ToolUsageSummary(**dict(row)) for row in rows]

    # =========================================================================
    # Search queries
    # =========================================================================

    def search_messages(
        self,
        query: str,
        project_id: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search messages using FTS5 full-text search.

        Args:
            query: Search query
            project_id: Optional filter by project
            role: Optional filter by role (user/assistant)
            limit: Maximum number of results

        Returns:
            List of matching messages with context
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build query
        sql = """
            SELECT
                m.message_id,
                m.session_id,
                m.role,
                m.content,
                m.timestamp,
                s.project_id,
                p.project_name,
                snippet(messages_fts, -1, '<mark>', '</mark>', '...', 64) as snippet
            FROM messages_fts
            JOIN messages m ON messages_fts.rowid = m.message_id
            JOIN sessions s ON m.session_id = s.session_id
            JOIN projects p ON s.project_id = p.project_id
            WHERE messages_fts MATCH ?
        """
        params = [query]

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if role:
            sql += " AND m.role = ?"
            params.append(role)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # =========================================================================
    # Analytics queries
    # =========================================================================

    def get_daily_statistics(
        self, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily aggregated statistics.

        Args:
            days: Number of days to include

        Returns:
            Daily statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                DATE(timestamp) as date,
                COUNT(DISTINCT session_id) as sessions,
                COUNT(*) as messages,
                SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                SUM(COALESCE(input_tokens, 0)) as input_tokens,
                SUM(COALESCE(output_tokens, 0)) as output_tokens
            FROM messages
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            """,
            (days,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
