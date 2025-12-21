"""Configuration module for Claude Code Analytics.

Loads configuration from environment variables with smart defaults.
Supports variable interpolation in .env files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables with interpolation support
# This allows using ${VAR} syntax in .env files
load_dotenv(override=False, interpolate=True)


def _expanduser(path_str: str) -> Path:
    """Expand ~ and environment variables in path string."""
    return Path(os.path.expandvars(path_str)).expanduser()


# =============================================================================
# Data Directories
# =============================================================================

# Base directory for all conversation data
CLAUDE_CONVERSATIONS_DIR = _expanduser(
    os.getenv('CLAUDE_CONVERSATIONS_DIR', '~/claude-conversations')
)

# Analysis output directory (defaults to subdirectory of base)
ANALYSIS_OUTPUT_DIR = _expanduser(
    os.getenv('ANALYSIS_OUTPUT_DIR', str(CLAUDE_CONVERSATIONS_DIR / 'analyses'))
)

# Database path (defaults to file in base directory)
DATABASE_PATH = _expanduser(
    os.getenv('DATABASE_PATH', str(CLAUDE_CONVERSATIONS_DIR / 'conversations.db'))
)

# Claude Code directories (hardcoded by Claude Code - cannot be changed)
CLAUDE_CODE_CONFIG_DIR = Path.home() / '.claude'
CLAUDE_CODE_PROJECTS_DIR = CLAUDE_CODE_CONFIG_DIR / 'projects'
CLAUDE_CODE_SETTINGS_FILE = CLAUDE_CODE_CONFIG_DIR / 'settings.json'

# =============================================================================
# Pagination Settings
# =============================================================================

PAGINATION_THRESHOLD = int(os.getenv('PAGINATION_THRESHOLD', '500'))
MESSAGES_PER_PAGE = int(os.getenv('MESSAGES_PER_PAGE', '100'))

# =============================================================================
# Search Configuration
# =============================================================================

SEARCH_RESULTS_PER_PAGE = int(os.getenv('SEARCH_RESULTS_PER_PAGE', '10'))

# =============================================================================
# Display Settings
# =============================================================================

TOOL_RESULT_MAX_LENGTH = int(os.getenv('TOOL_RESULT_MAX_LENGTH', '2000'))

# =============================================================================
# Debug Logging
# =============================================================================

CLAUDE_EXPORT_DEBUG_LOG = _expanduser(
    os.getenv('CLAUDE_EXPORT_DEBUG_LOG', '~/.claude/export-debug.log')
)

# =============================================================================
# LLM API Configuration
# =============================================================================

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-v3.2')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')


# =============================================================================
# Validation and Initialization
# =============================================================================

def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        CLAUDE_CONVERSATIONS_DIR,
        ANALYSIS_OUTPUT_DIR,
        DATABASE_PATH.parent,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def validate_config():
    """Validate configuration and warn about potential issues."""
    issues = []

    # Check if Claude Code directories exist
    if not CLAUDE_CODE_PROJECTS_DIR.exists():
        issues.append(
            f"Claude Code projects directory not found: {CLAUDE_CODE_PROJECTS_DIR}\n"
            f"  Make sure Claude Code is installed and has been run at least once."
        )

    # Check if debug log directory exists
    if not CLAUDE_EXPORT_DEBUG_LOG.parent.exists():
        issues.append(
            f"Debug log directory does not exist: {CLAUDE_EXPORT_DEBUG_LOG.parent}\n"
            f"  The export hook may fail to write debug logs."
        )

    return issues


# =============================================================================
# Helper Functions
# =============================================================================

def get_config_summary() -> str:
    """Get a human-readable summary of current configuration."""
    return f"""
Claude Code Analytics Configuration
====================================

Data Directories:
  Base Directory:      {CLAUDE_CONVERSATIONS_DIR}
  Analysis Output:     {ANALYSIS_OUTPUT_DIR}
  Database:            {DATABASE_PATH}

Claude Code Directories:
  Config Dir:          {CLAUDE_CODE_CONFIG_DIR}
  Projects/Transcripts: {CLAUDE_CODE_PROJECTS_DIR}
  Settings File:       {CLAUDE_CODE_SETTINGS_FILE}

Pagination:
  Threshold:           {PAGINATION_THRESHOLD} messages
  Per Page:            {MESSAGES_PER_PAGE} messages

Search:
  Results Per Page:    {SEARCH_RESULTS_PER_PAGE}

Display:
  Tool Result Max:     {TOOL_RESULT_MAX_LENGTH} chars

Debug:
  Export Log:          {CLAUDE_EXPORT_DEBUG_LOG}

LLM API:
  OpenRouter Key:      {'✓ Set' if OPENROUTER_API_KEY else '✗ Not set'}
  Default Model:       {OPENROUTER_MODEL}
  Google Key:          {'✓ Set' if GOOGLE_API_KEY else '✗ Not set'}
"""


if __name__ == '__main__':
    # When run as a script, display configuration
    print(get_config_summary())

    # Validate and show any issues
    issues = validate_config()
    if issues:
        print("\nConfiguration Issues:")
        print("=" * 50)
        for issue in issues:
            print(f"⚠️  {issue}\n")
    else:
        print("\n✅ Configuration looks good!")
