"""Pydantic models matching the database schema."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Project(BaseModel):
    """Project model - represents a directory containing conversations."""

    project_id: str = Field(..., description="Encoded directory name")
    project_name: str = Field(..., description="Human-readable project name")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class Session(BaseModel):
    """Session model - represents a single conversation (JSONL file)."""

    session_id: str = Field(..., description="UUID from JSONL filename")
    project_id: str = Field(..., description="Foreign key to projects")
    start_time: Optional[datetime] = Field(None, description="First message timestamp")
    end_time: Optional[datetime] = Field(None, description="Last message timestamp")
    message_count: int = Field(default=0, description="Total messages")
    tool_use_count: int = Field(default=0, description="Total tool uses")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class Message(BaseModel):
    """Message model - represents a single message in a conversation."""

    message_id: int
    session_id: str
    message_index: int = Field(..., description="Order within session")
    role: str = Field(..., description="user or assistant")
    content: Optional[str] = Field(None, description="Message text")
    timestamp: datetime

    # Token usage (only for assistant messages)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None
    cache_ephemeral_5m_tokens: Optional[int] = None
    cache_ephemeral_1h_tokens: Optional[int] = None

    class Config:
        from_attributes = True


class ToolUse(BaseModel):
    """Tool use model - represents a tool invocation and result."""

    tool_use_id: str = Field(..., description="Tool use ID (e.g., toolu_...)")
    session_id: str
    tool_name: str = Field(..., description="Tool name (Bash, Write, etc.)")
    tool_input: Optional[str] = Field(None, description="JSON string of input")
    tool_result: Optional[str] = Field(None, description="Result text")
    is_error: bool = Field(default=False, description="Whether result is an error")
    timestamp: datetime

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Aggregated statistics per project."""

    project_id: str
    project_name: str
    total_sessions: int
    first_session: Optional[datetime]
    last_session: Optional[datetime]
    total_messages: int
    total_tool_uses: int

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    """Detailed statistics per session."""

    session_id: str
    project_id: str
    project_name: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    message_count: int
    tool_use_count: int
    user_message_count: int
    assistant_message_count: int

    class Config:
        from_attributes = True


class ToolUsageSummary(BaseModel):
    """Statistics by tool name."""

    tool_name: str
    total_uses: int
    error_count: int
    error_rate_percent: float
    sessions_used_in: int
    first_used: Optional[datetime]
    last_used: Optional[datetime]

    class Config:
        from_attributes = True
