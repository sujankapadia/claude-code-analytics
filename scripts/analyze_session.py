#!/usr/bin/env python3
"""
Analyze Claude Code conversation sessions using Gemini 2.5 Flash.

This script provides multiple analysis types for conversation transcripts:
- decisions: Technical decisions, alternatives, and reasoning
- errors: Error patterns, root causes, and resolutions

Usage:
    python3 analyze_session.py <session_id> --type=decisions
    python3 analyze_session.py <session_id> --type=errors
    python3 analyze_session.py <session_id> --type=errors --output=analysis.md
"""

import argparse
import sqlite3
import os
import sys
from pathlib import Path
from typing import Optional, Dict
import google.generativeai as genai
from dotenv import load_dotenv
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Load environment variables from .env file
load_dotenv()


def load_prompts() -> tuple[Dict[str, str], Environment]:
    """
    Load analysis prompts from Jinja2 template files.

    Returns:
        Tuple of (metadata dict, jinja2 environment)
    """
    script_dir = Path(__file__).parent
    prompts_dir = script_dir.parent / "prompts"

    # Load metadata
    metadata_file = prompts_dir / "metadata.yaml"
    with open(metadata_file, 'r') as f:
        metadata = yaml.safe_load(f)

    # Create Jinja2 environment
    env = Environment(loader=FileSystemLoader(str(prompts_dir)))

    return metadata, env


# Load prompt metadata and Jinja2 environment
PROMPT_METADATA, JINJA_ENV = load_prompts()


def get_session_transcript(session_id: str, db_path: str) -> Optional[str]:
    """
    Get the pretty-printed transcript for a session.

    Args:
        session_id: Session UUID
        db_path: Path to SQLite database

    Returns:
        Transcript file path or None if not found
    """
    # Check if transcript already exists in ~/claude-conversations/
    conversations_dir = Path.home() / "claude-conversations"

    # Get project info from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.project_id, p.project_name
        FROM sessions s
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.session_id = ?
    """, (session_id,))

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
        print(f"❌ JSONL file not found: {jsonl_file}", file=sys.stderr)
        return None

    # Create output directory
    project_dir.mkdir(parents=True, exist_ok=True)
    output_file = project_dir / f"{session_id}.txt"

    # Run pretty-print script
    print(f"📄 Generating transcript from {jsonl_file}...")
    pretty_print_script = Path.home() / ".claude" / "scripts" / "pretty-print-transcript.py"

    import subprocess
    try:
        with open(output_file, 'w') as f:
            subprocess.run([str(pretty_print_script), str(jsonl_file)], stdout=f, check=True)
        print(f"✅ Transcript saved to {output_file}")
        return str(output_file)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating transcript: {e}", file=sys.stderr)
        return None


def analyze_with_gemini(transcript_path: str, api_key: str, analysis_type: str) -> str:
    """
    Analyze transcript using Gemini 2.5 Flash.

    Args:
        transcript_path: Path to conversation transcript
        api_key: Google AI API key
        analysis_type: Type of analysis to perform

    Returns:
        Analysis text
    """
    # Read transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Get metadata for this analysis type
    metadata = PROMPT_METADATA.get(analysis_type)
    if not metadata:
        raise ValueError(f"Unknown analysis type: {analysis_type}")

    # Load and render Jinja2 template
    try:
        template_file = metadata['file']
        template = JINJA_ENV.get_template(template_file)
        prompt = template.render(transcript=transcript)
    except TemplateNotFound:
        raise ValueError(f"Template file not found: {metadata['file']}")

    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

    analysis_name = metadata['name']
    print(f"🤖 Running {analysis_name} with Gemini 2.5 Flash...")
    print(f"📊 Transcript size: {len(transcript):,} characters")

    # Generate analysis
    response = model.generate_content(prompt)

    return response.text


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze Claude Code conversation sessions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Analysis Types:
  decisions    Technical decisions, alternatives, and reasoning
  errors       Error patterns, root causes, and resolutions

Examples:
  %(prog)s abc123 --type=decisions
  %(prog)s abc123 --type=errors --output=error-analysis.md
        """
    )
    parser.add_argument('session_id', nargs='?', help='Session UUID to analyze')
    parser.add_argument(
        '--type',
        choices=['decisions', 'errors'],
        default='decisions',
        help='Type of analysis to perform (default: decisions)'
    )
    parser.add_argument('--project', help='Analyze all sessions for a project (not yet implemented)')
    parser.add_argument(
        '--db',
        default=str(Path.home() / 'claude-conversations' / 'conversations.db'),
        help='Path to database (default: ~/claude-conversations/conversations.db)'
    )
    parser.add_argument('--output', help='Output file path (default: stdout)')

    args = parser.parse_args()

    # Get API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key from: https://aistudio.google.com/app/apikey", file=sys.stderr)
        sys.exit(1)

    # Validate arguments
    if not args.session_id and not args.project:
        parser.print_help()
        sys.exit(1)

    if args.project:
        print("❌ Error: Project-level analysis not yet implemented", file=sys.stderr)
        print("Please specify a single session_id for now.", file=sys.stderr)
        sys.exit(1)

    # Get transcript
    print(f"🔍 Looking up session {args.session_id}...")
    transcript_path = get_session_transcript(args.session_id, args.db)

    if not transcript_path:
        print(f"❌ Could not find or generate transcript for session {args.session_id}", file=sys.stderr)
        sys.exit(1)

    # Analyze
    try:
        analysis = analyze_with_gemini(transcript_path, api_key, args.type)

        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            print(f"\n✅ Analysis saved to {output_path}")
        else:
            # Get analysis name from metadata
            metadata = PROMPT_METADATA.get(args.type, {})
            analysis_name = metadata.get('name', args.type.upper())
            print("\n" + "="*100)
            print(analysis_name.upper())
            print("="*100 + "\n")
            print(analysis)

    except Exception as e:
        print(f"❌ Error during analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
