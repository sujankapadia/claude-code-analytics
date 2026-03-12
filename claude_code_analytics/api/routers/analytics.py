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


@router.get("/activity")
def get_activity_metrics(
    project_id: Optional[str] = None,
    idle_cap: int = 300,
    db: DatabaseService = Depends(get_db_service),
):
    """Get aggregate activity and text volume metrics."""
    return db.get_aggregate_activity_metrics(project_id=project_id, idle_cap_seconds=idle_cap)
