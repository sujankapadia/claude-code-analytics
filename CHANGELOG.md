# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **FastAPI Backend** - Full REST API replacing direct database access from the Streamlit frontend
  - 22 GET and 4 POST endpoints across 8 routers (projects, sessions, search, analytics, analysis, examples, import, events)
  - SSE (Server-Sent Events) endpoint for real-time updates
  - File watcher service that auto-imports new sessions from `~/.claude/projects/` using `watchfiles`
  - Startup catch-up import for sessions created while the server was offline
  - EventBus service for fan-out of real-time events to connected clients
  - Incremental import service with inline FTS index updates
  - CLI entry point: `claude-code-api` with `--host`, `--port`, `--reload` options

- **React Frontend** - Modern SPA replacing the Streamlit dashboard
  - **Dashboard** — KPI cards, daily activity charts, activity heatmap (day × hour), projects table
  - **Sessions** — Split-view with searchable session list (showing first user message) and detail preview with stats cards
  - **Session Detail** — Full conversation viewer with virtual scrolling (`@tanstack/react-virtual`), collapsible tool cards, minimap navigation, in-conversation search (Cmd+F), token usage bar
  - **Search** — FTS5 search with scope/project/tool filters, search history, keyboard navigation, URL sync
  - **Analytics** — Tool usage distribution, MCP server stats, daily trend charts
  - **Analysis** — LLM-powered session analysis with model selection, searchable session picker, Gist publishing
  - **Examples** — Natural language prompt and session discovery (see below)
  - **Import** — Streaming import with SSE progress
  - **Command Palette** — Cmd+K quick navigation with fuzzy search across pages, projects, sessions, and FTS content search
  - Real-time cache invalidation via SSE (`useEventSource` hook)
  - Dark mode with Tailwind CSS v4 and Base UI headless components

- **Find Examples Feature** — Hybrid FTS + LLM search for prompt and workflow discovery
  - `POST /api/examples/prompts` — Find specific user prompts that demonstrate a technique, shareable as templates
  - `POST /api/examples/sessions` — Find sessions where a workflow or technique was used
  - Natural language queries are decomposed into FTS keywords + tool name patterns
  - FTS narrows to ~20-30 candidates, then LLM (DeepSeek v3.2 via OpenRouter) ranks for relevance
  - Compaction/continuation messages automatically excluded from results
  - Frontend page with Prompts/Sessions toggle, project filter, copy-to-clipboard, and deep links to conversations
  - Minimal LLM cost: ~3-8k input tokens per query

- **Token Counts in Project Summary** - Display total input/output tokens per project on the Browse Sessions page and in the project_summary SQL view
- **Activity & Volume Metrics** - Track active time and text volume across sessions and projects
  - **Active Time Calculation** - Sums time between consecutive messages with idle gaps capped at 5 minutes, giving a realistic measure of hands-on time (wall clock duration is unreliable for re-entered sessions)
  - **Text Volume Analysis** - Character counts for user text and assistant text (including tool inputs/results), with ratios and percentages
  - **Session-Level Metrics** (Browse Sessions page) - Active time, message counts (user:assistant), text ratio, user/assistant text with percentages
  - **Project-Level Totals** (Browse Sessions page) - Aggregate active time, average active time per session, total text volume across all sessions in the selected project
  - **Aggregate Dashboard** (Analytics page) - Total active time, average per session, session count, total user/assistant text, text ratio, per-project breakdown table and bar chart
  - **Formatting Utilities** - New `format_utils.py` module with `format_duration()`, `format_char_count()`, and `format_percentage()` helpers
  - Three new database service methods: `get_active_time_for_session()`, `get_text_volume_for_session()`, `get_aggregate_activity_metrics()`
  - Comprehensive test coverage (23 formatting tests, 9 activity metrics tests)

- **Search Scope Tabs** — Scope selector (All/Messages/Tool Input/Tool Results) promoted to always-visible tabs below the search bar
- **Conversation Role Filter** — Filter messages by role (All/User/Assistant) in the conversation viewer
- **Analysis Scoping UI** — Scope analysis to entire session, time range, or search hit context with configurable context window
- **Generic OpenAI-Compatible Provider** — Model selection UI supports OpenRouter, Ollama, and any OpenAI-compatible API

### Changed
- **Conversation Viewer** — Empty user messages (tool-result acknowledgments with no text) are now hidden, reducing noise by ~30%
- **Sessions Page** — Session list shows first user message instead of UUID; added search filter
- **Analysis Page** — Session dropdown replaced with searchable session picker (Combobox)
- **Entry Points** — `claude-code-analytics` now launches the FastAPI + React app (port 8000); `claude-code-api` is an alias
- **Install Script** — Updated for React + FastAPI stack: checks Node.js 18+/npm, runs `npm install && npm run build`
- **Uninstall Script** — Now cleans frontend build artifacts (`frontend/dist/`, `frontend/node_modules/`)

### Fixed
- **FTS5 query escaping** — Properly escape special characters in user queries to prevent SQLite FTS5 syntax errors
- **Subagent project association** — Fix project ID resolution for sessions imported from subagent directories
- **Project name decoding** — Correctly decode URL-encoded project paths for display
- **SessionEnd hook timeout** - Remove unnecessary `sleep 1` in `export-conversation.sh` that caused the hook to exceed its timeout window and get cancelled
- **SPA routing** — Fix 404 on direct navigation to React routes in production (replaced StaticFiles mount with catch-all fallback)
- **Activity heatmap timezone** — Use local time instead of UTC for day-of-week and hour calculations

### Removed
- **Streamlit dashboard** — Legacy frontend removed; React dashboard is now the only UI
- **Streamlit dependencies** — Removed `streamlit`, `pandas`, `altair` from package dependencies
- **`run_dashboard.sh`** — Obsolete Streamlit launcher script deleted
- **`claude-code-streamlit`** — Entry point removed

## [0.1.0] - 2025-12-30

### Added
- **Pre-commit Hooks** - Automated code quality checks before commits
  - Black formatter (100 character line length)
  - Ruff linter with auto-fix capabilities
  - Bandit security scanner
  - Mypy type checker (manual-only, non-blocking)
  - Standard file checks (trailing whitespace, YAML/JSON validation, large files, merge conflicts, private keys)
  - Comprehensive tool configurations in `pyproject.toml`
- **Batch Insert Test Suite** - Comprehensive testing for database optimization
  - Tests for `executemany()` batch operations
  - Incremental import validation
  - Session metadata accuracy verification
  - Performance measurement and comparison
- **Logging Documentation** - Standards and conventions for consistent logging
  - `LOGGING.md` with setup patterns and usage guidelines
  - Benefits of logging module over print statements
  - Examples for programmatic log level control
- **GitHub Gist Publishing with Security Scanning** - Share analysis results as GitHub Gists with automatic security checks
  - **Multi-layer Security Scanner** - Detect secrets, PII, and sensitive data before publishing
    - Gitleaks integration (350+ secret patterns: API keys, tokens, credentials)
    - Regex pattern scanner (emails, phone numbers, SSNs, credit cards, private IPs)
    - Severity-based blocking (CRITICAL/HIGH blocks, MEDIUM/LOW warns)
    - Configurable allowlists for false positives
  - **GistPublisher Service** - GitHub API integration for gist creation
    - Automatic security scanning before publication
    - Support for analysis + optional session transcript
    - Public or secret gist visibility options
    - Auto-generated README with metadata and traceability
  - **Analysis Page UI** - Publish button with configuration options
    - Real-time security scan with progress indicators
    - Detailed security findings with severity breakdown
    - Gist configuration (visibility, session inclusion, description)
    - Success/error handling with gist URL display
  - **Configuration** - GitHub token management via `.env`
  - **Testing** - Comprehensive test suite (unit, integration, live)
    - 19 unit tests for scanner components
    - Integration tests with realistic content samples
    - Live tests with real GitHub API (all 5/5 passed)

- **Analysis Scoping Features** - Analyze specific portions of conversations instead of entire sessions
  - **Time-Range Filtering** - Analyze messages within specific date/time ranges
    - Database methods for filtering messages and tool uses by timestamp
    - Token estimation with tiktoken for cost preview
    - Interactive date/time pickers in UI
  - **Search Hit Context Window** - Analyze search results with surrounding context
    - Configurable context window (messages before/after)
    - Integration with search page via "Analyze with Context" buttons
    - Highlighted search hit markers in formatted transcripts
    - Message-level deep linking from search results
  - Session-grouped search pagination with proper session discovery
  - Token usage preview before running analysis

- **Interactive Token Timeline Visualization** - Visual analysis of token usage over time
  - Cumulative token usage chart showing growth throughout conversation
  - Hover tooltips with per-message token breakdowns
  - Input vs output token visualization

- **GitHub Pages Deployment** - Project website and documentation
  - Landing page with feature overview and getting started guide
  - Social media preview support (Open Graph, Twitter Card metadata)
  - Reorganized documentation structure optimized for web viewing
  - Jekyll configuration for proper GitHub Pages rendering

- **Custom Streamlit Styling** - Improved visual design
  - Enhanced colors, spacing, and typography
  - Better readability and user experience
  - Consistent design language across all pages

- **Technical Documentation**
  - Analysis scoping feature specification (ANALYSIS_SCOPING_FEATURE.md)
  - Updated SECURITY.md for unreleased project status

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
  - Customizable export filenames (user can edit before download/save)

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
  - Project identification explanation (how Claude Code uses directory paths)
  - Database schema documentation
  - Search implementation details
  - Deep linking technical guide
  - Custom prompt creation guide

### Changed
- **Code Quality Improvements** - Applied across all Python files (42 files modified)
  - Modernized type hints (`typing.Dict` → `dict`, `typing.List` → `list`, `typing.Tuple` → `tuple`)
  - Improved exception handling with proper exception chaining (`raise ... from err`)
  - Optimized import ordering and removed unused imports
  - Black code formatting with 100 character line length
  - Fixed trailing whitespace and end-of-file issues
- **Logging Standardization** - Production scripts now use Python's logging module
  - `create_database.py` - Replaced print statements with structured logging
  - `create_fts_index.py` - Replaced print statements with structured logging
  - Configurable log levels for programmatic usage
- README restructured for first-time users with clear prerequisites and 3-step quick start
- README: Added Development section with pre-commit setup instructions
- Analytics Dashboard: "Sessions by Project" chart changed to "Messages by Project"
- Database queries: Project summaries ordered by message count
- Configuration: All hardcoded paths moved to centralized config module
- CLI workflow: Prioritize package commands over direct Python script execution

### Fixed
- **FTS5 Query Safety** - Added error handling for invalid FTS5 syntax in user queries
  - `search_fts.py` - Catch and provide helpful error messages for syntax errors
  - `database_service.py` - Centralized FTS error handling with `_execute_fts_query()` helper
  - Prevents crashes from malformed queries with unmatched quotes or invalid operators
- **Timestamp Handling** - Defensive normalization for inconsistent timestamp formats
  - Added `normalize_timestamp()` function in `import_conversations.py`
  - Handles ISO 8601 strings, Unix epoch (seconds), Unix epoch (milliseconds)
  - Validates and logs warnings for invalid timestamps instead of crashing
- **Database Performance** - Optimized row-by-row inserts to use batch operations
  - `import_conversations.py` - Changed to `executemany()` for messages and tool uses
  - 5-10x performance improvement for large sessions
  - Maintains data integrity with proper transaction handling
- **Search Pagination Bugs** - Critical fixes to session-grouped search results
  - Missing GROUP BY in "All" scope causing only 1 session to appear instead of 3
  - Session filtering now uses SQL WHERE IN clause instead of Python filtering
  - "All" scope now correctly returns superset of all result types
  - Search snippets now properly highlight matched text in all scopes
- Projects missing from analytics chart due to ordering mismatch
- Import script auto-creates database if missing
- Search index automatically rebuilds after imports (no stale data)
- Hook script uses standard config location (not hardcoded paths)
- **File permissions** - Sensitive files now created with secure permissions (600/700)

### Security
- **PATH Injection Prevention** - Use `shutil.which()` to resolve full executable paths
  - `GitleaksScanner` - Resolves and validates gitleaks executable path on initialization
  - `cli.py` - Validates streamlit executable before launching dashboard
  - `analysis.py` - Resolves git executable path for commit ID retrieval
  - Prevents PATH manipulation attacks by using absolute paths for all subprocess calls
  - Improves cross-platform compatibility (Windows, macOS, Linux)
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
