"""Analytics endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends

from claude_code_analytics.api.dependencies import get_db_service
from claude_code_analytics.streamlit_app.services.database_service import DatabaseService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/daily")
def get_daily_stats(days: int = 30, db: DatabaseService = Depends(get_db_service)):
    """Get daily aggregated statistics."""
    return db.get_daily_statistics(days=days)


@router.get("/tools")
def get_tool_stats(db: DatabaseService = Depends(get_db_service)):
    """Get tool usage summary."""
    summaries = db.get_tool_usage_summary()
    return [s.model_dump() for s in summaries]


@router.get("/tools/names")
def get_tool_names(db: DatabaseService = Depends(get_db_service)):
    """Get list of all unique tool names."""
    return db.get_unique_tool_names()


@router.get("/tools/mcp")
def get_mcp_stats(db: DatabaseService = Depends(get_db_service)):
    """Get MCP tool usage statistics."""
    return db.get_mcp_tool_stats()


@router.get("/heatmap")
def get_hourly_heatmap(days: int = 90, db: DatabaseService = Depends(get_db_service)):
    """Get hourly activity heatmap data (day-of-week x hour-of-day)."""
    return db.get_hourly_activity_heatmap(days=days)


@router.get("/activity")
def get_activity_metrics(
    project_id: Optional[str] = None,
    idle_cap: int = 300,
    db: DatabaseService = Depends(get_db_service),
):
    """Get aggregate activity and text volume metrics."""
    return db.get_aggregate_activity_metrics(project_id=project_id, idle_cap_seconds=idle_cap)


@router.get("/activity/by-project")
def get_activity_by_project(
    idle_cap: int = 300,
    db: DatabaseService = Depends(get_db_service),
):
    """Get activity metrics broken down by project."""
    projects = db.get_project_summaries()
    results = []
    for p in projects:
        metrics = db.get_aggregate_activity_metrics(
            project_id=p.project_id, idle_cap_seconds=idle_cap
        )
        if metrics["session_count"] == 0:
            continue
        results.append(
            {
                "project_id": p.project_id,
                "project_name": p.project_name,
                "active_time_seconds": metrics["total_active_time_seconds"],
                "wall_time_seconds": metrics["total_wall_time_seconds"],
                "idle_ratio": metrics["overall_idle_ratio"],
                "user_text_chars": metrics["total_user_text_chars"],
                "assistant_text_chars": metrics["total_assistant_text_chars"],
                "tool_output_chars": metrics["total_tool_output_chars"],
                "session_count": metrics["session_count"],
            }
        )
    return results
