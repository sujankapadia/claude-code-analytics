"""Database service layer for conversation analytics."""

import sqlite3
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports

from claude_code_analytics import config
from claude_code_analytics.streamlit_app.models import (
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
            db_path: Path to SQLite database. Defaults to config.DATABASE_PATH
        """
        if db_path is None:
            db_path = str(config.DATABASE_PATH)
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
        cursor.execute("SELECT * FROM project_summary ORDER BY total_messages DESC")
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

    def get_messages_in_range(
        self,
        session_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Message]:
        """
        Get messages for a session filtered by timestamp range.

        Args:
            session_id: Session UUID
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)

        Returns:
            List of Message objects in chronological order
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM messages WHERE session_id = ?"
        params = [session_id]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY message_index"

        cursor.execute(query, params)
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

    def get_token_timeline_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get cumulative token usage timeline for a session.

        Returns ordered list of data points showing cumulative tokens over time,
        suitable for visualization in charts.

        Args:
            session_id: Session UUID

        Returns:
            List of dictionaries with keys:
                - timestamp: ISO format timestamp
                - cumulative_tokens: Running total of input + output tokens
                - input_tokens: Input tokens for this message
                - output_tokens: Output tokens for this message
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                timestamp,
                input_tokens,
                output_tokens
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        # Calculate cumulative totals
        cumulative_tokens = 0
        timeline = []

        for row in rows:
            input_tok = row["input_tokens"] or 0
            output_tok = row["output_tokens"] or 0
            cumulative_tokens += input_tok + output_tok

            timeline.append({
                "timestamp": row["timestamp"],
                "cumulative_tokens": cumulative_tokens,
                "input_tokens": input_tok,
                "output_tokens": output_tok,
            })

        return timeline

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

    def get_tool_uses_in_range(
        self,
        session_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ToolUse]:
        """
        Get tool uses for a session filtered by timestamp range.

        Args:
            session_id: Session UUID
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)

        Returns:
            List of ToolUse objects in chronological order
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM tool_uses WHERE session_id = ?"
        params = [session_id]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp"

        cursor.execute(query, params)
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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search messages using FTS5 full-text search.

        Args:
            query: Search query
            project_id: Optional filter by project
            role: Optional filter by role (user/assistant)
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Offset for pagination

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
                m.message_index,
                m.role,
                m.content,
                m.timestamp,
                s.project_id,
                p.project_name,
                snippet(fts_messages, -1, '<mark>', '</mark>', '...', 64) as snippet
            FROM fts_messages
            JOIN messages m ON fts_messages.rowid = m.message_id
            JOIN sessions s ON m.session_id = s.session_id
            JOIN projects p ON s.project_id = p.project_id
            WHERE fts_messages MATCH ?
        """
        params = [query]

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if role:
            sql += " AND m.role = ?"
            params.append(role)

        if start_date:
            sql += " AND m.timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND m.timestamp <= ?"
            params.append(end_date)

        sql += " ORDER BY rank LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_tool_inputs(
        self,
        query: str,
        project_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search tool input parameters using FTS5.

        Args:
            query: Search query
            project_id: Optional filter by project
            tool_name: Optional filter by tool name
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching tool uses
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT
                t.tool_use_id,
                t.session_id,
                t.message_index,
                t.tool_name,
                t.tool_input,
                t.timestamp,
                s.project_id,
                p.project_name
            FROM fts_tool_uses
            JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
            JOIN sessions s ON t.session_id = s.session_id
            JOIN projects p ON s.project_id = p.project_id
            WHERE fts_tool_uses MATCH 'tool_input:' || ?
        """
        params = [query]

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if tool_name:
            sql += " AND t.tool_name = ?"
            params.append(tool_name)

        if start_date:
            sql += " AND t.timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND t.timestamp <= ?"
            params.append(end_date)

        sql += " ORDER BY t.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_tool_results(
        self,
        query: str,
        project_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search tool results/output using FTS5.

        Args:
            query: Search query
            project_id: Optional filter by project
            tool_name: Optional filter by tool name
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching tool uses
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT
                t.tool_use_id,
                t.session_id,
                t.message_index,
                t.tool_name,
                t.tool_result,
                t.is_error,
                t.timestamp,
                s.project_id,
                p.project_name
            FROM fts_tool_uses
            JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
            JOIN sessions s ON t.session_id = s.session_id
            JOIN projects p ON s.project_id = p.project_id
            WHERE fts_tool_uses MATCH 'tool_result:' || ?
        """
        params = [query]

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if tool_name:
            sql += " AND t.tool_name = ?"
            params.append(tool_name)

        if start_date:
            sql += " AND t.timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND t.timestamp <= ?"
            params.append(end_date)

        sql += " ORDER BY t.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_all(
        self,
        query: str,
        project_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Combined search across messages and tools.

        Args:
            query: Search query
            project_id: Optional filter by project
            tool_name: Optional filter by tool name (only for tool results)
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of all matching results (messages and tool uses)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Union of message search and tool search
        sql = """
            SELECT * FROM (
                -- Messages
                SELECT
                    m.session_id,
                    m.message_index,
                    'message' as result_type,
                    m.role as detail,
                    m.content as matched_content,
                    m.timestamp,
                    s.project_id,
                    p.project_name
                FROM fts_messages
                JOIN messages m ON fts_messages.rowid = m.message_id
                JOIN sessions s ON m.session_id = s.session_id
                JOIN projects p ON s.project_id = p.project_id
                WHERE fts_messages MATCH ?
        """
        params = [query]

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if start_date:
            sql += " AND m.timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND m.timestamp <= ?"
            params.append(end_date)

        sql += """
                UNION ALL

                -- Tool inputs
                SELECT
                    t.session_id,
                    t.message_index,
                    'tool_input' as result_type,
                    t.tool_name as detail,
                    t.tool_input as matched_content,
                    t.timestamp,
                    s.project_id,
                    p.project_name
                FROM fts_tool_uses
                JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                JOIN sessions s ON t.session_id = s.session_id
                JOIN projects p ON s.project_id = p.project_id
                WHERE fts_tool_uses MATCH 'tool_input:' || ?
        """
        params.append(query)

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if tool_name:
            sql += " AND t.tool_name = ?"
            params.append(tool_name)

        if start_date:
            sql += " AND t.timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND t.timestamp <= ?"
            params.append(end_date)

        sql += """
                UNION ALL

                -- Tool results
                SELECT
                    t.session_id,
                    t.message_index,
                    'tool_result' as result_type,
                    t.tool_name as detail,
                    t.tool_result as matched_content,
                    t.timestamp,
                    s.project_id,
                    p.project_name
                FROM fts_tool_uses
                JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                JOIN sessions s ON t.session_id = s.session_id
                JOIN projects p ON s.project_id = p.project_id
                WHERE fts_tool_uses MATCH 'tool_result:' || ?
        """
        params.append(query)

        if project_id:
            sql += " AND s.project_id = ?"
            params.append(project_id)

        if tool_name:
            sql += " AND t.tool_name = ?"
            params.append(tool_name)

        if start_date:
            sql += " AND t.timestamp >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND t.timestamp <= ?"
            params.append(end_date)

        sql += """
            )
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_unique_tool_names(self) -> List[str]:
        """Get list of all tool names used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT tool_name FROM tool_uses ORDER BY tool_name")
        rows = cursor.fetchall()
        conn.close()
        return [row["tool_name"] for row in rows]

    def get_mcp_tool_stats(self) -> Dict[str, Any]:
        """Get MCP tool usage statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get MCP tool usage by tool name
        cursor.execute("""
            SELECT
                tool_name,
                COUNT(*) as use_count,
                COUNT(DISTINCT session_id) as session_count
            FROM tool_uses
            WHERE tool_name LIKE 'mcp__%'
            GROUP BY tool_name
            ORDER BY use_count DESC
        """)
        tool_stats = [dict(row) for row in cursor.fetchall()]

        # Get MCP by server (extract server from tool name)
        cursor.execute("""
            SELECT
                SUBSTR(tool_name, 1, INSTR(SUBSTR(tool_name, 6), '__') + 4) as mcp_server,
                COUNT(*) as total_uses,
                COUNT(DISTINCT session_id) as session_count
            FROM tool_uses
            WHERE tool_name LIKE 'mcp__%'
            GROUP BY mcp_server
            ORDER BY total_uses DESC
        """)
        server_stats = [dict(row) for row in cursor.fetchall()]

        # Get total MCP uses
        cursor.execute("""
            SELECT
                COUNT(*) as total_mcp_uses,
                COUNT(DISTINCT session_id) as total_sessions
            FROM tool_uses
            WHERE tool_name LIKE 'mcp__%'
        """)
        totals = dict(cursor.fetchone())

        conn.close()

        return {
            "total_uses": totals.get("total_mcp_uses", 0),
            "total_sessions": totals.get("total_sessions", 0),
            "by_tool": tool_stats,
            "by_server": server_stats
        }

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
