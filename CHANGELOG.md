# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Python Package** - Installable via pip with setuptools
  - Package name: `claude-code-analytics`
  - Entry points for CLI commands
  - Automatic dependency installation
  - Editable installation support for development

- **CLI Commands** - Convenient command-line tools
  - `claude-code-analytics` - Launch interactive dashboard
  - `claude-code-import` - Import conversations (auto-creates DB and search index)
  - `claude-code-search` - Search conversations from command line
  - `claude-code-analyze` - Run AI-powered analysis from command line

- **Streamlit Dashboard** - Interactive web UI for browsing, searching, and analyzing conversations
  - Session Browser - View and filter all conversations
  - Conversation Viewer - Terminal-style interface with tool calls inline
  - Search Page - Full-text search powered by SQLite FTS5
  - Analytics Dashboard - Visual insights (charts, metrics, trends)
  - AI Analysis Page - Run analysis with 300+ models via OpenRouter or Gemini
  - Import Page - UI for importing data with progress tracking

- **Automatic Export System** - SessionEnd hooks for Claude Code
  - export-conversation.sh - Bash hook script for automatic conversation export
  - Exports both JSONL (raw) and pretty-printed text formats
  - Organized by project directory structure
  - Handles session resumption correctly

- **Database System** - SQLite-based storage with full-text search
  - Normalized schema (projects, sessions, messages, tool_uses)
  - FTS5 full-text search index
  - Pre-aggregated views for performance
  - Incremental import support (updates existing sessions)
  - Auto-creation on first import

- **Configuration System** - Centralized, XDG-compliant configuration
  - Standard location: `~/.config/claude-code-analytics/.env`
  - Variable interpolation support
  - Smart defaults with derived paths
  - All settings optional except API keys (for AI analysis)

- **AI Analysis Features**
  - OpenRouter integration (300+ models)
  - Google Gemini integration
  - Curated model selection (13 latest premium models)
  - Pre-built analysis types: Technical Decisions, Error Patterns, AI Agent Usage
  - Custom analysis with user prompts
  - Jinja2-based prompt templates
  - Export analysis as markdown

- **Installation Script** - Automated setup (`install.sh`)
  - Creates required directories
  - Installs Python package and dependencies
  - Configures Claude Code settings.json with SessionEnd hook
  - Sets up hook scripts with proper permissions
  - Creates configuration file at `~/.config/claude-code-analytics/.env`

- **Uninstallation Script** - Clean removal (`uninstall.sh`)
  - Removes Python package
  - Preserves user data and configuration by default
  - Options for complete removal (`--complete`, `--purge`)

- **Python Scripts** - Direct script access for advanced usage
  - create_database.py - Create database schema
  - import_conversations.py - Import conversations with auto-create DB and FTS rebuild
  - create_fts_index.py - Create/rebuild search index
  - search_fts.py - Command-line search interface
  - analyze_session.py - AI-powered session analysis
  - pretty-print-transcript.py - Convert JSONL to readable text

- **Documentation**
  - Comprehensive README with prerequisites and quick start
  - Database schema documentation
  - Search implementation details
  - Deep linking technical guide
  - Custom prompt creation guide

### Changed
- README restructured for first-time users with clear prerequisites and 3-step quick start
- Analytics Dashboard: "Sessions by Project" chart changed to "Messages by Project"
- Database queries: Project summaries ordered by message count
- Configuration: All hardcoded paths moved to centralized config module
- CLI workflow: Prioritize package commands over direct Python script execution

### Fixed
- Projects missing from analytics chart due to ordering mismatch
- Import script auto-creates database if missing
- Search index automatically rebuilds after imports (no stale data)
- Hook script uses standard config location (not hardcoded paths)
- **File permissions** - Sensitive files now created with secure permissions (600/700)

### Security
- **Secure file permissions** - All sensitive files now use restrictive permissions
  - Configuration file (`.env` with API keys): 600 (owner read/write only)
  - Database (`conversations.db`): 600 (owner read/write only)
  - Exported conversations (`.jsonl`, `.txt`): 600 (owner read/write only)
  - Settings backup: 600 (owner read/write only)
  - Data directories: 700 (owner full access only)
  - Prevents unauthorized access to sensitive data on multi-user systems
- All API keys stored in config file (not environment variables)
- Config file location follows XDG standard
- No sensitive data stored in database
- All data stays local (no cloud sync)

### Removed
- Homebrew packaging support (too complex, unreliable builds)
- Homebrew formula and tap repository
- Homebrew-related documentation
