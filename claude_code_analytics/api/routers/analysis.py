"""Analysis endpoints for LLM-powered session analysis."""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from claude_code_analytics.api.dependencies import get_analysis_service
from claude_code_analytics.streamlit_app.models import AnalysisType
from claude_code_analytics.streamlit_app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    """Request body for running an analysis."""

    session_id: str
    analysis_type: AnalysisType
    custom_prompt: Optional[str] = None
    model: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message_index: Optional[int] = None
    context_window: int = 20


class PublishRequest(BaseModel):
    """Request body for publishing analysis to a Gist."""

    analysis_content: str
    session_content: Optional[str] = None
    description: str = "Claude Code Analysis"
    is_public: bool = False


@router.post("/run")
async def run_analysis(
    req: AnalysisRequest,
    svc: AnalysisService = Depends(get_analysis_service),
):
    """Run an LLM analysis on a session (blocking)."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: svc.analyze_session(
                session_id=req.session_id,
                analysis_type=req.analysis_type,
                custom_prompt=req.custom_prompt,
                model=req.model,
                start_time=req.start_time,
                end_time=req.end_time,
                message_index=req.message_index,
                context_window=req.context_window,
            ),
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/types")
def list_analysis_types(svc: AnalysisService = Depends(get_analysis_service)):
    """Get available analysis types."""
    types = svc.get_available_analysis_types()
    return {k: v.model_dump() for k, v in types.items()}


@router.post("/publish")
async def publish_analysis(req: PublishRequest):
    """Publish analysis result to a GitHub Gist."""
    from claude_code_analytics import config
    from claude_code_analytics.streamlit_app.services.gist_publisher import GistPublisher

    if not config.GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GITHUB_TOKEN not configured")

    publisher = GistPublisher(github_token=config.GITHUB_TOKEN)
    loop = asyncio.get_event_loop()

    success, url_or_error, findings = await loop.run_in_executor(
        None,
        lambda: publisher.publish(
            analysis_content=req.analysis_content,
            session_content=req.session_content,
            description=req.description,
            is_public=req.is_public,
        ),
    )

    if not success:
        raise HTTPException(status_code=500, detail=url_or_error)

    return {
        "url": url_or_error,
        "findings": [f.model_dump() if hasattr(f, "model_dump") else str(f) for f in findings],
    }
