"""Analysis service layer for running LLM-powered analysis."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import google.generativeai as genai

from streamlit_app.models import AnalysisType, AnalysisResult, AnalysisTypeMetadata


class AnalysisService:
    """Service for running conversation analysis."""

    def __init__(self, api_key: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize analysis service.

        Args:
            api_key: Google AI API key. Defaults to GOOGLE_API_KEY env var.
            db_path: Path to database. Defaults to ~/claude-conversations/conversations.db
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if db_path is None:
            db_path = str(Path.home() / "claude-conversations" / "conversations.db")
        self.db_path = db_path

        # Load prompt metadata
        self.metadata, self.jinja_env = self._load_prompts()

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
        self, session_id: str, analysis_type: AnalysisType
    ) -> AnalysisResult:
        """
        Analyze a session with the specified analysis type.

        Args:
            session_id: Session UUID
            analysis_type: Type of analysis to perform

        Returns:
            AnalysisResult with the analysis output

        Raises:
            ValueError: If API key not configured or analysis type not found
            FileNotFoundError: If transcript not found
        """
        if not self.api_key:
            raise ValueError(
                "Google API key not configured. Set GOOGLE_API_KEY environment variable."
            )

        # Get transcript
        transcript_path = self.get_transcript_path(session_id)
        if not transcript_path:
            raise FileNotFoundError(
                f"Could not find or generate transcript for session {session_id}"
            )

        # Read transcript
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()

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

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Generate analysis
        response = model.generate_content(prompt)

        # Extract token usage if available
        usage_metadata = getattr(response, "usage_metadata", None)
        input_tokens = None
        output_tokens = None
        if usage_metadata:
            input_tokens = getattr(usage_metadata, "prompt_token_count", None)
            output_tokens = getattr(usage_metadata, "candidates_token_count", None)

        return AnalysisResult(
            session_id=session_id,
            analysis_type=analysis_type,
            result_text=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name="gemini-2.0-flash-exp",
        )
