"""Tests for import service SQLite thread safety (Fixes #13)."""

import asyncio
import sqlite3
import threading
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from claude_code_analytics.api.services.import_service import (
    import_single_session,
    run_import,
)


@pytest.fixture
def db_with_schema(tmp_path):
    """Create a temporary database with the required schema."""
    db_path = str(tmp_path / "test.db")
    from claude_code_analytics.scripts.create_database import create_database

    create_database(db_path)
    return db_path


@pytest.fixture
def sample_session_file(tmp_path):
    """Create a minimal valid JSONL session file."""
    import json

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    session_file = project_dir / "test-session-123.jsonl"
    entries = [
        {
            "ts": "2024-01-01T00:00:00Z",
            "message": {
                "role": "user",
                "content": "Hello",
                "usage": {},
            },
        },
        {
            "ts": "2024-01-01T00:01:00Z",
            "message": {
                "role": "assistant",
                "content": "Hi there!",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        },
    ]
    session_file.write_text("\n".join(json.dumps(e) for e in entries))
    return session_file


class TestImportServiceThreadSafety:
    """Verify SQLite connections are created in the same thread that uses them."""

    def test_import_single_session_creates_own_connection(
        self, db_with_schema, sample_session_file
    ):
        """import_single_session creates its own connection, safe for executor use."""
        # Run in a different thread (simulating run_in_executor)
        result_holder = {}
        errors = []

        def run_in_thread():
            try:
                result = import_single_session(sample_session_file, db_path=db_with_schema)
                result_holder["result"] = result
            except sqlite3.ProgrammingError as e:
                errors.append(str(e))

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=10)

        assert not errors, f"SQLite threading error: {errors}"
        assert result_holder.get("result") is not None
        messages, tool_uses = result_holder["result"]
        assert messages == 2
        assert tool_uses == 0

    def test_run_import_creates_connection_in_thread(self, db_with_schema, tmp_path):
        """run_import should not pass SQLite connections across thread boundaries."""
        import json

        # Create a project dir with a session file
        project_dir = tmp_path / "projects" / "test-project"
        project_dir.mkdir(parents=True)
        session_file = project_dir / "test-session.jsonl"
        entries = [
            {
                "ts": "2024-01-01T00:00:00Z",
                "message": {
                    "role": "user",
                    "content": "Test message",
                    "usage": {},
                },
            },
        ]
        session_file.write_text("\n".join(json.dumps(e) for e in entries))

        event_bus = AsyncMock()

        # Patch config to point to our test dirs
        import claude_code_analytics.config as config_mod

        original_projects_dir = config_mod.CLAUDE_CODE_PROJECTS_DIR
        original_db_path = config_mod.DATABASE_PATH
        try:
            config_mod.CLAUDE_CODE_PROJECTS_DIR = tmp_path / "projects"
            config_mod.DATABASE_PATH = Path(db_with_schema)

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(run_import(event_bus, db_path=db_with_schema))
                # Should complete without SQLite threading errors
                assert result["sessions"] >= 0
            finally:
                loop.close()
        finally:
            config_mod.CLAUDE_CODE_PROJECTS_DIR = original_projects_dir
            config_mod.DATABASE_PATH = original_db_path
