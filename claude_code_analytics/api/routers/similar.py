"""Session similarity search endpoint.

Hybrid search: FTS keyword search + ChromaDB semantic embeddings + LLM query expansion,
fused via Reciprocal Rank Fusion (RRF).
"""

import logging
import re
import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from claude_code_analytics import config
from claude_code_analytics.api.dependencies import get_db_service, get_embedding_service
from claude_code_analytics.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["similar"])

# Weights for FTS scope aggregation
_MESSAGE_WEIGHT = 1.0
_TOOL_INPUT_WEIGHT = 1.5

# RRF constant
_RRF_K = 60

# Max matches to show per session
_MAX_MATCHES_PER_SESSION = 5


class SampleMatch(BaseModel):
    source: str  # "fts_message", "fts_tool_input", or future "semantic"
    message_index: int
    text: str
    similarity: Optional[float] = None
    matched_via: Optional[str] = None


class SessionResult(BaseModel):
    session_id: str
    project_name: str
    score: float
    fts_hits: int
    semantic_best: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    message_count: int = 0
    tool_use_count: int = 0
    sample_matches: list[SampleMatch]


class SimilarResponse(BaseModel):
    query: str
    expansions: list[str] = []
    results: list[SessionResult]
    total_sessions: int


def _strip_html(text: str) -> str:
    """Remove HTML tags from FTS snippets."""
    return re.sub(r"<[^>]+>", "", text)


def _fts_session_search(
    db: DatabaseService, query: str, project_id: Optional[str] = None
) -> dict[str, dict[str, Any]]:
    """Run FTS across messages and tool inputs, aggregate by session.

    Returns dict keyed by session_id with:
        score: weighted hit count
        hits: total hit count
        matches: list of {source, message_index, text}
        project_name: from first hit
    """
    sessions: dict[str, dict[str, Any]] = {}

    # Search messages
    try:
        message_hits = db.search_messages(query=query, limit=200, project_id=project_id)
        for hit in message_hits:
            sid = hit["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "score": 0,
                    "hits": 0,
                    "matches": [],
                    "project_name": hit.get("project_name", ""),
                }
            sessions[sid]["score"] += _MESSAGE_WEIGHT
            sessions[sid]["hits"] += 1
            snippet = _strip_html(hit.get("snippet") or hit.get("content") or "")
            if snippet:
                sessions[sid]["matches"].append(
                    {
                        "source": "fts_message",
                        "message_index": hit["message_index"],
                        "text": snippet[:200],
                    }
                )
    except sqlite3.OperationalError:
        logger.debug("FTS message search failed for query: %s", query)

    # Search tool inputs
    try:
        tool_hits = db.search_tool_inputs(query=query, limit=200, project_id=project_id)
        for hit in tool_hits:
            sid = hit["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "score": 0,
                    "hits": 0,
                    "matches": [],
                    "project_name": hit.get("project_name", ""),
                }
            sessions[sid]["score"] += _TOOL_INPUT_WEIGHT
            sessions[sid]["hits"] += 1
            tool_text = f"{hit.get('tool_name', '')}: {(hit.get('tool_input') or '')[:150]}"
            sessions[sid]["matches"].append(
                {
                    "source": "fts_tool_input",
                    "message_index": hit["message_index"],
                    "text": tool_text[:200],
                }
            )
    except sqlite3.OperationalError:
        logger.debug("FTS tool input search failed for query: %s", query)

    return sessions


def _rrf_fusion(
    fts_results: dict[str, dict[str, Any]],
    semantic_results: Optional[dict[str, dict[str, Any]]] = None,
    k: int = _RRF_K,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion of ranked result lists.

    Returns list of (session_id, rrf_score) sorted by score descending.
    """
    scores: dict[str, float] = {}

    # Rank FTS results by weighted score
    fts_ranked = sorted(fts_results.items(), key=lambda x: -x[1]["score"])
    for rank, (sid, _) in enumerate(fts_ranked):
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank + 1)

    # Rank semantic results (future: iteration 2)
    if semantic_results:
        sem_ranked = sorted(semantic_results.items(), key=lambda x: -x[1].get("best", 0))
        for rank, (sid, _) in enumerate(sem_ranked):
            scores[sid] = scores.get(sid, 0) + 1 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: -x[1])


def _semantic_session_search_from_hits(
    hits: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Aggregate semantic search hits by session.

    Args:
        hits: List of hit dicts from EmbeddingService.search or search_expanded.

    Returns dict keyed by session_id with:
        best: highest similarity score
        hits: total hit count
        matches: list of {source, message_index, text, similarity, matched_via}
    """
    sessions: dict[str, dict[str, Any]] = {}
    for hit in hits:
        sid = hit["session_id"]
        if sid not in sessions:
            sessions[sid] = {
                "best": 0,
                "hits": 0,
                "matches": [],
            }
        sessions[sid]["hits"] += 1
        if hit["similarity"] > sessions[sid]["best"]:
            sessions[sid]["best"] = hit["similarity"]
        sessions[sid]["matches"].append(
            {
                "source": "semantic",
                "message_index": hit["message_index"],
                "text": hit["text"][:200],
                "similarity": round(hit["similarity"], 3),
                "matched_via": hit.get("matched_via"),
            }
        )

    return sessions


def _get_expansion_provider():
    """Create the appropriate provider for query expansion based on config."""
    base = config.EXPANSION_BASE_URL.rstrip("/")
    is_ollama = "11434" in base or "ollama" in base.lower()

    if is_ollama:
        from claude_code_analytics.services.llm_providers import OllamaProvider

        return OllamaProvider(
            base_url=base,
            default_model=config.EXPANSION_MODEL,
        )
    else:
        from claude_code_analytics.services.llm_providers import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            base_url=base,
            api_key=config.EXPANSION_API_KEY or None,
            default_model=config.EXPANSION_MODEL,
        )


def _expand_query(query: str) -> list[str]:
    """Expand a query into alternative phrasings using a configured LLM.

    Uses OllamaProvider for local models (with think=false, keep_alive=30m)
    or OpenAICompatibleProvider for remote APIs.
    Returns empty list on any failure — search proceeds without expansion.
    """
    if not config.EXPANSION_BASE_URL:
        return []

    prompt = (
        f"List 6 alternative phrases a software developer might use "
        f'when discussing "{query}". Comma-separated only, no explanation.'
    )

    try:
        provider = _get_expansion_provider()
        response = provider.generate(prompt)
        text = response.text.strip()

        # Strip thinking tags as fallback
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        expansions = [t.strip() for t in text.split(",") if t.strip()]
        logger.debug("Query expansion for '%s': %s", query, expansions)
        return expansions[:8]
    except Exception:
        logger.debug("Query expansion failed for '%s'", query, exc_info=True)
        return []


@router.get("/search/sessions", response_model=SimilarResponse)
def find_similar_sessions(
    q: str,
    limit: int = 10,
    exclude_session: Optional[str] = None,
    project_id: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service),
    embedding_service=Depends(get_embedding_service),
):
    """Find sessions similar to a query using hybrid search.

    Combines FTS keyword search, semantic embeddings, and LLM query expansion.
    Degrades gracefully: works with any combination of available layers.
    """
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")

    # Step 1: FTS session search
    fts_results = _fts_session_search(db, q, project_id=project_id)

    # Step 2: Query expansion (if provider available)
    expansions = _expand_query(q)

    # Step 3: Semantic search with expansions (if embeddings available)
    if embedding_service and embedding_service.collection_count() > 0:
        if expansions:
            hits = embedding_service.search_expanded(q, expansions)
        else:
            hits = embedding_service.search(q)

        # Aggregate hits by session
        semantic_results = _semantic_session_search_from_hits(hits)
    else:
        semantic_results = {}

    # Step 4: RRF fusion
    ranked = _rrf_fusion(fts_results, semantic_results if semantic_results else None)

    # Step 4: Exclude specified session
    if exclude_session:
        ranked = [(sid, score) for sid, score in ranked if sid != exclude_session]

    # Step 5: Enrich top N with session metadata
    all_summaries = db.get_session_summaries()
    summary_map = {s.session_id: s for s in all_summaries}

    # Filter by project_id (catches semantic-only results not filtered by FTS)
    if project_id:
        ranked = [
            (sid, score)
            for sid, score in ranked
            if summary_map.get(sid) and summary_map[sid].project_id == project_id
        ]

    results = []
    for sid, rrf_score in ranked[:limit]:
        fts_data = fts_results.get(sid, {})
        sem_data = semantic_results.get(sid, {})
        summary = summary_map.get(sid)

        # Merge FTS and semantic matches, dedupe by message_index
        all_matches = fts_data.get("matches", []) + sem_data.get("matches", [])
        # Sort semantic matches first (richer info), then FTS
        all_matches.sort(key=lambda m: (m.get("similarity") or 0), reverse=True)

        seen_indices: set[int] = set()
        matches = []
        for m in all_matches:
            idx = m["message_index"]
            if idx not in seen_indices and len(matches) < _MAX_MATCHES_PER_SESSION:
                seen_indices.add(idx)
                matches.append(
                    SampleMatch(
                        source=m["source"],
                        message_index=idx,
                        text=m["text"],
                        similarity=m.get("similarity"),
                        matched_via=m.get("matched_via"),
                    )
                )

        results.append(
            SessionResult(
                session_id=sid,
                project_name=fts_data.get("project_name")
                or (summary.project_name if summary else ""),
                score=round(rrf_score, 6),
                fts_hits=fts_data.get("hits", 0),
                semantic_best=round(sem_data["best"], 3) if sem_data.get("best") else None,
                start_time=str(summary.start_time) if summary and summary.start_time else None,
                end_time=str(summary.end_time) if summary and summary.end_time else None,
                message_count=summary.message_count if summary else 0,
                tool_use_count=summary.tool_use_count if summary else 0,
                sample_matches=matches,
            )
        )

    return SimilarResponse(
        query=q,
        expansions=expansions,
        results=results,
        total_sessions=len(ranked),
    )
