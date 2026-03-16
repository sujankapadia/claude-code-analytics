"""Tests for EmbeddingService (ChromaDB message-level embeddings)."""

from unittest.mock import MagicMock

import chromadb
import pytest

from claude_code_analytics.services.embedding_service import EmbeddingService

_test_counter = 0


class InMemoryEmbeddingService(EmbeddingService):
    """EmbeddingService using in-memory ChromaDB for testing."""

    def __init__(self):
        global _test_counter
        _test_counter += 1
        self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=f"test_messages_{_test_counter}",
            metadata={"hnsw:space": "cosine"},
        )


@pytest.fixture
def svc():
    """Create an in-memory EmbeddingService with isolated collection."""
    return InMemoryEmbeddingService()


def _make_messages(*texts, start_index=0):
    """Create user message dicts for testing."""
    return [
        {"role": "user", "content": text, "message_index": start_index + i}
        for i, text in enumerate(texts)
    ]


# --- TestEmbedSession ---


class TestEmbedSession:
    """Tests for embed_session."""

    def test_embeds_user_messages(self, svc):
        """E1: User messages >20 chars are embedded."""
        messages = _make_messages(
            "How do I set up a database for this project?",
            "Can you add pagination to the API endpoint?",
            "Please deploy this to production on AWS.",
        )
        count = svc.embed_session("sess-1", messages, "my-project")

        assert count == 3
        assert svc.collection_count() == 3

    def test_skips_non_user_roles(self, svc):
        """E2: Only user messages embedded."""
        messages = [
            {"role": "user", "content": "How do I set up a database?", "message_index": 0},
            {
                "role": "assistant",
                "content": "Here's how to set up a database...",
                "message_index": 1,
            },
            {"role": "user", "content": "Can you add pagination to the API?", "message_index": 2},
        ]
        count = svc.embed_session("sess-1", messages, "proj")

        assert count == 2
        assert svc.collection_count() == 2

    def test_skips_short_messages(self, svc):
        """E3: Messages under 20 chars are skipped."""
        messages = [
            {"role": "user", "content": "Yes", "message_index": 0},
            {"role": "user", "content": "ok", "message_index": 1},
            {
                "role": "user",
                "content": "This is a real question about databases",
                "message_index": 2,
            },
        ]
        count = svc.embed_session("sess-1", messages, "proj")

        assert count == 1

    def test_skips_compaction_messages(self, svc):
        """E4: Compaction messages are skipped."""
        messages = [
            {
                "role": "user",
                "content": "This session is being continued from a previous conversation that ran out of context.",
                "message_index": 0,
            },
            {
                "role": "user",
                "content": "Now let's work on the pagination feature",
                "message_index": 1,
            },
        ]
        count = svc.embed_session("sess-1", messages, "proj")

        assert count == 1

    def test_upsert_no_duplicates(self, svc):
        """E5: Re-embedding same session doesn't create duplicates."""
        messages = _make_messages("How do I set up a database for this project?")

        svc.embed_session("sess-1", messages, "proj")
        assert svc.collection_count() == 1

        svc.embed_session("sess-1", messages, "proj")
        assert svc.collection_count() == 1


# --- TestSearch ---


class TestSearch:
    """Tests for semantic search."""

    def test_finds_similar_messages(self, svc):
        """S1: Finds semantically similar messages."""
        svc.embed_session(
            "sess-1",
            _make_messages("How do I deploy this application to production?"),
            "my-project",
        )
        svc.embed_session(
            "sess-2",
            _make_messages("Set up the CI/CD pipeline for automated deployments"),
            "other-project",
        )

        results = svc.search("deploying to production")

        assert len(results) > 0
        assert all(r["similarity"] > 0.2 for r in results)
        assert all("session_id" in r for r in results)

    def test_empty_collection(self, svc):
        """S2: Search on empty collection returns empty list."""
        results = svc.search("anything")
        assert results == []

    def test_result_fields(self, svc):
        """S3: Results have all required fields."""
        svc.embed_session(
            "sess-1",
            _make_messages("Implement pagination for the search results page"),
            "my-project",
        )
        results = svc.search("pagination")

        assert len(results) > 0
        hit = results[0]
        assert "session_id" in hit
        assert "message_index" in hit
        assert "similarity" in hit
        assert "text" in hit
        assert "project" in hit


# --- TestSearchExpanded ---


class TestSearchExpanded:
    """Tests for expanded search."""

    def test_deduplicates_results(self, svc):
        """X1: Results deduplicated by doc_id, best similarity kept."""
        svc.embed_session(
            "sess-1",
            _make_messages("How do I deploy this to production?"),
            "proj",
        )

        results = svc.search_expanded(
            "deploy",
            ["deploying to production", "shipping code to prod"],
        )

        # Same message should appear only once
        doc_ids = [f"{r['session_id']}:{r['message_index']}" for r in results]
        assert len(doc_ids) == len(set(doc_ids))


# --- TestBuildIndex ---


class TestBuildIndex:
    """Tests for batch index building."""

    def test_indexes_all_sessions(self, svc):
        """B1: Indexes messages from all sessions."""
        # Mock DatabaseService
        mock_db = MagicMock()

        mock_session_1 = MagicMock()
        mock_session_1.session_id = "sess-1"
        mock_session_1.project_name = "project-a"

        mock_session_2 = MagicMock()
        mock_session_2.session_id = "sess-2"
        mock_session_2.project_name = "project-b"

        mock_db.get_session_summaries.return_value = [mock_session_1, mock_session_2]

        mock_msg_1 = MagicMock()
        mock_msg_1.role = "user"
        mock_msg_1.content = "How do I set up a database?"
        mock_msg_1.message_index = 0

        mock_msg_2 = MagicMock()
        mock_msg_2.role = "assistant"
        mock_msg_2.content = "Here is how..."
        mock_msg_2.message_index = 1

        mock_msg_3 = MagicMock()
        mock_msg_3.role = "user"
        mock_msg_3.content = "Can you also add an API endpoint for search?"
        mock_msg_3.message_index = 2

        mock_msg_4 = MagicMock()
        mock_msg_4.role = "user"
        mock_msg_4.content = "Deploy this application to production please"
        mock_msg_4.message_index = 0

        mock_db.get_messages_for_session.side_effect = [
            [mock_msg_1, mock_msg_2, mock_msg_3],  # sess-1: 2 user msgs
            [mock_msg_4],  # sess-2: 1 user msg
        ]

        total = svc.build_index(mock_db)

        assert total == 3
        assert svc.collection_count() == 3
