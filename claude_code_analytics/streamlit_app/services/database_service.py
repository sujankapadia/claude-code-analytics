"""Database service layer for conversation analytics."""

import sqlite3
from datetime import datetime
from typing import Any, Optional

# Add parent directory to path for imports
from claude_code_analytics import config
from claude_code_analytics.streamlit_app.models import (
    Message,
    Project,
    ProjectSummary,
    Session,
    SessionSummary,
    ToolUsageSummary,
    ToolUse,
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

    def _execute_fts_query(
        self, cursor: sqlite3.Cursor, sql: str, params: list, query_text: str
    ) -> None:
        """
        Execute an FTS5 query with proper error handling.

        Args:
            cursor: Database cursor
            sql: SQL query string
            params: Query parameters
            query_text: The user-supplied FTS query text (for error messages)

        Raises:
            sqlite3.OperationalError: If FTS5 query syntax is invalid
        """
        try:
            cursor.execute(sql, params)
        except sqlite3.OperationalError as e:
            # FTS5 syntax error - provide helpful message
            error_str = str(e).lower()
            if "fts5" in error_str or "syntax error" in error_str:
                raise sqlite3.OperationalError(
                    f"Invalid FTS5 query syntax: {e}\n"
                    f"Query: '{query_text}'\n"
                    f"Tip: Check for unmatched quotes, invalid operators, or special characters"
                ) from e
            raise

    # =========================================================================
    # Project queries
    # =========================================================================

    def get_all_projects(self) -> list[Project]:
        """Get all projects."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY project_name")
        rows = cursor.fetchall()
        conn.close()
        return [Project(**dict(row)) for row in rows]

    def get_project_summaries(self) -> list[ProjectSummary]:
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

    def get_sessions_for_project(self, project_id: str) -> list[Session]:
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
    ) -> list[SessionSummary]:
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

    def get_messages_for_session(self, session_id: str) -> list[Message]:
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
        end_time: Optional[datetime] = None,
    ) -> list[Message]:
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

    def get_token_usage_for_session(self, session_id: str) -> dict[str, int]:
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

    def get_token_timeline_for_session(self, session_id: str) -> list[dict[str, Any]]:
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

            timeline.append(
                {
                    "timestamp": row["timestamp"],
                    "cumulative_tokens": cumulative_tokens,
                    "input_tokens": input_tok,
                    "output_tokens": output_tok,
                }
            )

        return timeline

    # =========================================================================
    # Tool use queries
    # =========================================================================

    def get_tool_uses_for_session(self, session_id: str) -> list[ToolUse]:
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
        end_time: Optional[datetime] = None,
    ) -> list[ToolUse]:
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

    def get_tool_usage_summary(self) -> list[ToolUsageSummary]:
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
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Search messages using FTS5 full-text search.

        Args:
            query: Search query (user-supplied, may contain FTS5 operators)
            project_id: Optional filter by project
            role: Optional filter by role (user/assistant)
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching messages with context

        Raises:
            sqlite3.OperationalError: If FTS5 query syntax is invalid
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

        self._execute_fts_query(cursor, sql, params, query)
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
        offset: int = 0,
    ) -> list[dict[str, Any]]:
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

        self._execute_fts_query(cursor, sql, params, query)
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
        offset: int = 0,
    ) -> list[dict[str, Any]]:
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

        self._execute_fts_query(cursor, sql, params, query)
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
        offset: int = 0,
    ) -> list[dict[str, Any]]:
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
                    snippet(fts_messages, -1, '<mark>', '</mark>', '...', 64) as snippet,
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
                    NULL as snippet,
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
                    NULL as snippet,
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

        self._execute_fts_query(cursor, sql, params, query)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def count_search_results_for_session(
        self,
        query: str,
        session_id: str,
        scope: str = "All",
        tool_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """
        Count total search results for a specific session.

        Args:
            query: Search query
            session_id: Session to count results for
            scope: Search scope (All, Messages, Tool Inputs, Tool Results)
            tool_name: Optional tool name filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Total count of matches in this session
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if scope == "Messages":
            sql = """
                SELECT COUNT(*) as count
                FROM fts_messages
                JOIN messages m ON fts_messages.rowid = m.message_id
                WHERE fts_messages MATCH ? AND m.session_id = ?
            """
            params = [query, session_id]

            if start_date:
                sql += " AND m.timestamp >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND m.timestamp <= ?"
                params.append(end_date)

        elif scope == "Tool Inputs":
            sql = """
                SELECT COUNT(*) as count
                FROM fts_tool_uses
                JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                WHERE fts_tool_uses MATCH 'tool_input:' || ? AND t.session_id = ?
            """
            params = [query, session_id]

            if tool_name:
                sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                params.append(end_date)

        elif scope == "Tool Results":
            sql = """
                SELECT COUNT(*) as count
                FROM fts_tool_uses
                JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                WHERE fts_tool_uses MATCH 'tool_result:' || ? AND t.session_id = ?
            """
            params = [query, session_id]

            if tool_name:
                sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                params.append(end_date)

        else:  # All
            sql = """
                SELECT COUNT(*) as count FROM (
                    SELECT m.session_id
                    FROM fts_messages
                    JOIN messages m ON fts_messages.rowid = m.message_id
                    WHERE fts_messages MATCH ? AND m.session_id = ?
            """
            params = [query, session_id]

            if start_date:
                sql += " AND m.timestamp >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND m.timestamp <= ?"
                params.append(end_date)

            sql += """
                    UNION ALL
                    SELECT t.session_id
                    FROM fts_tool_uses
                    JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                    WHERE fts_tool_uses MATCH 'tool_input:' || ? AND t.session_id = ?
            """
            params.extend([query, session_id])

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
                    SELECT t.session_id
                    FROM fts_tool_uses
                    JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                    WHERE fts_tool_uses MATCH 'tool_result:' || ? AND t.session_id = ?
            """
            params.extend([query, session_id])

            if tool_name:
                sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                params.append(end_date)

            sql += ")"

        self._execute_fts_query(cursor, sql, params, query)
        result = cursor.fetchone()
        conn.close()

        return result["count"] if result else 0

    def search_grouped_by_session(
        self,
        query: str,
        scope: str = "All",
        project_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sessions_per_page: int = 3,
        page: int = 0,
    ) -> dict[str, Any]:
        """
        Search with results grouped by session, paginated by sessions.

        Args:
            query: Search query
            scope: Search scope (All, Messages, Tool Inputs, Tool Results)
            project_id: Optional filter by project
            tool_name: Optional filter by tool name
            start_date: Optional start date filter
            end_date: Optional end date filter
            sessions_per_page: Number of sessions to show per page
            page: Page number (0-indexed)

        Returns:
            Dictionary with:
                - results_by_session: Dict[session_id, List[results]]
                - has_more: bool indicating if there are more pages
                - total_sessions: Total number of sessions with matches
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Step 1: Get session IDs for this page
        if scope == "Messages":
            session_sql = """
                SELECT
                    m.session_id,
                    MAX(m.timestamp) as latest_match
                FROM fts_messages
                JOIN messages m ON fts_messages.rowid = m.message_id
                JOIN sessions s ON m.session_id = s.session_id
                WHERE fts_messages MATCH ?
            """
            params = [query]

            if project_id:
                session_sql += " AND s.project_id = ?"
                params.append(project_id)
            if start_date:
                session_sql += " AND m.timestamp >= ?"
                params.append(start_date)
            if end_date:
                session_sql += " AND m.timestamp <= ?"
                params.append(end_date)

            # Add GROUP BY for Messages scope
            session_sql += "\n            GROUP BY m.session_id"

        elif scope == "Tool Inputs":
            session_sql = """
                SELECT
                    t.session_id,
                    MAX(t.timestamp) as latest_match
                FROM fts_tool_uses
                JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                JOIN sessions s ON t.session_id = s.session_id
                WHERE fts_tool_uses MATCH 'tool_input:' || ?
            """
            params = [query]

            if project_id:
                session_sql += " AND s.project_id = ?"
                params.append(project_id)
            if tool_name:
                session_sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                session_sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                session_sql += " AND t.timestamp <= ?"
                params.append(end_date)

            # Add GROUP BY for Tool Inputs scope
            session_sql += "\n            GROUP BY t.session_id"

        elif scope == "Tool Results":
            session_sql = """
                SELECT
                    t.session_id,
                    MAX(t.timestamp) as latest_match
                FROM fts_tool_uses
                JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                JOIN sessions s ON t.session_id = s.session_id
                WHERE fts_tool_uses MATCH 'tool_result:' || ?
            """
            params = [query]

            if project_id:
                session_sql += " AND s.project_id = ?"
                params.append(project_id)
            if tool_name:
                session_sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                session_sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                session_sql += " AND t.timestamp <= ?"
                params.append(end_date)

            # Add GROUP BY for Tool Results scope
            session_sql += "\n            GROUP BY t.session_id"

        else:  # All - union of all types
            session_sql = """
                SELECT session_id, MAX(latest_match) as latest_match
                FROM (
                    SELECT m.session_id, m.timestamp as latest_match
                    FROM fts_messages
                    JOIN messages m ON fts_messages.rowid = m.message_id
                    JOIN sessions s ON m.session_id = s.session_id
                    WHERE fts_messages MATCH ?
            """
            params = [query]

            if project_id:
                session_sql += " AND s.project_id = ?"
                params.append(project_id)
            if start_date:
                session_sql += " AND m.timestamp >= ?"
                params.append(start_date)
            if end_date:
                session_sql += " AND m.timestamp <= ?"
                params.append(end_date)

            session_sql += """
                    UNION ALL
                    SELECT t.session_id, t.timestamp as latest_match
                    FROM fts_tool_uses
                    JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                    JOIN sessions s ON t.session_id = s.session_id
                    WHERE fts_tool_uses MATCH 'tool_input:' || ?
            """
            params.append(query)

            if project_id:
                session_sql += " AND s.project_id = ?"
                params.append(project_id)
            if tool_name:
                session_sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                session_sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                session_sql += " AND t.timestamp <= ?"
                params.append(end_date)

            session_sql += """
                    UNION ALL
                    SELECT t.session_id, t.timestamp as latest_match
                    FROM fts_tool_uses
                    JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                    JOIN sessions s ON t.session_id = s.session_id
                    WHERE fts_tool_uses MATCH 'tool_result:' || ?
            """
            params.append(query)

            if project_id:
                session_sql += " AND s.project_id = ?"
                params.append(project_id)
            if tool_name:
                session_sql += " AND t.tool_name = ?"
                params.append(tool_name)
            if start_date:
                session_sql += " AND t.timestamp >= ?"
                params.append(start_date)
            if end_date:
                session_sql += " AND t.timestamp <= ?"
                params.append(end_date)

            session_sql += """
                )
                GROUP BY session_id
            """

        # Add ordering and pagination
        session_sql += """
            ORDER BY latest_match DESC
            LIMIT ? OFFSET ?
        """
        offset = page * sessions_per_page
        params.extend([sessions_per_page + 1, offset])  # Get one extra to check for more pages

        self._execute_fts_query(cursor, session_sql, params, query)
        session_rows = cursor.fetchall()

        # Check if there are more pages
        has_more = len(session_rows) > sessions_per_page
        session_ids = [row["session_id"] for row in session_rows[:sessions_per_page]]

        # Get total session count (without pagination)
        total_sql = session_sql.replace("LIMIT ? OFFSET ?", "")
        total_params = params[:-2]  # Remove the limit/offset params
        self._execute_fts_query(
            cursor, f"SELECT COUNT(*) as total FROM ({total_sql})", total_params, query
        )
        total_sessions = cursor.fetchone()["total"]

        if not session_ids:
            conn.close()
            return {"results_by_session": {}, "has_more": False, "total_sessions": 0}

        # Step 2: Get all results for these specific sessions
        results_by_session = {}
        placeholders = ",".join("?" * len(session_ids))

        if scope == "Messages":
            # Custom query to filter by session_ids
            sql = f"""
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
                WHERE fts_messages MATCH ? AND m.session_id IN ({placeholders})
            """
            result_params = [query] + session_ids

            if project_id:
                sql += " AND s.project_id = ?"
                result_params.append(project_id)
            if start_date:
                sql += " AND m.timestamp >= ?"
                result_params.append(start_date)
            if end_date:
                sql += " AND m.timestamp <= ?"
                result_params.append(end_date)

            sql += " ORDER BY m.timestamp DESC"
            self._execute_fts_query(cursor, sql, result_params, query)
            results = [dict(row) for row in cursor.fetchall()]

            for result in results:
                if result["session_id"] not in results_by_session:
                    results_by_session[result["session_id"]] = []
                results_by_session[result["session_id"]].append(result)

        elif scope == "Tool Inputs":
            # Custom query to filter by session_ids
            sql = f"""
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
                WHERE fts_tool_uses MATCH 'tool_input:' || ? AND t.session_id IN ({placeholders})
            """
            result_params = [query] + session_ids

            if project_id:
                sql += " AND s.project_id = ?"
                result_params.append(project_id)
            if tool_name:
                sql += " AND t.tool_name = ?"
                result_params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                result_params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                result_params.append(end_date)

            sql += " ORDER BY t.timestamp DESC"
            self._execute_fts_query(cursor, sql, result_params, query)
            results = [dict(row) for row in cursor.fetchall()]

            for result in results:
                if result["session_id"] not in results_by_session:
                    results_by_session[result["session_id"]] = []
                results_by_session[result["session_id"]].append(result)

        elif scope == "Tool Results":
            # Custom query to filter by session_ids
            sql = f"""
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
                WHERE fts_tool_uses MATCH 'tool_result:' || ? AND t.session_id IN ({placeholders})
            """
            result_params = [query] + session_ids

            if project_id:
                sql += " AND s.project_id = ?"
                result_params.append(project_id)
            if tool_name:
                sql += " AND t.tool_name = ?"
                result_params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                result_params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                result_params.append(end_date)

            sql += " ORDER BY t.timestamp DESC"
            self._execute_fts_query(cursor, sql, result_params, query)
            results = [dict(row) for row in cursor.fetchall()]

            for result in results:
                if result["session_id"] not in results_by_session:
                    results_by_session[result["session_id"]] = []
                results_by_session[result["session_id"]].append(result)

        else:  # All
            # Custom UNION query to filter by session_ids
            sql = f"""
                SELECT * FROM (
                    -- Messages
                    SELECT
                        m.session_id,
                        m.message_index,
                        'message' as result_type,
                        m.role as detail,
                        m.content as matched_content,
                        snippet(fts_messages, -1, '<mark>', '</mark>', '...', 64) as snippet,
                        m.timestamp,
                        s.project_id,
                        p.project_name
                    FROM fts_messages
                    JOIN messages m ON fts_messages.rowid = m.message_id
                    JOIN sessions s ON m.session_id = s.session_id
                    JOIN projects p ON s.project_id = p.project_id
                    WHERE fts_messages MATCH ? AND m.session_id IN ({placeholders})
            """
            result_params = [query] + session_ids

            if project_id:
                sql += " AND s.project_id = ?"
                result_params.append(project_id)
            if start_date:
                sql += " AND m.timestamp >= ?"
                result_params.append(start_date)
            if end_date:
                sql += " AND m.timestamp <= ?"
                result_params.append(end_date)

            sql += """
                    UNION ALL

                    -- Tool inputs
                    SELECT
                        t.session_id,
                        t.message_index,
                        'tool_input' as result_type,
                        t.tool_name as detail,
                        t.tool_input as matched_content,
                        NULL as snippet,
                        t.timestamp,
                        s.project_id,
                        p.project_name
                    FROM fts_tool_uses
                    JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                    JOIN sessions s ON t.session_id = s.session_id
                    JOIN projects p ON s.project_id = p.project_id
                    WHERE fts_tool_uses MATCH 'tool_input:' || ?
            """
            sql += f" AND t.session_id IN ({placeholders})"
            result_params.append(query)
            result_params.extend(session_ids)

            if project_id:
                sql += " AND s.project_id = ?"
                result_params.append(project_id)
            if tool_name:
                sql += " AND t.tool_name = ?"
                result_params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                result_params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                result_params.append(end_date)

            sql += """
                    UNION ALL

                    -- Tool results
                    SELECT
                        t.session_id,
                        t.message_index,
                        'tool_result' as result_type,
                        t.tool_name as detail,
                        t.tool_result as matched_content,
                        NULL as snippet,
                        t.timestamp,
                        s.project_id,
                        p.project_name
                    FROM fts_tool_uses
                    JOIN tool_uses t ON fts_tool_uses.rowid = t.rowid
                    JOIN sessions s ON t.session_id = s.session_id
                    JOIN projects p ON s.project_id = p.project_id
                    WHERE fts_tool_uses MATCH 'tool_result:' || ?
            """
            sql += f" AND t.session_id IN ({placeholders})"
            result_params.append(query)
            result_params.extend(session_ids)

            if project_id:
                sql += " AND s.project_id = ?"
                result_params.append(project_id)
            if tool_name:
                sql += " AND t.tool_name = ?"
                result_params.append(tool_name)
            if start_date:
                sql += " AND t.timestamp >= ?"
                result_params.append(start_date)
            if end_date:
                sql += " AND t.timestamp <= ?"
                result_params.append(end_date)

            sql += """
                )
                ORDER BY timestamp DESC
            """
            self._execute_fts_query(cursor, sql, result_params, query)
            results = [dict(row) for row in cursor.fetchall()]

            for result in results:
                if result["session_id"] not in results_by_session:
                    results_by_session[result["session_id"]] = []
                results_by_session[result["session_id"]].append(result)

        # Sort results within each session by timestamp
        for session_id in results_by_session:
            results_by_session[session_id].sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        conn.close()

        return {
            "results_by_session": results_by_session,
            "has_more": has_more,
            "total_sessions": total_sessions,
        }

    def get_unique_tool_names(self) -> list[str]:
        """Get list of all tool names used."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT tool_name FROM tool_uses ORDER BY tool_name")
        rows = cursor.fetchall()
        conn.close()
        return [row["tool_name"] for row in rows]

    def get_mcp_tool_stats(self) -> dict[str, Any]:
        """Get MCP tool usage statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get MCP tool usage by tool name
        cursor.execute(
            """
            SELECT
                tool_name,
                COUNT(*) as use_count,
                COUNT(DISTINCT session_id) as session_count
            FROM tool_uses
            WHERE tool_name LIKE 'mcp__%'
            GROUP BY tool_name
            ORDER BY use_count DESC
        """
        )
        tool_stats = [dict(row) for row in cursor.fetchall()]

        # Get MCP by server (extract server from tool name)
        cursor.execute(
            """
            SELECT
                SUBSTR(tool_name, 1, INSTR(SUBSTR(tool_name, 6), '__') + 4) as mcp_server,
                COUNT(*) as total_uses,
                COUNT(DISTINCT session_id) as session_count
            FROM tool_uses
            WHERE tool_name LIKE 'mcp__%'
            GROUP BY mcp_server
            ORDER BY total_uses DESC
        """
        )
        server_stats = [dict(row) for row in cursor.fetchall()]

        # Get total MCP uses
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_mcp_uses,
                COUNT(DISTINCT session_id) as total_sessions
            FROM tool_uses
            WHERE tool_name LIKE 'mcp__%'
        """
        )
        totals = dict(cursor.fetchone())

        conn.close()

        return {
            "total_uses": totals.get("total_mcp_uses", 0),
            "total_sessions": totals.get("total_sessions", 0),
            "by_tool": tool_stats,
            "by_server": server_stats,
        }

    # =========================================================================
    # Analytics queries
    # =========================================================================

    def get_daily_statistics(self, days: int = 30) -> list[dict[str, Any]]:
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
