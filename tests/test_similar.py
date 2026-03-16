"""Tests for session similarity search endpoint (similar.py)."""

import sqlite3
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from claude_code_analytics.api.routers.similar import (
    _fts_session_search,
    _rrf_fusion,
)

# --- Fixtures ---


def _make_message_hit(session_id, message_index, content="test", project_name="proj"):
    return {
        "session_id": session_id,
        "message_index": message_index,
        "content": content,
        "snippet": content,
        "project_name": project_name,
        "role": "user",
        "timestamp": "2024-01-01T00:00:00Z",
    }


def _make_tool_hit(
    session_id, message_index, tool_name="Bash", tool_input="echo hi", project_name="proj"
):
    return {
        "session_id": session_id,
        "message_index": message_index,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "project_name": project_name,
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_db():
    """Mock DatabaseService with configurable search results."""
    db = MagicMock()
    db.search_messages.return_value = []
    db.search_tool_inputs.return_value = []
    db.get_session_summaries.return_value = []
    return db


@pytest.fixture
def client(mock_db):
    """Test client with mocked dependencies."""
    from claude_code_analytics.api.dependencies import get_db_service, get_embedding_service
    from claude_code_analytics.api.routers.similar import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db_service] = lambda: mock_db
    app.dependency_overrides[get_embedding_service] = lambda: None  # FTS-only for these tests

    yield TestClient(app)

    app.dependency_overrides.clear()


# --- TestFTSSessionSearch ---


class TestFTSSessionSearch:
    """Tests for _fts_session_search aggregation logic."""

    def test_aggregates_message_hits_by_session(self, mock_db):
        """F1: Message hits grouped by session with 1.0 weight."""
        mock_db.search_messages.return_value = [
            _make_message_hit("sess-a", 0, "first match"),
            _make_message_hit("sess-a", 5, "second match"),
            _make_message_hit("sess-b", 3, "other session"),
        ]
        result = _fts_session_search(mock_db, "test")

        assert len(result) == 2
        assert result["sess-a"]["hits"] == 2
        assert result["sess-a"]["score"] == 2.0  # 2 * 1.0
        assert result["sess-b"]["hits"] == 1
        assert result["sess-b"]["score"] == 1.0

    def test_aggregates_tool_input_hits_by_session(self, mock_db):
        """F2: Tool input hits weighted at 1.5x."""
        mock_db.search_tool_inputs.return_value = [
            _make_tool_hit("sess-a", 10),
            _make_tool_hit("sess-a", 20),
        ]
        result = _fts_session_search(mock_db, "test")

        assert result["sess-a"]["hits"] == 2
        assert result["sess-a"]["score"] == 3.0  # 2 * 1.5

    def test_combines_message_and_tool_hits(self, mock_db):
        """F3: Same session gets combined score from both scopes."""
        mock_db.search_messages.return_value = [
            _make_message_hit("sess-a", 0),
        ]
        mock_db.search_tool_inputs.return_value = [
            _make_tool_hit("sess-a", 5),
        ]
        result = _fts_session_search(mock_db, "test")

        assert len(result) == 1
        assert result["sess-a"]["hits"] == 2
        assert result["sess-a"]["score"] == 2.5  # 1.0 + 1.5

    def test_handles_fts_error_gracefully(self, mock_db):
        """F4: OperationalError on messages still returns tool results."""
        mock_db.search_messages.side_effect = sqlite3.OperationalError("fts error")
        mock_db.search_tool_inputs.return_value = [
            _make_tool_hit("sess-a", 10),
        ]
        result = _fts_session_search(mock_db, "test")

        assert len(result) == 1
        assert result["sess-a"]["hits"] == 1

    def test_handles_both_fts_errors(self, mock_db):
        """F5: Both scopes fail, returns empty."""
        mock_db.search_messages.side_effect = sqlite3.OperationalError("fts error")
        mock_db.search_tool_inputs.side_effect = sqlite3.OperationalError("fts error")

        result = _fts_session_search(mock_db, "test")
        assert result == {}

    def test_strips_html_from_snippets(self, mock_db):
        """F6: HTML tags removed from match text."""
        hit = _make_message_hit("sess-a", 0)
        hit["snippet"] = "found <mark>pagination</mark> here"
        mock_db.search_messages.return_value = [hit]

        result = _fts_session_search(mock_db, "test")

        match_text = result["sess-a"]["matches"][0]["text"]
        assert "<mark>" not in match_text
        assert "pagination" in match_text


# --- TestRRFFusion ---


class TestRRFFusion:
    """Tests for RRF fusion ranking."""

    def test_ranks_by_score(self):
        """R1: Sessions ranked by RRF score descending."""
        fts = {
            "sess-a": {"score": 10},
            "sess-b": {"score": 5},
            "sess-c": {"score": 1},
        }
        ranked = _rrf_fusion(fts)

        sids = [sid for sid, _ in ranked]
        assert sids == ["sess-a", "sess-b", "sess-c"]

    def test_fts_only(self):
        """R2: Works with FTS only, no semantic."""
        fts = {"sess-a": {"score": 5}}
        ranked = _rrf_fusion(fts, semantic_results=None)

        assert len(ranked) == 1
        assert ranked[0][0] == "sess-a"
        assert ranked[0][1] > 0

    def test_session_in_both_lists_ranks_higher(self):
        """R3: Session in both FTS and semantic gets boosted score."""
        fts = {
            "sess-a": {"score": 5},
            "sess-b": {"score": 5},
        }
        semantic = {
            "sess-a": {"best": 0.8},
        }
        ranked = _rrf_fusion(fts, semantic)

        # sess-a should rank higher (in both lists)
        sids = [sid for sid, _ in ranked]
        assert sids[0] == "sess-a"
        # sess-a score should be higher than sess-b
        scores = dict(ranked)
        assert scores["sess-a"] > scores["sess-b"]

    def test_empty_inputs(self):
        """R4: Empty inputs return empty list."""
        assert _rrf_fusion({}) == []
        assert _rrf_fusion({}, {}) == []


# --- TestSimilarEndpoint ---


class TestSimilarEndpoint:
    """Tests for the /sessions/similar endpoint."""

    def test_returns_results_for_valid_query(self, mock_db, client):
        """E1: Valid query returns session results."""
        mock_db.search_messages.return_value = [
            _make_message_hit("sess-a", 0, "pagination results"),
        ]
        response = client.get("/api/search/sessions?q=pagination")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "pagination"
        assert len(data["results"]) == 1
        assert data["results"][0]["session_id"] == "sess-a"
        assert len(data["results"][0]["sample_matches"]) > 0

    def test_rejects_short_query(self, client):
        """E2: Query under 2 chars returns 400."""
        response = client.get("/api/search/sessions?q=a")
        assert response.status_code == 400

    def test_exclude_session(self, mock_db, client):
        """E3: Excluded session filtered from results."""
        mock_db.search_messages.return_value = [
            _make_message_hit("sess-a", 0),
            _make_message_hit("sess-b", 0),
        ]
        response = client.get("/api/search/sessions?q=test&exclude_session=sess-a")

        data = response.json()
        sids = [r["session_id"] for r in data["results"]]
        assert "sess-a" not in sids
        assert "sess-b" in sids

    def test_limit_parameter(self, mock_db, client):
        """E4: Limit caps result count."""
        mock_db.search_messages.return_value = [_make_message_hit(f"sess-{i}", 0) for i in range(5)]
        response = client.get("/api/search/sessions?q=test&limit=2")

        data = response.json()
        assert len(data["results"]) == 2
        assert data["total_sessions"] == 5

    def test_no_matches(self, mock_db, client):
        """E5: No matches returns empty results."""
        response = client.get("/api/search/sessions?q=xyznonexistent")

        data = response.json()
        assert response.status_code == 200
        assert data["results"] == []
        assert data["total_sessions"] == 0

    def test_sample_matches_deduped(self, mock_db, client):
        """E6: Duplicate message_index within a session is deduped."""
        # Same message_index from both message and tool scopes
        mock_db.search_messages.return_value = [
            _make_message_hit("sess-a", 5, "message match"),
        ]
        mock_db.search_tool_inputs.return_value = [
            _make_tool_hit("sess-a", 5, tool_input="tool match"),
        ]
        response = client.get("/api/search/sessions?q=test")

        data = response.json()
        matches = data["results"][0]["sample_matches"]
        indices = [m["message_index"] for m in matches]
        assert len(indices) == len(set(indices))  # no duplicates
