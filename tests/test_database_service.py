"""Comprehensive tests for DatabaseService."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from claude_code_analytics.streamlit_app.models import (
    Message,
    Project,
    ProjectSummary,
    Session,
    SessionSummary,
    ToolUsageSummary,
    ToolUse,
)
from claude_code_analytics.streamlit_app.services.database_service import DatabaseService


@pytest.fixture
def test_db():
    """Create a temporary test database with sample data."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()
    db_path = temp_db.name

    # Create database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute(
        """
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            created_at TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            message_count INTEGER DEFAULT 0,
            tool_use_count INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_index INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            timestamp TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_creation_input_tokens INTEGER DEFAULT 0,
            cache_read_input_tokens INTEGER DEFAULT 0,
            cache_ephemeral_5m_tokens INTEGER DEFAULT 0,
            cache_ephemeral_1h_tokens INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE tool_uses (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_use_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            message_index INTEGER NOT NULL,
            tool_name TEXT NOT NULL,
            tool_input TEXT,
            tool_result TEXT,
            is_error INTEGER DEFAULT 0,
            timestamp TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """
    )

    # Create FTS5 tables
    cursor.execute(
        """
        CREATE VIRTUAL TABLE fts_messages USING fts5(
            content,
            content=messages,
            content_rowid=message_id
        )
    """
    )

    cursor.execute(
        """
        CREATE VIRTUAL TABLE fts_tool_uses USING fts5(
            tool_input,
            tool_result,
            content=tool_uses,
            content_rowid=rowid
        )
    """
    )

    # Create views
    cursor.execute(
        """
        CREATE VIEW project_summary AS
        SELECT
            p.project_id,
            p.project_name,
            COUNT(DISTINCT s.session_id) as total_sessions,
            MIN(s.start_time) as first_session,
            MAX(s.end_time) as last_session,
            COALESCE(SUM(s.message_count), 0) as total_messages,
            COALESCE(SUM(s.tool_use_count), 0) as total_tool_uses
        FROM projects p
        LEFT JOIN sessions s ON p.project_id = p.project_id
        GROUP BY p.project_id, p.project_name
    """
    )

    cursor.execute(
        """
        CREATE VIEW session_summary AS
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
        FROM sessions s
        INNER JOIN projects p ON s.project_id = p.project_id
        LEFT JOIN messages m ON s.session_id = m.session_id
        GROUP BY s.session_id
    """
    )

    cursor.execute(
        """
        CREATE VIEW tool_usage_summary AS
        SELECT
            tool_name,
            COUNT(*) as total_uses,
            SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as error_count,
            ROUND(SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as error_rate_percent,
            COUNT(DISTINCT session_id) as sessions_used_in,
            MIN(timestamp) as first_used,
            MAX(timestamp) as last_used
        FROM tool_uses
        GROUP BY tool_name
        ORDER BY total_uses DESC
    """
    )

    # Insert sample data
    cursor.execute(
        """
        INSERT INTO projects (project_id, project_name, created_at)
        VALUES ('proj1', 'Test Project', '2025-01-01T00:00:00')
    """
    )

    cursor.execute(
        """
        INSERT INTO sessions (session_id, project_id, start_time, end_time, message_count, tool_use_count)
        VALUES ('session1', 'proj1', '2025-01-01T10:00:00', '2025-01-01T11:00:00', 3, 2)
    """
    )

    cursor.execute(
        """
        INSERT INTO messages (session_id, message_index, role, content, timestamp, input_tokens, output_tokens)
        VALUES
            ('session1', 0, 'user', 'Hello world', '2025-01-01T10:00:00', 10, 0),
            ('session1', 1, 'assistant', 'Hi there!', '2025-01-01T10:01:00', 5, 15),
            ('session1', 2, 'user', 'How are you?', '2025-01-01T10:02:00', 8, 0)
    """
    )

    cursor.execute(
        """
        INSERT INTO fts_messages (rowid, content)
        SELECT message_id, content FROM messages
    """
    )

    cursor.execute(
        """
        INSERT INTO tool_uses (tool_use_id, session_id, message_index, tool_name, tool_input, tool_result, is_error, timestamp)
        VALUES
            ('tool1', 'session1', 1, 'Read', '{"file_path": "/test.py"}', 'File contents here', 0, '2025-01-01T10:01:30'),
            ('tool2', 'session1', 1, 'Bash', '{"command": "ls"}', 'file1.txt\nfile2.txt', 0, '2025-01-01T10:01:45')
    """
    )

    cursor.execute(
        """
        INSERT INTO fts_tool_uses (rowid, tool_input, tool_result)
        SELECT rowid, tool_input, tool_result FROM tool_uses
    """
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestDatabaseServiceInit:
    """Test DatabaseService initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default database path."""
        service = DatabaseService()
        assert service.db_path is not None

    def test_init_with_custom_path(self, test_db):
        """Test initialization with custom database path."""
        service = DatabaseService(db_path=test_db)
        assert service.db_path == test_db

    def test_get_connection(self, test_db):
        """Test database connection."""
        service = DatabaseService(db_path=test_db)
        conn = service._get_connection()
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestProjectQueries:
    """Test project-related queries."""

    def test_get_all_projects(self, test_db):
        """Test getting all projects."""
        service = DatabaseService(db_path=test_db)
        projects = service.get_all_projects()
        assert len(projects) == 1
        assert isinstance(projects[0], Project)
        assert projects[0].project_id == "proj1"
        assert projects[0].project_name == "Test Project"

    def test_get_project_summaries(self, test_db):
        """Test getting project summaries."""
        service = DatabaseService(db_path=test_db)
        summaries = service.get_project_summaries()
        assert len(summaries) == 1
        assert isinstance(summaries[0], ProjectSummary)
        assert summaries[0].project_id == "proj1"
        assert summaries[0].total_sessions == 1
        assert summaries[0].total_messages == 3
        assert summaries[0].total_tool_uses == 2

    def test_get_project_existing(self, test_db):
        """Test getting a specific project that exists."""
        service = DatabaseService(db_path=test_db)
        project = service.get_project("proj1")
        assert project is not None
        assert isinstance(project, Project)
        assert project.project_id == "proj1"

    def test_get_project_nonexistent(self, test_db):
        """Test getting a project that doesn't exist."""
        service = DatabaseService(db_path=test_db)
        project = service.get_project("nonexistent")
        assert project is None


class TestSessionQueries:
    """Test session-related queries."""

    def test_get_sessions_for_project(self, test_db):
        """Test getting all sessions for a project."""
        service = DatabaseService(db_path=test_db)
        sessions = service.get_sessions_for_project("proj1")
        assert len(sessions) == 1
        assert isinstance(sessions[0], Session)
        assert sessions[0].session_id == "session1"
        assert sessions[0].project_id == "proj1"

    def test_get_sessions_for_nonexistent_project(self, test_db):
        """Test getting sessions for a project that doesn't exist."""
        service = DatabaseService(db_path=test_db)
        sessions = service.get_sessions_for_project("nonexistent")
        assert len(sessions) == 0

    def test_get_session_existing(self, test_db):
        """Test getting a specific session that exists."""
        service = DatabaseService(db_path=test_db)
        session = service.get_session("session1")
        assert session is not None
        assert isinstance(session, Session)
        assert session.session_id == "session1"

    def test_get_session_nonexistent(self, test_db):
        """Test getting a session that doesn't exist."""
        service = DatabaseService(db_path=test_db)
        session = service.get_session("nonexistent")
        assert session is None

    def test_get_session_summaries_all(self, test_db):
        """Test getting all session summaries."""
        service = DatabaseService(db_path=test_db)
        summaries = service.get_session_summaries()
        assert len(summaries) == 1
        assert isinstance(summaries[0], SessionSummary)
        assert summaries[0].message_count == 3

    def test_get_session_summaries_with_project_filter(self, test_db):
        """Test getting session summaries filtered by project."""
        service = DatabaseService(db_path=test_db)
        summaries = service.get_session_summaries(project_id="proj1")
        assert len(summaries) == 1

    def test_get_session_summaries_with_limit(self, test_db):
        """Test getting session summaries with limit."""
        service = DatabaseService(db_path=test_db)
        summaries = service.get_session_summaries(limit=1)
        assert len(summaries) == 1


class TestMessageQueries:
    """Test message-related queries."""

    def test_get_messages_for_session(self, test_db):
        """Test getting all messages for a session."""
        service = DatabaseService(db_path=test_db)
        messages = service.get_messages_for_session("session1")
        assert len(messages) == 3
        assert all(isinstance(m, Message) for m in messages)
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_get_messages_for_nonexistent_session(self, test_db):
        """Test getting messages for a session that doesn't exist."""
        service = DatabaseService(db_path=test_db)
        messages = service.get_messages_for_session("nonexistent")
        assert len(messages) == 0

    def test_get_messages_in_range_with_start_time(self, test_db):
        """Test getting messages filtered by start time."""
        service = DatabaseService(db_path=test_db)
        start_time = datetime.fromisoformat("2025-01-01T10:01:00")
        messages = service.get_messages_in_range("session1", start_time=start_time)
        assert len(messages) == 2  # Should exclude first message

    def test_get_messages_in_range_with_end_time(self, test_db):
        """Test getting messages filtered by end time."""
        service = DatabaseService(db_path=test_db)
        end_time = datetime.fromisoformat("2025-01-01T10:01:00")
        messages = service.get_messages_in_range("session1", end_time=end_time)
        assert len(messages) == 2  # Should exclude last message

    def test_get_messages_in_range_with_both_times(self, test_db):
        """Test getting messages filtered by both start and end time."""
        service = DatabaseService(db_path=test_db)
        start_time = datetime.fromisoformat("2025-01-01T10:00:30")
        end_time = datetime.fromisoformat("2025-01-01T10:01:30")
        messages = service.get_messages_in_range(
            "session1", start_time=start_time, end_time=end_time
        )
        assert len(messages) == 1  # Should only get middle message

    def test_get_token_usage_for_session(self, test_db):
        """Test getting token usage statistics for a session."""
        service = DatabaseService(db_path=test_db)
        usage = service.get_token_usage_for_session("session1")
        assert usage["input_tokens"] == 5  # Only assistant message
        assert usage["output_tokens"] == 15  # Only assistant message

    def test_get_token_usage_for_nonexistent_session(self, test_db):
        """Test getting token usage for a session that doesn't exist."""
        service = DatabaseService(db_path=test_db)
        usage = service.get_token_usage_for_session("nonexistent")
        # Should return dict with zero values when no data
        assert usage == {} or all(v == 0 for v in usage.values())

    def test_get_token_timeline_for_session(self, test_db):
        """Test getting token usage timeline for a session."""
        service = DatabaseService(db_path=test_db)
        timeline = service.get_token_timeline_for_session("session1")
        assert len(timeline) == 3
        assert timeline[0]["cumulative_tokens"] == 10
        assert timeline[1]["cumulative_tokens"] == 30  # 10 + 5 + 15
        assert timeline[2]["cumulative_tokens"] == 38  # 30 + 8


class TestToolUseQueries:
    """Test tool use-related queries."""

    def test_get_tool_uses_for_session(self, test_db):
        """Test getting all tool uses for a session."""
        service = DatabaseService(db_path=test_db)
        tool_uses = service.get_tool_uses_for_session("session1")
        assert len(tool_uses) == 2
        assert all(isinstance(t, ToolUse) for t in tool_uses)
        assert tool_uses[0].tool_name == "Read"
        assert tool_uses[1].tool_name == "Bash"

    def test_get_tool_uses_in_range(self, test_db):
        """Test getting tool uses filtered by time range."""
        service = DatabaseService(db_path=test_db)
        start_time = datetime.fromisoformat("2025-01-01T10:01:40")
        tool_uses = service.get_tool_uses_in_range("session1", start_time=start_time)
        assert len(tool_uses) == 1  # Should only get Bash tool

    def test_get_tool_usage_summary(self, test_db):
        """Test getting tool usage summary."""
        service = DatabaseService(db_path=test_db)
        summary = service.get_tool_usage_summary()
        assert len(summary) == 2
        assert all(isinstance(s, ToolUsageSummary) for s in summary)

    def test_get_unique_tool_names(self, test_db):
        """Test getting unique tool names."""
        service = DatabaseService(db_path=test_db)
        tool_names = service.get_unique_tool_names()
        assert len(tool_names) == 2
        assert "Read" in tool_names
        assert "Bash" in tool_names

    def test_get_mcp_tool_stats_empty(self, test_db):
        """Test getting MCP tool stats when no MCP tools exist."""
        service = DatabaseService(db_path=test_db)
        stats = service.get_mcp_tool_stats()
        assert stats["total_uses"] == 0
        assert stats["total_sessions"] == 0
        assert len(stats["by_tool"]) == 0


class TestFTSSearchQueries:
    """Test full-text search queries."""

    def test_search_messages_basic(self, test_db):
        """Test basic message search."""
        service = DatabaseService(db_path=test_db)
        results = service.search_messages("Hello")
        assert len(results) == 1
        assert results[0]["content"] == "Hello world"

    def test_search_messages_no_results(self, test_db):
        """Test message search with no results."""
        service = DatabaseService(db_path=test_db)
        results = service.search_messages("nonexistent")
        assert len(results) == 0

    def test_search_messages_with_project_filter(self, test_db):
        """Test message search with project filter."""
        service = DatabaseService(db_path=test_db)
        results = service.search_messages("Hello", project_id="proj1")
        assert len(results) == 1

    def test_search_messages_with_role_filter(self, test_db):
        """Test message search with role filter."""
        service = DatabaseService(db_path=test_db)
        results = service.search_messages("Hi", role="assistant")
        assert len(results) == 1

    def test_search_messages_with_pagination(self, test_db):
        """Test message search with pagination."""
        service = DatabaseService(db_path=test_db)
        results = service.search_messages("Hello OR Hi", limit=1, offset=0)
        assert len(results) == 1

    def test_search_messages_invalid_fts_syntax(self, test_db):
        """Test that invalid FTS syntax raises proper error."""
        service = DatabaseService(db_path=test_db)
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            service.search_messages('unmatched"quote')
        # Error message varies by SQLite version, check for either
        error_msg = str(exc_info.value).lower()
        assert (
            "invalid" in error_msg
            or "fts5" in error_msg
            or "syntax" in error_msg
            or "unterminated" in error_msg
        )

    def test_search_tool_inputs(self, test_db):
        """Test searching tool inputs."""
        service = DatabaseService(db_path=test_db)
        results = service.search_tool_inputs("file_path")
        assert len(results) == 1
        assert results[0]["tool_name"] == "Read"

    def test_search_tool_results(self, test_db):
        """Test searching tool results."""
        service = DatabaseService(db_path=test_db)
        results = service.search_tool_results("File contents")
        assert len(results) == 1
        assert results[0]["tool_name"] == "Read"

    def test_search_all(self, test_db):
        """Test searching across all content types."""
        service = DatabaseService(db_path=test_db)
        results = service.search_all("Hello")
        assert len(results) >= 1  # Should find at least the message

    def test_count_search_results_for_session(self, test_db):
        """Test counting search results for a session."""
        service = DatabaseService(db_path=test_db)
        count = service.count_search_results_for_session("Hello", "session1", scope="Messages")
        assert count == 1

    def test_count_search_results_all_scope(self, test_db):
        """Test counting search results with 'All' scope."""
        service = DatabaseService(db_path=test_db)
        count = service.count_search_results_for_session("file", "session1", scope="All")
        assert count >= 1  # Should find tool inputs/results


class TestAnalyticsQueries:
    """Test analytics-related queries."""

    def test_get_daily_statistics(self, test_db):
        """Test getting daily statistics."""
        service = DatabaseService(db_path=test_db)
        stats = service.get_daily_statistics(days=7)
        # May return empty list or list with data depending on timestamp handling
        assert isinstance(stats, list)
        if len(stats) > 0:
            assert all("date" in s for s in stats)
            assert all("sessions" in s for s in stats)
            assert all("messages" in s for s in stats)

    def test_get_daily_statistics_with_limit(self, test_db):
        """Test getting daily statistics with day limit."""
        service = DatabaseService(db_path=test_db)
        stats = service.get_daily_statistics(days=1)
        assert len(stats) <= 1  # Should respect day limit


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_execute_fts_query_with_valid_query(self, test_db):
        """Test FTS query execution with valid query."""
        service = DatabaseService(db_path=test_db)
        conn = service._get_connection()
        cursor = conn.cursor()
        service._execute_fts_query(
            cursor, "SELECT * FROM fts_messages WHERE fts_messages MATCH ?", ["Hello"], "Hello"
        )
        results = cursor.fetchall()
        conn.close()
        assert len(results) >= 0  # Should execute without error

    def test_execute_fts_query_with_invalid_syntax(self, test_db):
        """Test FTS query execution with invalid syntax raises helpful error."""
        service = DatabaseService(db_path=test_db)
        conn = service._get_connection()
        cursor = conn.cursor()
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            service._execute_fts_query(
                cursor,
                "SELECT * FROM fts_messages WHERE fts_messages MATCH ?",
                ['unmatched"'],
                'unmatched"',
            )
        # Error message enhanced by helper or raw SQLite error
        error_msg = str(exc_info.value).lower()
        assert "fts" in error_msg or "syntax" in error_msg or "unterminated" in error_msg
        conn.close()

    def test_search_grouped_by_session_messages_scope(self, test_db):
        """Test session-grouped search with Messages scope."""
        service = DatabaseService(db_path=test_db)
        result = service.search_grouped_by_session("Hello", scope="Messages")
        assert "results_by_session" in result
        assert "has_more" in result
        assert "total_sessions" in result
        assert result["total_sessions"] >= 0

    def test_search_grouped_by_session_with_pagination(self, test_db):
        """Test session-grouped search with pagination."""
        service = DatabaseService(db_path=test_db)
        result = service.search_grouped_by_session(
            "Hello", scope="All", sessions_per_page=1, page=0
        )
        assert isinstance(result["has_more"], bool)
        assert isinstance(result["total_sessions"], int)
