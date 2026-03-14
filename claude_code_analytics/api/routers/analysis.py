"""Analysis endpoints for LLM-powered session analysis."""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from claude_code_analytics.api.dependencies import get_analysis_service
from claude_code_analytics.models import AnalysisType
from claude_code_analytics.services.analysis_service import AnalysisService
from claude_code_analytics.services.llm_providers import (
    OpenAICompatibleProvider,
)

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
    base_url: Optional[str] = None
    api_key: Optional[str] = None


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
    # Create a one-off provider if the client sent a custom base_url
    override_provider = None
    if req.base_url:
        override_provider = OpenAICompatibleProvider(
            base_url=req.base_url,
            api_key=req.api_key,
            default_model=req.model or "default",
        )

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
                provider=override_provider,
            ),
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/provider-info")
def get_provider_info(svc: AnalysisService = Depends(get_analysis_service)):
    """Return info about the server's default LLM provider and available presets."""
    provider = svc.provider
    provider_type = type(provider).__name__

    # Determine base_url and default_model from the active provider
    base_url = getattr(provider, "base_url", None)
    default_model = getattr(provider, "default_model", None)

    # Quick-select models (from OpenAICompatibleProvider if available)
    quick_select = [
        {"label": label, "value": model_id}
        for label, model_id in OpenAICompatibleProvider.QUICK_SELECT_MODELS
    ]

    # Provider presets
    presets = [
        {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "requires_key": True,
            "default_model": "deepseek/deepseek-v3.2",
        },
        {
            "name": "Ollama",
            "base_url": "http://localhost:11434/v1",
            "requires_key": False,
            "default_model": "llama3.2",
        },
        {
            "name": "LM Studio",
            "base_url": "http://localhost:1234/v1",
            "requires_key": False,
            "default_model": "default",
        },
        {
            "name": "vLLM",
            "base_url": "http://localhost:8001/v1",
            "requires_key": False,
            "default_model": "default",
        },
        {
            "name": "Custom",
            "base_url": "",
            "requires_key": False,
            "default_model": "",
        },
    ]

    return {
        "provider_type": provider_type,
        "base_url": base_url,
        "default_model": default_model,
        "quick_select_models": quick_select,
        "presets": presets,
    }


@router.get("/models")
async def list_provider_models(
    base_url: str,
    api_key: Optional[str] = None,
):
    """Fetch available models from an OpenAI-compatible provider (proxy to avoid CORS)."""
    loop = asyncio.get_event_loop()
    try:
        raw_models = await loop.run_in_executor(
            None,
            lambda: OpenAICompatibleProvider.fetch_all_models(base_url=base_url, api_key=api_key),
        )
        # Return just id + owned_by for each model
        return [{"id": m.get("id", ""), "owned_by": m.get("owned_by", "")} for m in raw_models]
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/types")
def list_analysis_types(svc: AnalysisService = Depends(get_analysis_service)):
    """Get available analysis types."""
    types = svc.get_available_analysis_types()
    return {k: v.model_dump() for k, v in types.items()}


@router.post("/publish")
async def publish_analysis(req: PublishRequest):
    """Publish analysis result to a GitHub Gist."""
    from claude_code_analytics import config
    from claude_code_analytics.services.gist_publisher import GistPublisher

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
