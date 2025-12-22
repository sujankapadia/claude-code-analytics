# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Homebrew formula for easy installation on macOS and Linux
- Platform compatibility documentation
- Packaging considerations documentation

## [1.0.0] - TBD

### Added
- **Streamlit Dashboard** - Interactive web UI for browsing, searching, and analyzing conversations
  - Session Browser - View and filter all conversations
  - Conversation Viewer - Terminal-style interface with tool calls inline
  - Search Page - Full-text search powered by SQLite FTS5
  - Analytics Dashboard - Visual insights (charts, metrics, trends)
  - AI Analysis Page - Run analysis with 300+ models via OpenRouter or Gemini

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

- **Configuration System** - Centralized, XDG-compliant configuration
  - Standard location: `~/.config/claude-code-analytics/.env`
  - Variable interpolation support
  - Smart defaults with derived paths
  - All settings optional except API keys (for AI analysis)

- **CLI Tools**
  - create_database.py - Create database schema
  - import_conversations.py - Import conversations with auto-create DB and FTS rebuild
  - create_fts_index.py - Create/rebuild search index (now automatic)
  - search_fts.py - Command-line search interface
  - analyze_session.py - AI-powered session analysis from CLI
  - pretty-print-transcript.py - Convert JSONL to readable text

- **AI Analysis Features**
  - OpenRouter integration (300+ models)
  - Google Gemini integration
  - Curated model selection (13 latest premium models)
  - Pre-built analysis types: Technical Decisions, Error Patterns, AI Agent Usage
  - Custom analysis with user prompts
  - Jinja2-based prompt templates
  - Export analysis as markdown

- **Import Page** - Streamlit UI for importing data
  - Detects new conversations and updates
  - Progress tracking
  - Database statistics display
  - Auto-creates database if needed
  - Auto-rebuilds search index after import

- **Documentation**
  - Comprehensive README with user journey focus
  - Database schema documentation
  - Search implementation details
  - Deep linking technical guide
  - Custom prompt creation guide
  - Homebrew packaging plan
  - Platform compatibility analysis
  - Packaging considerations

### Changed
- Analytics Dashboard: Changed "Sessions by Project" chart to "Messages by Project" (more meaningful metric)
- Database queries: Order project summaries by message count (not session count)
- README: Restructured to position tool as analytics platform (not scripts)
- Configuration: All hardcoded paths moved to centralized config module

### Fixed
- Projects missing from analytics chart due to ordering mismatch
- Import script now auto-creates database if missing
- Search index automatically rebuilds after imports (no stale data)
- Hook script uses standard config location (not hardcoded paths)

### Security
- All API keys stored in config file (not environment variables)
- Config file location follows XDG standard
- No sensitive data stored in database
- All data stays local (no cloud sync)

## Release History

### Version Numbering
- **1.0.0** - Initial Homebrew release
- **1.x.x** - New features (backward compatible)
- **2.x.x** - Breaking changes (if needed)

### Upgrade Notes
- First release - no upgrade path needed
- Future versions will document migration steps here

---

[Unreleased]: https://github.com/sujankapadia/claude-code-utils/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/sujankapadia/claude-code-utils/releases/tag/v1.0.0
