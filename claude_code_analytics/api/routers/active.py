"""Router for active session monitoring."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends

from claude_code_analytics.api.dependencies import get_db_service
from claude_code_analytics.api.services.process_scanner import (
    get_active_sessions_cached,
)
from claude_code_analytics.services.database_service import (
    DatabaseService,
)

router = APIRouter(tags=["active"])


@router.get("/active-sessions")
async def get_active_sessions(
    include_recent: bool = True,
    recent_minutes: int = 60,
    db: DatabaseService = Depends(get_db_service),
):
    """Get currently active Claude Code sessions and optionally recent ones.

    Active sessions are detected via process scanning (psutil).
    Recent sessions come from the database (sessions ended within recent_minutes).
    """
    active = get_active_sessions_cached()

    recent = []
    if include_recent:
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(minutes=recent_minutes)
        summaries = db.get_session_summaries()
        for s in summaries:
            if not s.end_time:
                continue

            end_time = s.end_time
            if isinstance(end_time, str):
                try:
                    end_time = datetime.fromisoformat(end_time)
                except ValueError:
                    continue

            # Ensure both times are tz-aware for comparison
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            if end_time < cutoff:
                continue

            # Skip if this project has an active session
            # (use project_name as fallback since DB doesn't store project_dir)
            if any(a.project_name in (s.project_name or "") for a in active):
                continue

            ended_minutes_ago = int((now_utc - end_time).total_seconds() / 60)

            recent.append(
                {
                    "session_id": s.session_id,
                    "project_name": Path(s.project_name).name if s.project_name else "Unknown",
                    "ended_at": end_time.isoformat(),
                    "ended_minutes_ago": ended_minutes_ago,
                    "message_count": s.message_count or 0,
                    "first_user_message": s.first_user_message,
                }
            )

        # Sort by most recently ended first, limit to 10
        recent.sort(key=lambda x: x["ended_at"], reverse=True)
        recent = recent[:10]

    return {
        "active": [
            {
                "pid": s.pid,
                "tty": s.tty,
                "project_name": s.project_name,
                "project_dir": s.project_dir,
                "started_at": s.started_at,
                "duration_minutes": s.duration_minutes,
                "status": s.status,
                "recent_messages": s.recent_messages,
            }
            for s in active
        ],
        "recent": recent,
    }
