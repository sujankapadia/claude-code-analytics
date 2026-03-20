"""Embedding service for session similarity search.

Uses ChromaDB with sentence-transformers for message-level embeddings.
Supports persistent storage across restarts and incremental indexing.
"""

import logging
from typing import Any

import chromadb

from claude_code_analytics import config
from claude_code_analytics.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

# Messages shorter than this are skipped (approvals like "Yes", "ok")
_MIN_MESSAGE_LENGTH = 20

# Truncate messages before embedding to limit token count
_MAX_MESSAGE_CHARS = 1000

# Compaction message prefix to skip
_COMPACTION_PREFIX = "This session is being continued"

# Collection name in ChromaDB
_COLLECTION_NAME = "user_messages"


class EmbeddingService:
    """Manages ChromaDB embeddings for user messages."""

    def __init__(self, persist_dir: str | None = None):
        """Initialize with persistent ChromaDB storage.

        Args:
            persist_dir: Directory for ChromaDB data. Defaults to config.CHROMA_DATA_DIR.
        """
        if persist_dir is None:
            persist_dir = str(config.CHROMA_DATA_DIR)

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def collection_count(self) -> int:
        """Number of documents in the collection."""
        return self._collection.count()

    def embed_session(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        project_name: str,
    ) -> int:
        """Embed user messages from a session.

        Args:
            session_id: Session identifier.
            messages: List of message dicts with role, content, message_index.
            project_name: Project name for metadata.

        Returns:
            Number of new embeddings added.
        """
        docs = []
        ids = []
        metadatas = []

        project_short = project_name.split("/")[-1] if "/" in project_name else project_name

        for msg in messages:
            if msg.get("role") != "user":
                continue

            content = msg.get("content")
            if not isinstance(content, str):
                continue
            if len(content.strip()) < _MIN_MESSAGE_LENGTH:
                continue
            if content.startswith(_COMPACTION_PREFIX):
                continue

            doc_id = f"{session_id}:{msg['message_index']}"
            docs.append(content[:_MAX_MESSAGE_CHARS])
            ids.append(doc_id)
            metadatas.append(
                {
                    "session_id": session_id,
                    "project": project_short,
                    "message_index": msg["message_index"],
                }
            )

        if not docs:
            return 0

        # Upsert handles both new and re-imported messages
        self._collection.upsert(
            documents=docs,
            ids=ids,
            metadatas=metadatas,
        )

        return len(docs)

    def search(self, query: str, n_results: int = 20) -> list[dict[str, Any]]:
        """Semantic search for similar messages.

        Args:
            query: Search query text.
            n_results: Maximum number of results.

        Returns:
            List of dicts with session_id, message_index, similarity, text, project.
        """
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count()),
        )

        hits = []
        for j in range(len(results["ids"][0])):
            similarity = 1 - results["distances"][0][j]
            if similarity < 0.2:
                continue

            meta = results["metadatas"][0][j]
            hits.append(
                {
                    "session_id": meta["session_id"],
                    "message_index": meta["message_index"],
                    "similarity": similarity,
                    "text": results["documents"][0][j][:200],
                    "project": meta["project"],
                }
            )

        return hits

    def search_expanded(
        self,
        query: str,
        expansions: list[str],
        n_results_per: int = 15,
    ) -> list[dict[str, Any]]:
        """Search with query + all expansions, deduplicate results.

        Args:
            query: Original search query.
            expansions: List of expanded query phrases.
            n_results_per: Max results per individual query.

        Returns:
            Deduplicated list of hits, best similarity kept per document.
        """
        all_queries = [query] + expansions
        seen: dict[str, dict[str, Any]] = {}  # keyed by doc_id

        for q in all_queries:
            hits = self.search(q, n_results=n_results_per)
            for hit in hits:
                doc_id = f"{hit['session_id']}:{hit['message_index']}"
                if doc_id not in seen or hit["similarity"] > seen[doc_id]["similarity"]:
                    hit["matched_via"] = q
                    seen[doc_id] = hit

        return list(seen.values())

    def build_index(self, db_service: DatabaseService) -> int:
        """Batch index all existing sessions.

        Args:
            db_service: DatabaseService to fetch sessions and messages.

        Returns:
            Total number of messages embedded.
        """
        sessions = db_service.get_session_summaries()
        total = 0

        for i, session in enumerate(sessions):
            messages = db_service.get_messages_for_session(session.session_id)
            msg_dicts = [
                {
                    "role": m.role,
                    "content": m.content,
                    "message_index": m.message_index,
                }
                for m in messages
            ]

            count = self.embed_session(
                session_id=session.session_id,
                messages=msg_dicts,
                project_name=session.project_name,
            )
            total += count

            if (i + 1) % 100 == 0:
                logger.info("Indexed %d/%d sessions (%d messages)", i + 1, len(sessions), total)

        logger.info("Embedding index complete: %d messages from %d sessions", total, len(sessions))
        return total
