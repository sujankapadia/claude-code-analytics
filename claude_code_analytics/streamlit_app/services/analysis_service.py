"""Analysis service layer for running LLM-powered analysis."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import json
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from claude_code_analytics.streamlit_app.models import (
    AnalysisType,
    AnalysisResult,
    AnalysisTypeMetadata,
    Message,
    ToolUse,
)
from claude_code_analytics.streamlit_app.services.llm_providers import LLMProvider, create_provider
from claude_code_analytics.streamlit_app.services.database_service import DatabaseService


class AnalysisService:
    """Service for running conversation analysis."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        db_path: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """
        Initialize analysis service.

        Args:
            provider: LLM provider instance. If None, creates provider from environment.
            db_path: Path to database. Defaults to ~/claude-conversations/conversations.db
            default_model: Default model to use for analysis
        """
        # Initialize provider
        if provider is None:
            self.provider = create_provider(default_model=default_model)
        else:
            self.provider = provider

        # Set database path
        if db_path is None:
            db_path = str(Path.home() / "claude-conversations" / "conversations.db")
        self.db_path = db_path

        # Initialize database service
        self.db_service = DatabaseService(db_path=db_path)

        # Load prompt metadata
        self.metadata, self.jinja_env = self._load_prompts()

    @property
    def api_key(self) -> Optional[str]:
        """Legacy property for backwards compatibility."""
        # Check if provider has API key
        return getattr(self.provider, 'api_key', None)

    def _load_prompts(self) -> tuple[Dict[str, AnalysisTypeMetadata], Environment]:
        """
        Load analysis prompts from Jinja2 template files.

        Returns:
            Tuple of (metadata dict, jinja2 environment)
        """
        # Get prompts directory (relative to project root)
        project_root = Path(__file__).parent.parent.parent
        prompts_dir = project_root / "prompts"

        # Load metadata
        metadata_file = prompts_dir / "metadata.yaml"
        with open(metadata_file, "r") as f:
            raw_metadata = yaml.safe_load(f)

        # Convert to Pydantic models
        metadata = {
            key: AnalysisTypeMetadata(**value) for key, value in raw_metadata.items()
        }

        # Create Jinja2 environment
        env = Environment(loader=FileSystemLoader(str(prompts_dir)))

        return metadata, env

    def get_available_analysis_types(self) -> Dict[str, AnalysisTypeMetadata]:
        """Get all available analysis types and their metadata."""
        return self.metadata

    def format_messages_simple(
        self,
        messages: List[Message],
        tool_uses: List[ToolUse]
    ) -> str:
        """
        Format messages and tool uses into simple transcript format.

        Args:
            messages: List of Message objects
            tool_uses: List of ToolUse objects

        Returns:
            Formatted transcript string
        """
        # Create mapping of message_index to tool uses for quick lookup
        tools_by_message = {}
        for tool in tool_uses:
            if tool.message_index not in tools_by_message:
                tools_by_message[tool.message_index] = []
            tools_by_message[tool.message_index].append(tool)

        lines = []

        for msg in messages:
            # Format timestamp
            timestamp = msg.timestamp if isinstance(msg.timestamp, str) else msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            # Add message header and content
            lines.append(f"[{msg.role.capitalize()} - {timestamp}]")
            if msg.content:
                lines.append(msg.content)

            # Add tool uses for this message
            if msg.message_index in tools_by_message:
                for tool in tools_by_message[msg.message_index]:
                    lines.append(f"\n[Tool: {tool.tool_name} - {tool.timestamp if isinstance(tool.timestamp, str) else tool.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]")

                    # Add tool input (parse JSON if possible for readability)
                    if tool.tool_input:
                        try:
                            tool_input_dict = json.loads(tool.tool_input)
                            lines.append("Input:")
                            for key, value in tool_input_dict.items():
                                # Truncate long values
                                value_str = str(value)
                                if len(value_str) > 200:
                                    value_str = value_str[:200] + "..."
                                lines.append(f"  {key}: {value_str}")
                        except (json.JSONDecodeError, TypeError):
                            lines.append(f"Input: {tool.tool_input[:200]}...")

                    # Add tool result
                    if tool.tool_result:
                        result_preview = tool.tool_result[:500] + "..." if len(tool.tool_result) > 500 else tool.tool_result
                        lines.append(f"Result: {result_preview}")

                    if tool.is_error:
                        lines.append("(Error)")

            lines.append("")  # Blank line between messages

        return "\n".join(lines)

    def format_messages_with_highlight(
        self,
        messages: List[Message],
        tool_uses: List[ToolUse],
        highlight_index: int
    ) -> str:
        """
        Format messages with one message highlighted as the search hit.

        Args:
            messages: List of Message objects
            tool_uses: List of ToolUse objects
            highlight_index: message_index to highlight as search hit

        Returns:
            Formatted transcript string with markers
        """
        # Create mapping of message_index to tool uses for quick lookup
        tools_by_message = {}
        for tool in tool_uses:
            if tool.message_index not in tools_by_message:
                tools_by_message[tool.message_index] = []
            tools_by_message[tool.message_index].append(tool)

        lines = []

        for msg in messages:
            # Format timestamp
            timestamp = msg.timestamp if isinstance(msg.timestamp, str) else msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            # Check if this is the highlighted message
            is_highlight = msg.message_index == highlight_index

            if is_highlight:
                lines.append(f"\n>>> SEARCH HIT - Message {msg.message_index} <<<")

            # Add message header and content
            lines.append(f"[{msg.role.capitalize()} - {timestamp}]")
            if msg.content:
                lines.append(msg.content)

            # Add tool uses for this message
            if msg.message_index in tools_by_message:
                for tool in tools_by_message[msg.message_index]:
                    lines.append(f"\n[Tool: {tool.tool_name} - {tool.timestamp if isinstance(tool.timestamp, str) else tool.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]")

                    # Add tool input (parse JSON if possible for readability)
                    if tool.tool_input:
                        try:
                            tool_input_dict = json.loads(tool.tool_input)
                            lines.append("Input:")
                            for key, value in tool_input_dict.items():
                                # Truncate long values
                                value_str = str(value)
                                if len(value_str) > 200:
                                    value_str = value_str[:200] + "..."
                                lines.append(f"  {key}: {value_str}")
                        except (json.JSONDecodeError, TypeError):
                            lines.append(f"Input: {tool.tool_input[:200]}...")

                    # Add tool result
                    if tool.tool_result:
                        result_preview = tool.tool_result[:500] + "..." if len(tool.tool_result) > 500 else tool.tool_result
                        lines.append(f"Result: {result_preview}")

                    if tool.is_error:
                        lines.append("(Error)")

            if is_highlight:
                lines.append(f">>> END SEARCH HIT <<<\n")
            else:
                lines.append("")  # Blank line between messages

        return "\n".join(lines)

    def get_messages_around_index(
        self,
        session_id: str,
        message_index: int,
        context_window: int = 20
    ) -> tuple[List[Message], List[ToolUse], str]:
        """
        Get messages around a specific message index with context window.

        Args:
            session_id: Session UUID
            message_index: The message_index to center the window around
            context_window: Number of messages before and after (default 20)

        Returns:
            Tuple of (messages, tool_uses, formatted_transcript)
        """
        # Get all messages for the session to find the range
        all_messages = self.db_service.get_messages_for_session(session_id)

        if not all_messages:
            return ([], [], "")

        # Find the target message and its position
        target_position = None
        for i, msg in enumerate(all_messages):
            if msg.message_index == message_index:
                target_position = i
                break

        if target_position is None:
            raise ValueError(f"Message index {message_index} not found in session {session_id}")

        # Calculate the range
        start_pos = max(0, target_position - context_window)
        end_pos = min(len(all_messages) - 1, target_position + context_window)

        # Get messages in range
        messages_in_range = all_messages[start_pos:end_pos + 1]

        # Get tool uses for these messages
        min_index = messages_in_range[0].message_index
        max_index = messages_in_range[-1].message_index
        all_tool_uses = self.db_service.get_tool_uses_for_session(session_id)
        tool_uses_in_range = [
            t for t in all_tool_uses
            if min_index <= t.message_index <= max_index
        ]

        # Format with highlight
        formatted = self.format_messages_with_highlight(
            messages_in_range,
            tool_uses_in_range,
            message_index
        )

        return (messages_in_range, tool_uses_in_range, formatted)

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text using tiktoken.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        try:
            import tiktoken
            # Use cl100k_base encoding (used by GPT-4, GPT-3.5-turbo, and many other models)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback to character-based estimation if tiktoken not available
            return len(text) // 4

    def get_transcript_path(self, session_id: str) -> Optional[str]:
        """
        Get the transcript path for a session, generating it if needed.

        Args:
            session_id: Session UUID

        Returns:
            Path to transcript file, or None if not found
        """
        import sqlite3

        conversations_dir = Path.home() / "claude-conversations"

        # Get project info from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.project_id, p.project_name
            FROM sessions s
            JOIN projects p ON s.project_id = p.project_id
            WHERE s.session_id = ?
        """,
            (session_id,),
        )

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        project_id, project_name = result

        # Look for existing transcript
        project_dir = conversations_dir / project_id
        if project_dir.exists():
            transcript_file = project_dir / f"{session_id}.txt"
            if transcript_file.exists():
                return str(transcript_file)

        # If not found, generate it
        claude_projects = Path.home() / ".claude" / "projects"
        jsonl_file = claude_projects / project_id / f"{session_id}.jsonl"

        if not jsonl_file.exists():
            return None

        # Create output directory
        project_dir.mkdir(parents=True, exist_ok=True)
        output_file = project_dir / f"{session_id}.txt"

        # Run pretty-print script
        pretty_print_script = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "pretty-print-transcript.py"
        )

        try:
            with open(output_file, "w") as f:
                subprocess.run(
                    [sys.executable, str(pretty_print_script), str(jsonl_file)],
                    stdout=f,
                    check=True,
                    stderr=subprocess.PIPE,
                )
            return str(output_file)
        except subprocess.CalledProcessError:
            return None

    def analyze_session(
        self,
        session_id: str,
        analysis_type: AnalysisType,
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        message_index: Optional[int] = None,
        context_window: int = 20,
    ) -> AnalysisResult:
        """
        Analyze a session with the specified analysis type.

        Args:
            session_id: Session UUID
            analysis_type: Type of analysis to perform
            custom_prompt: Custom prompt text (required if analysis_type is CUSTOM)
            model: Model to use (provider-specific). If None, uses provider's default.
            start_time: Optional start time for filtering messages (inclusive)
            end_time: Optional end time for filtering messages (inclusive)
            message_index: Optional message index for search hit context mode
            context_window: Number of messages before/after for search hit (default 20)

        Returns:
            AnalysisResult with the analysis output

        Raises:
            ValueError: If analysis type not found or custom_prompt missing
            FileNotFoundError: If transcript not found
        """
        # Determine the scope mode
        use_search_hit = message_index is not None
        use_time_filter = start_time is not None or end_time is not None

        if use_search_hit:
            # Search hit context mode
            _, _, transcript = self.get_messages_around_index(
                session_id=session_id,
                message_index=message_index,
                context_window=context_window
            )

            if not transcript.strip():
                raise ValueError(f"No messages found around message index {message_index}")

        elif use_time_filter:
            # Get messages and tool uses from database with time filter
            messages = self.db_service.get_messages_in_range(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time
            )
            tool_uses = self.db_service.get_tool_uses_in_range(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time
            )

            # Format using simple format
            transcript = self.format_messages_simple(messages, tool_uses)

            if not transcript.strip():
                raise ValueError("No messages found in the specified time range")
        else:
            # Use existing behavior: read from transcript file
            transcript_path = self.get_transcript_path(session_id)
            if not transcript_path:
                raise FileNotFoundError(
                    f"Could not find or generate transcript for session {session_id}"
                )

            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = f.read()

        # Build prompt based on analysis type
        if analysis_type == AnalysisType.CUSTOM:
            if not custom_prompt:
                raise ValueError("custom_prompt is required for CUSTOM analysis type")
            # Automatically append the transcript
            prompt = f"{custom_prompt}\n\n---\n\nCONVERSATION TRANSCRIPT:\n\n{transcript}"
        else:
            # Get metadata for this analysis type
            metadata = self.metadata.get(analysis_type.value)
            if not metadata:
                raise ValueError(f"Unknown analysis type: {analysis_type}")

            # Load and render Jinja2 template
            try:
                template = self.jinja_env.get_template(metadata.file)
                prompt = template.render(transcript=transcript)
            except TemplateNotFound:
                raise ValueError(f"Template file not found: {metadata.file}")

        # Generate analysis using provider
        llm_response = self.provider.generate(prompt, model=model)

        return AnalysisResult(
            session_id=session_id,
            analysis_type=analysis_type,
            result_text=llm_response.text,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            model_name=llm_response.model_name,
        )
