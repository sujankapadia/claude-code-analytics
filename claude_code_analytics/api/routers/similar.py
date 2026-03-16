"""Session similarity search endpoint.

Finds sessions related to a query by aggregating FTS results at the session level.
Future iterations add semantic search (ChromaDB) and query expansion (LLM).
"""

import logging
import re
import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from claude_code_analytics.api.dependencies import get_db_service
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


def _fts_session_search(db: DatabaseService, query: str) -> dict[str, dict[str, Any]]:
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
        message_hits = db.search_messages(query=query, limit=200)
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
        tool_hits = db.search_tool_inputs(query=query, limit=200)
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


@router.get("/search/sessions", response_model=SimilarResponse)
def find_similar_sessions(
    q: str,
    limit: int = 10,
    exclude_session: Optional[str] = None,
    db: DatabaseService = Depends(get_db_service),
):
    """Find sessions similar to a query using hybrid search.

    Combines FTS keyword search with session-level aggregation.
    Future iterations add semantic search and query expansion.
    """
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")

    # Step 1: FTS session search
    fts_results = _fts_session_search(db, q)

    # Step 2: RRF fusion (FTS only for now)
    ranked = _rrf_fusion(fts_results)

    # Step 3: Exclude specified session
    if exclude_session:
        ranked = [(sid, score) for sid, score in ranked if sid != exclude_session]

    # Step 4: Enrich top N with session metadata
    all_summaries = db.get_session_summaries()
    summary_map = {s.session_id: s for s in all_summaries}

    results = []
    for sid, rrf_score in ranked[:limit]:
        fts_data = fts_results.get(sid, {})
        summary = summary_map.get(sid)

        # Dedupe and limit matches
        seen_indices: set[int] = set()
        matches = []
        for m in fts_data.get("matches", []):
            idx = m["message_index"]
            if idx not in seen_indices and len(matches) < _MAX_MATCHES_PER_SESSION:
                seen_indices.add(idx)
                matches.append(
                    SampleMatch(
                        source=m["source"],
                        message_index=idx,
                        text=m["text"],
                    )
                )

        results.append(
            SessionResult(
                session_id=sid,
                project_name=fts_data.get("project_name")
                or (summary.project_name if summary else ""),
                score=round(rrf_score, 6),
                fts_hits=fts_data.get("hits", 0),
                start_time=str(summary.start_time) if summary and summary.start_time else None,
                end_time=str(summary.end_time) if summary and summary.end_time else None,
                message_count=summary.message_count if summary else 0,
                tool_use_count=summary.tool_use_count if summary else 0,
                sample_matches=matches,
            )
        )

    return SimilarResponse(
        query=q,
        results=results,
        total_sessions=len(ranked),
    )
