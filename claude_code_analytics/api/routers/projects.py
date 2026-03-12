"""Project endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from claude_code_analytics.api.dependencies import get_db_service
from claude_code_analytics.streamlit_app.services.database_service import DatabaseService

router = APIRouter(tags=["projects"])


@router.get("/projects")
def list_projects(db: DatabaseService = Depends(get_db_service)):
    """Get all projects with summary statistics."""
    summaries = db.get_project_summaries()
    return [s.model_dump() for s in summaries]


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: DatabaseService = Depends(get_db_service)):
    """Get a single project by ID."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump()
