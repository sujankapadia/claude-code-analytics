"""Pydantic models for analysis functionality."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    """Available analysis types."""

    DECISIONS = "decisions"
    ERRORS = "errors"
    # Future types can be added here
    # PII = "pii"


class AnalysisTypeMetadata(BaseModel):
    """Metadata for an analysis type."""

    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Short description")
    file: str = Field(..., description="Jinja2 template file")


class AnalysisResult(BaseModel):
    """Result of running an analysis."""

    session_id: str
    analysis_type: AnalysisType
    result_text: str = Field(..., description="Markdown analysis output")
    created_at: datetime = Field(default_factory=datetime.now)

    # Optional metadata
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model_name: Optional[str] = None
