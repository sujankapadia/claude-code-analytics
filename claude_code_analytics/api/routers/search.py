"""Search endpoints."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from claude_code_analytics.api.dependencies import get_db_service
from claude_code_analytics.streamlit_app.services.database_service import DatabaseService

router = APIRouter(tags=["search"])


@router.get("/search")
def search(
    q: str,
    scope: str = "All",
    project_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    per_page: int = 3,
    page: int = 0,
    db: DatabaseService = Depends(get_db_service),
):
    """Search across messages and tool uses, grouped by session.

    Args:
        q: Search query (FTS5 syntax supported)
        scope: One of All, Messages, Tool Inputs, Tool Results
        project_id: Optional project filter
        tool_name: Optional tool name filter
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        per_page: Sessions per page
        page: Page number (0-indexed)
    """
    try:
        return db.search_grouped_by_session(
            query=q,
            scope=scope,
            project_id=project_id,
            tool_name=tool_name,
            start_date=start_date,
            end_date=end_date,
            sessions_per_page=per_page,
            page=page,
        )
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
