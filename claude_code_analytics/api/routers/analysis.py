"""Analysis endpoints for LLM-powered session analysis."""

import asyncio
import ipaddress
import socket
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from claude_code_analytics.api.dependencies import get_analysis_service
from claude_code_analytics.models import AnalysisType
from claude_code_analytics.services.analysis_service import AnalysisService
from claude_code_analytics.services.llm_providers import (
    OpenAICompatibleProvider,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Well-known local LLM provider ports allowed on loopback addresses
_ALLOWED_LOCAL_PORTS = {11434, 1234, 8001}


def validate_base_url(url: str) -> str:
    """Validate that a base_url does not target internal/private networks.

    Allows public http/https URLs and localhost on known local-provider ports
    (Ollama 11434, LM Studio 1234, vLLM 8001).

    Raises HTTPException(422) for disallowed URLs.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="URL must include a hostname.")

    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail=f"Cannot resolve hostname '{hostname}'.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])

        if ip.is_loopback:
            if port in _ALLOWED_LOCAL_PORTS:
                continue
            raise HTTPException(
                status_code=422,
                detail=(
                    "Loopback addresses are only allowed on ports "
                    f"{sorted(_ALLOWED_LOCAL_PORTS)}."
                ),
            )

        if ip.is_private or ip.is_reserved or ip.is_link_local:
            raise HTTPException(
                status_code=422,
                detail="URLs pointing to private/internal network addresses are not allowed.",
            )

    return url


class AnalysisRequest(BaseModel):
    """Request body for running an analysis."""

    session_id: str
    analysis_type: AnalysisType
    custom_prompt: str | None = None
    model: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    message_index: int | None = None
    context_window: int = 20
    base_url: str | None = None
    api_key: str | None = None


class PublishRequest(BaseModel):
    """Request body for publishing analysis to a Gist."""

    analysis_content: str
    session_content: str | None = None
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
        validate_base_url(req.base_url)
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


class ModelsRequest(BaseModel):
    base_url: str
    api_key: str | None = None


@router.post("/models")
async def list_provider_models(req: ModelsRequest):
    """Fetch available models from an OpenAI-compatible provider (proxy to avoid CORS)."""
    validate_base_url(req.base_url)
    loop = asyncio.get_event_loop()
    try:
        raw_models = await loop.run_in_executor(
            None,
            lambda: OpenAICompatibleProvider.fetch_all_models(
                base_url=req.base_url, api_key=req.api_key
            ),
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
async def publish_analysis(req: PublishRequest, request: Request):
    """Publish analysis result to a GitHub Gist.

    Security note: This endpoint uses the server's GITHUB_TOKEN to create Gists.
    This is intentional for localhost use — the tool is designed to run locally.
    Access is restricted to localhost (127.0.0.1 / ::1) as an additional safeguard.
    """
    from claude_code_analytics import config
    from claude_code_analytics.services.gist_publisher import GistPublisher

    # Restrict to localhost callers only
    client_host = request.client.host if request.client else None
    if client_host not in ("127.0.0.1", "::1"):
        raise HTTPException(
            status_code=403,
            detail="Publishing is only allowed from localhost",
        )

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
