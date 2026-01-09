# Claude Code Analytics

[![Tests](https://github.com/sujankapadia/claude-code-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/sujankapadia/claude-code-analytics/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/sujankapadia/claude-code-analytics/branch/main/graph/badge.svg)](https://codecov.io/gh/sujankapadia/claude-code-analytics)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A analysis tool for [Claude Code](https://claude.com/claude-code) that automatically captures, archives, and analyzes your AI development conversations. Features an interactive dashboard, full-text search, and AI-powered insights across all your sessions.

## What It Does

Claude Code Analytics transforms your AI development workflow into actionable insights:
- **Automatically captures** every conversation when you exit Claude Code
- **Stores and indexes** conversations in a searchable SQLite database
- **Provides an interactive dashboard** to explore patterns, tool usage, and decisions
- **Enables AI-powered analysis** of your development sessions using 300+ LLM models

## Prerequisites

Before installing, you need:

- **[Claude Code](https://claude.com/claude-code)** - The AI coding assistant (this tool captures its conversations)
- **Python 3.9+** - Check with `python3 --version`
- **jq** - JSON processor for installation script
  - macOS: `brew install jq`
  - Linux: `apt-get install jq` or `yum install jq`

## Compatibility

**Testing Status**: This is an alpha release (v0.1.0) that has been tested on:
- **macOS 14.7** (Sonoma)
- **Python 3.9-3.12** (CI tested on Ubuntu and macOS)
- **Claude Code 2.0.21**

**Platform Support**:
- ✅ **macOS**: Fully tested and supported
- ⚠️ **Linux**: Likely compatible (CI tests pass on Ubuntu) but not extensively tested on user systems
- ❓ **Windows**: Untested - hook scripts may require WSL or adaptation

If you encounter platform-specific issues, please [report them on GitHub](https://github.com/sujankapadia/claude-code-analytics/issues).

## Quick Start

### 1. Install

```bash
git clone https://github.com/sujankapadia/claude-code-analytics.git
cd claude-code-analytics
./install.sh
```

The installer automatically:
- Installs the Python package and all dependencies
- Sets up hooks to capture conversations
- Creates the CLI commands
- Configures Claude Code settings

### 2. Import Existing Conversations

```bash
claude-code-import
```

This creates the database, imports all existing conversations, and builds the search index.

### 3. Launch Dashboard

```bash
claude-code-analytics
```

The dashboard opens at `http://localhost:8501`. Start exploring your conversations!

### 4. (Optional) Configure AI Analysis

To enable AI-powered analysis features, add an API key to your config file:

```bash
# Edit the config file
nano ~/.config/claude-code-analytics/.env

# Add one of these:
OPENROUTER_API_KEY=sk-or-your-key-here  # For 300+ models
GOOGLE_API_KEY=your-key-here             # For Gemini models
```

Get API keys from [OpenRouter](https://openrouter.ai/keys) or [Google AI Studio](https://aistudio.google.com/app/apikey).

That's it! New conversations will be automatically captured when you exit Claude Code sessions.

> **⚠️ Important: Transcript Retention**
>
> Claude Code automatically removes transcripts for sessions that have been inactive for more than **30 days** by default. This helps manage disk space but means older conversations may be deleted before you archive them.
>
> To change this retention period, edit `~/.claude/settings.json` and add:
> ```json
> {
>   "cleanupPeriodDays": 90
> }
> ```
> Set this to a higher value (e.g., 90, 180, or 365 days) to keep transcripts longer, or set it to `0` to disable automatic cleanup entirely.

---

## Key Features

### 📊 Interactive Dashboard

The Streamlit-based dashboard is your primary interface for exploring conversations:

- **Session Browser** - View, filter, and navigate all your Claude Code sessions with pagination support
- **Conversation Viewer** - Terminal-style interface that faithfully recreates your sessions:
  - Inline tool calls and results
  - Role-based filtering (user/assistant)
  - Content search within sessions
  - Token usage display
  - Deep linking to specific messages from search results
- **Analytics Dashboard** - Visual insights into your development patterns:
  - Messages and token usage over time
  - Tool usage distribution and error rates
  - Project statistics (sessions, messages, tool uses, activity timeline)
  - Daily activity trends
- **Full-Text Search** - FTS5-powered search across all messages, tool inputs, and tool results:
  - Scope filtering (messages, tool inputs/results)
  - Project and date range filters
  - Highlighted search results with context
  - Direct navigation to matching messages
  - MCP tool usage analysis
- **AI-Powered Analysis** - Run sophisticated analysis on any session:
  - Technical decisions extraction
  - Error pattern analysis
  - AI agent usage patterns
  - Custom analysis with your own prompts
  - 300+ model selection via OpenRouter or Gemini

### 🔍 Search & Discovery

- **Full-text search** - Lightning-fast FTS5 search across millions of tokens
- **Deep linking** - Search results link directly to specific messages in conversations
- **Advanced filtering** - Filter by project, date range, role, tool name
- **MCP tool tracking** - Dedicated analytics for MCP server usage
- **Message-level precision** - Every tool use is linked to its exact message

### 💾 Automatic Archiving

- **Hook-based capture** - Conversations automatically export on session end
- **Dual-format storage** - Raw JSONL for programmatic access, formatted text for reading
- **Project organization** - Conversations organized by the project directory they occurred in
- **Incremental imports** - Database updates efficiently with only new content
- **Session resumption** - Correctly handles resumed sessions and updates

### 🤖 AI-Powered Analysis

- **300+ models** - Access entire OpenRouter catalog or use Google Gemini directly
- **Curated selection** - Quick-select from 13 newest premium models (2025):
  - **Budget**: Qwen3, Llama 4 Scout, Mistral Small ($0.06-$0.10/1M tokens)
  - **Balanced**: DeepSeek V3.2, Gemini 3 Flash, Claude Haiku 4.5 ($0.26-$1.75/1M tokens)
  - **Premium**: Gemini 3 Pro, Claude Sonnet 4.5, Grok 4, Claude Opus 4.5 ($2-$5/1M tokens)
- **Pre-built analysis types**:
  - Technical Decisions - Extract decisions, alternatives, and reasoning
  - Error Patterns - Identify recurring issues, root causes, resolutions
  - AI Agent Usage - Understand how you use AI for prototyping and discovery
  - Custom - Write your own analysis prompts
- **Templated prompts** - Jinja2-based templates for easy customization
- **Export results** - Save analysis as markdown files
- **GitHub Gist publishing** - Share analysis with automatic security scanning:
  - Multi-layer scanning (Gitleaks + Regex patterns) for secrets, PII, and sensitive data
  - Blocks publication on CRITICAL/HIGH severity findings
  - Optional session transcript inclusion
  - Public or secret gist visibility
  - Auto-generated README with metadata and traceability

### 📈 Comprehensive Analytics

- **Token tracking** - Input, output, and cache metrics (creation, read, 5m, 1h)
- **Tool usage stats** - Track which tools you use most, error rates, session distribution
- **Daily trends** - Message volume, token usage, and activity over time
- **Project insights** - Compare activity levels across different projects

## Quick Start

### 1. Install

```bash
git clone https://github.com/yourusername/claude-code-analytics.git
cd claude-code-analytics
./install.sh
```

The installer sets up hooks, creates directories, and configures Claude Code to automatically export conversations.

### 2. Create Database

```bash
# Create database schema
python3 scripts/create_database.py

# Import existing conversations
python3 scripts/import_conversations.py

# Create search index
python3 scripts/create_fts_index.py
```

### 3. Launch Dashboard

```bash
./run_dashboard.sh
```

The dashboard opens at `http://localhost:8501`. Start exploring your conversations!

### 4. (Optional) Configure AI Analysis

To use AI-powered analysis features:

```bash
# Option 1: OpenRouter (300+ models)
export OPENROUTER_API_KEY="sk-or-your-key-here"

# Option 2: Google Gemini (direct)
export GOOGLE_API_KEY="your-api-key-here"
```

Get API keys from [OpenRouter](https://openrouter.ai/keys) or [Google AI Studio](https://aistudio.google.com/app/apikey).

## Configuration

Claude Code Analytics uses a centralized configuration system with smart defaults. All settings are stored in `~/.config/claude-code-analytics/.env`.

### Configuration File Location

The configuration file is automatically created during installation at:
```
~/.config/claude-code-analytics/.env
```

This location follows the [XDG Base Directory specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html).

### Configuration Variables

The `.env` file supports all standard environment variable syntax, including variable interpolation using `${VAR}` syntax.

#### Data Directories

```bash
# Base directory for all conversation data
# All other paths default to subdirectories of this unless explicitly overridden
CLAUDE_CONVERSATIONS_DIR=~/claude-conversations

# Optional: Override specific directories
ANALYSIS_OUTPUT_DIR=${CLAUDE_CONVERSATIONS_DIR}/analyses
DATABASE_PATH=${CLAUDE_CONVERSATIONS_DIR}/conversations.db
```

#### Pagination Settings

```bash
# Number of messages before enabling pagination in conversation viewer
PAGINATION_THRESHOLD=500

# Number of messages to show per page when paginated
MESSAGES_PER_PAGE=100
```

#### Search Configuration

```bash
# Number of search results to show per page
SEARCH_RESULTS_PER_PAGE=10
```

#### Display Settings

```bash
# Maximum length of tool results to display (characters)
# Results longer than this will be truncated
TOOL_RESULT_MAX_LENGTH=2000
```

#### Debug Logging

```bash
# Location of export hook debug log
CLAUDE_EXPORT_DEBUG_LOG=~/.claude/export-debug.log
```

#### LLM API Configuration (Required for AI Analysis)

```bash
# OpenRouter API key (access 300+ models)
# Get your key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-your-key-here

# Default model for CLI analysis (when --model not specified)
OPENROUTER_MODEL=deepseek/deepseek-v3.2

# Google Gemini API key (alternative to OpenRouter)
# Get your key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your-api-key-here
```

#### GitHub Integration (Optional - for Gist Publishing)

```bash
# GitHub Personal Access Token for publishing analysis as gists
# Get your token from: https://github.com/settings/tokens/new
# Required scope: 'gist' (create gists)
GITHUB_TOKEN=ghp_your_token_here
```

### Required vs Optional Settings

**Required for basic features** (browse, search, analytics):
- None! The defaults work out of the box.

**Required for AI analysis features**:
- Either `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`

**Required for GitHub Gist publishing**:
- `GITHUB_TOKEN` - Personal Access Token with `gist` scope

**Optional customization**:
- All other settings have sensible defaults
- Customize data directories if you want conversations stored elsewhere
- Adjust pagination/display settings for personal preferences

### Customizing Configuration

Edit the configuration file to customize settings:

```bash
# Open configuration file in your default editor
${EDITOR:-nano} ~/.config/claude-code-analytics/.env
```

**Example customizations:**

```bash
# Store conversations on external drive
CLAUDE_CONVERSATIONS_DIR=~/Dropbox/claude-conversations

# Increase pagination threshold for faster sessions
PAGINATION_THRESHOLD=1000
MESSAGES_PER_PAGE=200

# Show more search results per page
SEARCH_RESULTS_PER_PAGE=25

# Show longer tool results without truncation
TOOL_RESULT_MAX_LENGTH=5000
```

### Variable Interpolation

The configuration system supports referencing other variables using `${VAR}` syntax:

```bash
# Set base directory
CLAUDE_CONVERSATIONS_DIR=~/my-custom-location

# Derived paths automatically use the base
ANALYSIS_OUTPUT_DIR=${CLAUDE_CONVERSATIONS_DIR}/analyses
DATABASE_PATH=${CLAUDE_CONVERSATIONS_DIR}/conversations.db
```

### Environment Variables

You can override configuration file settings using environment variables:

```bash
# Temporary override for this session
export OPENROUTER_MODEL="anthropic/claude-sonnet-4.5"
./run_dashboard.sh

# Permanent override in shell profile (~/.bashrc, ~/.zshrc)
echo 'export OPENROUTER_API_KEY="sk-or-your-key"' >> ~/.zshrc
```

### Configuration Reference

For a complete list of all configuration variables with documentation, see [`.env.example`](.env.example) in the repository.

## Using the Dashboard

### Browse Sessions

The **Browse Sessions** page shows all your conversations:
- Filter by project, date range, or minimum message count
- Sort by date or activity level
- Pagination for large conversation histories
- Click any session to view full conversation

### Search Conversations

The **Search** page provides powerful full-text search:
- Search across messages, tool inputs, or tool results
- Filter by project, date range, or specific tools
- View MCP tool usage statistics
- Click search results to jump directly to matching messages in context

### View Analytics

The **Analytics Dashboard** provides visual insights:
- **Tool Usage** - Distribution of top 10 tools, error rates, and session usage
- **Daily Activity** - Messages, tokens, and sessions over time (configurable time range)
- **Token Usage** - Input vs output tokens with stacked area chart
- **Project Statistics** - Sessions, messages, tool uses, and activity timeline per project (sorted by message volume)

### Run AI Analysis

The **AI Analysis** page lets you analyze sessions with LLMs:
1. Select a session from the dropdown
2. Choose analysis type or write custom prompt
3. Select model (browse 300+ options or pick from curated list)
4. Adjust temperature (default: 0.1 for deterministic analysis)
5. Run analysis and optionally export to markdown

### Publish to GitHub Gists

After running an analysis, you can publish your results as a GitHub Gist with automatic security scanning:

1. **Configure GitHub Token** - Add `GITHUB_TOKEN` to `~/.config/claude-code-analytics/.env`
2. **Run Analysis** - Complete an analysis on any session
3. **Configure Gist Options**:
   - Choose visibility (Secret/unlisted or Public)
   - Optionally include raw session transcript
   - Customize gist description
4. **Scan & Publish** - Click "Scan & Publish to Gist" button
5. **Review Results**:
   - ✅ **Safe**: Gist is published with URL and scan summary
   - ❌ **Blocked**: Security findings prevent publication (review and remove sensitive data)

**Security Scanning**:
- **Gitleaks** - Detects 350+ secret patterns (API keys, tokens, credentials)
- **Regex Patterns** - Catches PII (emails, phone numbers, SSNs, credit cards)
- **Severity Levels**:
  - CRITICAL/HIGH → Blocks publication
  - MEDIUM/LOW → Informational warnings only

The gist includes:
- Analysis result with full metadata and traceability
- Optional session transcript
- Auto-generated README with tool attribution

## Advanced Usage

### CLI Tools

The installation provides several CLI commands for working with your conversations:

#### Search Conversations

```bash
claude-code-search "error handling"
```

#### Run Analysis from CLI

```bash
# Analyze technical decisions
claude-code-analyze <session-id> --type=decisions

# Specify model and save output
claude-code-analyze <session-id> \
  --type=errors \
  --model=anthropic/claude-sonnet-4.5 \
  --output=analysis.md

# Custom analysis
claude-code-analyze <session-id> \
  --type=custom \
  --prompt="Summarize key technical insights"
```

**Popular models:**
- `deepseek/deepseek-v3.2` - Best balance (default, $0.26/1M)
- `anthropic/claude-sonnet-4.5` - Highest quality ($3.00/1M)
- `openai/gpt-5.2-chat` - Latest GPT ($1.75/1M)
- `google/gemini-3-flash-preview` - 1M context window ($0.50/1M)

#### Import New Conversations

Run the import command anytime to update the database with new conversations:

```bash
claude-code-import
```

The command automatically:
- Detects existing sessions
- Imports only new messages
- Updates session metadata (end times, message counts)
- Preserves all existing data with zero duplicates
- Works efficiently on active or completed sessions

### Using Python Scripts Directly

If you prefer to use the Python scripts directly instead of CLI commands:

```bash
# Search
python3 scripts/search_fts.py "error handling"

# Analyze
python3 scripts/analyze_session.py <session-id> --type=decisions

# Import
python3 scripts/import_conversations.py
```

### Manual Export

Convert JSONL transcripts to readable text format:

```bash
~/.claude/scripts/pretty-print-transcript.py /path/to/transcript.jsonl output.txt

# Or via stdin/stdout
cat transcript.jsonl | ~/.claude/scripts/pretty-print-transcript.py > output.txt
```

### Custom Analysis Prompts

Create custom analysis templates in `prompts/`:

1. Create a new `.md` file with your Jinja2 template
2. Add metadata to `prompts/metadata.yaml`
3. Use from dashboard or CLI with `--type=your_template_name`

See `prompts/README.md` for detailed instructions.

## How It Works

### Architecture

```
Claude Code Session
       ↓
SessionEnd Hook (export-conversation.sh)
       ↓
~/claude-conversations/
  ├── project-name/
  │   ├── session-YYYYMMDD-HHMMSS.jsonl  (raw data)
  │   └── session-YYYYMMDD-HHMMSS.txt    (readable format)
       ↓
Import Script (import_conversations.py)
       ↓
SQLite Database (conversations.db)
  ├── projects
  ├── sessions
  ├── messages
  ├── tool_uses
  └── fts_messages (full-text search index)
       ↓
Streamlit Dashboard
  ├── Browse & filter sessions
  ├── Search conversations
  ├── View analytics
  └── Run AI analysis
```

### Hook System

The `export-conversation.sh` hook runs automatically when you exit Claude Code:

1. Receives current working directory and transcript path
2. Finds the most recent transcript (handles session resumption)
3. Creates project-specific directory structure
4. Copies JSONL file with timestamp
5. Generates human-readable text version
6. Logs to `~/.claude/export-debug.log`

### Database Schema

The SQLite database uses a normalized schema:

- **projects** - Unique project directories
- **sessions** - Conversation sessions with metadata
- **messages** - Individual messages with token tracking
- **tool_uses** - Tool calls linked to messages via `message_index`
- **fts_messages** - FTS5 full-text search index
- **Views** - Pre-aggregated statistics for performance

See the technical documentation in `docs/technical/` for more details.

### Project Identification

**Important**: Claude Code uses the **working directory path** as the project identifier, not a separate project name or git repository name.

When you run `claude-code` in a directory like `/Users/username/dev/my-project`, Claude Code:

1. **Encodes the path** by replacing `/` with `-`:
   - `/Users/username/dev/my-project` → `-Users-username-dev-my-project`

2. **Stores sessions** in `~/.claude/projects/{encoded-path}/`:
   ```
   ~/.claude/projects/
     └── -Users-username-dev-my-project/
         ├── session-uuid-1.jsonl
         ├── session-uuid-2.jsonl
         └── ...
   ```

3. **Analytics tool decodes** the path back to display in the dashboard:
   - `project_id` (database): `-Users-username-dev-my-project` (as stored by Claude Code)
   - `project_name` (display): `/Users/username/dev/my-project` (decoded for readability)

This means:
- **Same directory = same project** across all your sessions
- Different paths to the same repo = different projects (e.g., `/home/user/project` vs `/home/user/repos/project`)
- Subdirectories are treated as separate projects (e.g., `/project` vs `/project/subdir`)

The analytics dashboard groups all conversations by these directory paths, so you'll see all your work for a specific codebase location together.

### File Organization

Exported conversations are organized by project:

```
~/claude-conversations/
├── project-name-1/
│   ├── session-20250113-143022.jsonl
│   ├── session-20250113-143022.txt
│   ├── session-20250113-151430.jsonl
│   └── session-20250113-151430.txt
├── project-name-2/
│   └── session-20250114-091500.jsonl
└── conversations.db
```

### Readable Text Format

The generated `.txt` files provide a clean, readable format:

```
═══════════════════════════════════════════════════════════════
USER (2025-01-13 14:30:22)
───────────────────────────────────────────────────────────────
Can you help me fix the bug in the authentication module?

═══════════════════════════════════════════════════════════════
CLAUDE (2025-01-13 14:30:24)
───────────────────────────────────────────────────────────────
I'll help you fix the authentication bug. Let me first examine the
authentication module to understand the issue.

[Tool: Read]
$ Read file_path=/path/to/auth.js

[Tool Result]
1  function authenticate(user, password) {
2    if (user && password) {
3      return true;
4    }
5  }
```

### Manual Installation

If you need to install manually or want to understand what the installer does:

#### 1. Create directories

```bash
mkdir -p ~/.claude/scripts
mkdir -p ~/claude-conversations
```

#### 2. Copy scripts

```bash
cp hooks/export-conversation.sh ~/.claude/scripts/
cp scripts/pretty-print-transcript.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/export-conversation.sh
chmod +x ~/.claude/scripts/pretty-print-transcript.py
```

#### 3. Configure hook

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/scripts/export-conversation.sh"
          }
        ]
      }
    ]
  }
}
```

If you have existing hooks, merge the `SessionEnd` entry into your existing `hooks` object.

#### 4. Install Python package and dependencies

```bash
# From the repository directory
pip install -e .

# This installs the package and all dependencies, and creates the CLI commands
```

### Troubleshooting

#### Conversations not exporting

Check the debug log:
```bash
cat ~/.claude/export-debug.log
```

Common issues:
- Hook not configured in `~/.claude/settings.json`
- Scripts not executable (`chmod +x`)
- Incorrect paths in settings

#### Permission errors

Ensure directories are writable:
```bash
chmod 755 ~/claude-conversations
chmod 755 ~/.claude/scripts
```

#### Import errors

If database import fails:
- Verify JSONL files exist in `~/claude-conversations/`
- Check file permissions
- Ensure Python 3.9+ is installed
- Run with verbose output: `claude-code-import -v`

#### Dashboard not launching

- Install dependencies: `pip install streamlit pandas altair`
- Check port 8501 is available
- Try alternate port: `streamlit run streamlit_app/app.py --server.port=8502`

## Project Structure

```
claude-code-analytics/
├── hooks/
│   └── export-conversation.sh       # SessionEnd hook for auto-export
├── scripts/
│   ├── pretty-print-transcript.py   # Convert JSONL to readable text
│   ├── create_database.py           # Create SQLite database schema
│   ├── import_conversations.py      # Import conversations to database
│   ├── create_fts_index.py          # Create full-text search index
│   ├── search_fts.py                # CLI search tool
│   └── analyze_session.py           # CLI analysis tool
├── streamlit_app/
│   ├── app.py                       # Dashboard entry point
│   ├── models/                      # Pydantic data models
│   │   └── __init__.py
│   ├── services/                    # Business logic layer
│   │   └── database_service.py
│   └── pages/                       # Dashboard pages
│       ├── browser.py               # Session browser
│       ├── conversation.py          # Conversation viewer
│       ├── search.py                # Full-text search
│       ├── analytics.py             # Analytics dashboard
│       └── ai_analysis.py           # AI-powered analysis
├── prompts/                         # Analysis prompt templates
│   ├── metadata.yaml                # Analysis type definitions
│   ├── decisions.md                 # Technical decisions prompt
│   ├── errors.md                    # Error patterns prompt
│   └── agent_usage.md               # AI agent usage analysis
├── docs/                            # Documentation
│   ├── index.html                   # Landing page (GitHub Pages)
│   └── technical/                   # Technical documentation
│       ├── agent-knowledge-retention.md
│       ├── deep-linking-implementation.md
│       ├── mcp-server-analytics.md
│       └── search-feature-requirements.md
├── install.sh                       # Automated installer
├── run_dashboard.sh                 # Dashboard launcher
└── README.md                        # This file
```

## Documentation

- **[Deep Linking](docs/technical/deep-linking-implementation.md)** - Technical details on search-to-conversation navigation
- **[Search Feature](docs/technical/search-feature-requirements.md)** - Full-text search implementation
- **[MCP Server Analytics](docs/technical/mcp-server-analytics.md)** - Analytics for MCP servers
- **[Agent Knowledge Retention](docs/technical/agent-knowledge-retention.md)** - Knowledge retention strategies
- **[Custom Prompts](prompts/README.md)** - How to create custom analysis prompts

## Development

### Setting Up Development Environment

If you're contributing to Claude Code Analytics or modifying the code, we use pre-commit hooks to ensure code quality:

#### 1. Install pre-commit

```bash
pip install pre-commit
```

#### 2. Install the git hooks

```bash
pre-commit install
```

#### 3. (Optional) Run against all files

```bash
pre-commit run --all-files
```

The hooks will now run automatically before each commit.

### Code Quality Tools

The pre-commit configuration includes:

- **Black** - Automatic code formatting (100 character line length)
- **Ruff** - Fast Python linter with auto-fix capabilities
  - Checks: pycodestyle, pyflakes, isort, flake8-bugbear, pyupgrade, and more
  - Automatically modernizes type hints (e.g., `typing.Dict` → `dict`)
  - Improves exception handling patterns
- **Bandit** - Security linting to detect potential vulnerabilities
- **Mypy** - Static type checking for type safety
- **Standard checks** - Trailing whitespace, end-of-file, YAML/JSON validation, large files, merge conflicts, private keys

### Manual Code Quality Checks

If you need to run checks manually without committing:

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files

# Skip hooks for a specific commit (not recommended)
git commit --no-verify
```

### Configuration

All tool configurations are in `pyproject.toml`:

- **Black**: 100 character line length
- **Ruff**: Comprehensive rule set with modern Python practices
- **Bandit**: Excludes test files, configured for security-critical patterns
- **Mypy**: Python 3.9+ target with reasonable strictness

### Logging Standards

Production scripts use Python's `logging` module for consistent output. See `claude_code_analytics/scripts/LOGGING.md` for conventions:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Use logger methods instead of print()
logger.info("Processing completed")
logger.error("Database not found")
logger.warning("Interrupted by user")
```

## Future Roadmap

- **Vector embeddings** - Semantic search across conversations
- **Cost tracking** - Monitor LLM API costs per analysis
- **Model comparison** - A/B test analysis quality across models
- **Export formats** - HTML, PDF conversation exports
- **Real-time analysis** - Analyze conversations as they happen
- **Cloud sync** - Optional backup to cloud storage
- **Presidio integration** - Advanced PII detection with entity recognition

## Contributing

Contributions are welcome! Feel free to:
- Report bugs or request features via GitHub Issues
- Submit pull requests
- Share your custom analysis prompts
- Suggest new analytics visualizations

## License

MIT License - Use and modify freely.

## Resources

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Claude Code Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks)
- [OpenRouter API](https://openrouter.ai/)
- [Google Gemini API](https://ai.google.dev/)
