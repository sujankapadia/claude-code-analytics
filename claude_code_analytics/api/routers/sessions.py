"""Session endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from claude_code_analytics.api.dependencies import get_db_service
from claude_code_analytics.services.database_service import DatabaseService

router = APIRouter(tags=["sessions"])


@router.get("/sessions")
def list_sessions(
    project_id: Optional[str] = None,
    limit: Optional[int] = None,
    db: DatabaseService = Depends(get_db_service),
):
    """Get session summaries, optionally filtered by project."""
    summaries = db.get_session_summaries(project_id=project_id, limit=limit)
    return [s.model_dump() for s in summaries]


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get a single session by ID."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get all messages for a session."""
    messages = db.get_messages_for_session(session_id)
    return [m.model_dump() for m in messages]


@router.get("/sessions/{session_id}/tool-uses")
def get_session_tool_uses(session_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get all tool uses for a session."""
    tool_uses = db.get_tool_uses_for_session(session_id)
    return [t.model_dump() for t in tool_uses]


@router.get("/sessions/{session_id}/tokens")
def get_session_tokens(session_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get aggregated token usage for a session."""
    return db.get_token_usage_for_session(session_id)


@router.get("/sessions/{session_id}/tokens/timeline")
def get_session_token_timeline(session_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get cumulative token usage timeline for a session."""
    return db.get_token_timeline_for_session(session_id)


@router.get("/sessions/{session_id}/activity")
def get_session_activity(
    session_id: str,
    idle_cap: int = 300,
    db: DatabaseService = Depends(get_db_service),
):
    """Get active time metrics for a session."""
    return db.get_active_time_for_session(session_id, idle_cap_seconds=idle_cap)


@router.get("/sessions/{session_id}/text-volume")
def get_session_text_volume(session_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get text volume metrics for a session."""
    return db.get_text_volume_for_session(session_id)
