"""CLI entry points for claude-code-analytics."""


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


def api():
    """Launch the FastAPI server."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Launch Claude Code Analytics API server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "claude_code_analytics.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
