"""CLI entry points for claude-code-analytics."""

import sys


def dashboard():
    """Launch the Streamlit dashboard."""
    import shutil
    import subprocess
    from pathlib import Path

    from claude_code_analytics import streamlit_app

    # Find streamlit executable in PATH
    streamlit_path = shutil.which("streamlit")
    if not streamlit_path:
        print("Error: streamlit not found in PATH", file=sys.stderr)
        print("Install with: pip install streamlit", file=sys.stderr)
        return 1

    # Find the app.py file within the package
    app_path = Path(streamlit_app.__file__).parent / "app.py"

    # Run streamlit with all command-line args passed through
    result = subprocess.run([streamlit_path, "run", str(app_path)] + sys.argv[1:], check=False)
    return result.returncode


def import_conversations():
    """Import conversations from Claude Code."""
    from claude_code_analytics.scripts.import_conversations import main

    return main() or 0


def search():
    """Search conversations."""
    from claude_code_analytics.scripts.search_fts import main

    return main() or 0


def analyze():
    """Analyze session metrics."""
    from claude_code_analytics.scripts.analyze_session import main

    return main() or 0
