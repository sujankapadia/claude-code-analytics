# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
