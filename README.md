# Claude Code Analytics

[![Tests](https://github.com/sujankapadia/claude-code-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/sujankapadia/claude-code-analytics/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/sujankapadia/claude-code-analytics/branch/main/graph/badge.svg)](https://codecov.io/gh/sujankapadia/claude-code-analytics)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An analysis tool for [Claude Code](https://claude.com/claude-code) that automatically captures, archives, and analyzes your AI development conversations. Features a React dashboard with real-time updates, hybrid search (FTS + semantic embeddings), AI-powered insights, and session similarity search across all your sessions.

## What It Does

Claude Code Analytics transforms your AI development workflow into actionable insights:
- **Automatically captures** every conversation when you exit Claude Code
- **Real-time import** — a file watcher detects new sessions and imports them instantly, with SSE push to the UI
- **Stores and indexes** conversations in a searchable SQLite database with FTS5
- **React dashboard** — modern SPA with virtual scrolling, command palette (Cmd+K), and dark mode
- **Session similarity search** — hybrid FTS + semantic embeddings with sort by relevance/date and infinite scroll pagination
- **AI-powered analysis** of your development sessions using 300+ LLM models

## Prerequisites

Before installing, you need:

- **[Claude Code](https://claude.com/claude-code)** - The AI coding assistant (this tool captures its conversations)
- **Python 3.10+** - Check with `python3 --version`
- **Node.js 18+** and **npm** - Check with `node -v` and `npm -v`
  - macOS: `brew install node`
  - Linux: See [nodejs.org](https://nodejs.org)
- **jq** - JSON processor for installation script (optional but recommended)
  - macOS: `brew install jq`
  - Linux: `apt-get install jq` or `yum install jq`

## Compatibility

**Testing Status**: This is an alpha release (v0.1.0) that has been tested on:
- **macOS 14.7** (Sonoma)
- **Python 3.10-3.12** (CI tested on Ubuntu and macOS)
- **Claude Code 2.1.x**

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
- Builds the React frontend (`npm install && npm run build`)
- Sets up hooks to capture conversations
- Creates the CLI commands
- Configures Claude Code settings

### 2. Import Existing Conversations

```bash
claude-code-import
```

This creates the database, imports all existing conversations, and builds the search index.

### 3. Launch the App

```bash
claude-code-analytics
```

Open `http://localhost:8000` in your browser. The API server auto-imports new sessions via a file watcher and pushes updates to the UI in real time.

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

### ⚛️ React Dashboard

- **Dashboard** — KPI cards, daily activity charts, activity heatmap, projects table
- **Active Sessions** — Live view of currently running Claude Code sessions
- **Sessions** — Split-view with searchable session list and detail pane
- **Bookmarks** — Save and annotate specific messages across sessions
- **Conversation Viewer** — Virtual scrolling, collapsible tool cards, minimap, in-conversation search, role filtering
- **Search** — FTS5 with scope tabs, project/tool filters, search history, keyboard navigation
- **Session Similarity** — Hybrid search (FTS + ChromaDB + LLM query expansion) with RRF, sort, and pagination
- **Analytics** — Tool usage distribution, MCP server stats, daily trends, most expensive sessions
- **Analysis** — LLM-powered session analysis with scoping, searchable picker, Gist publishing
- **Command Palette** — Cmd+K for quick navigation across pages, projects, sessions, and search
- **Real-time updates** — File watcher auto-imports new sessions, SSE pushes updates to the UI

### 🔍 Search & Discovery

- **Full-text search** across all messages and tool content with deep linking to specific messages
- **Session similarity search** with hybrid FTS + semantic embeddings + LLM query expansion
- **Advanced filtering** by project, date range, role, and tool name
- **MCP tool tracking** with dedicated analytics for MCP server usage

### Additional Features

- **Automatic archiving** — Hook-based capture with dual-format storage (JSONL + readable text)
- **AI-powered analysis** — 300+ models via OpenRouter or Google Gemini, with pre-built and custom analysis types, GitHub Gist publishing with security scanning
- **Comprehensive analytics** — Token tracking, tool usage stats, daily trends, project insights, active time metrics

## Configuration

All settings are stored in `~/.config/claude-code-analytics/.env` with sensible defaults. No configuration is required for basic features (browse, search, analytics). Add an API key to enable AI analysis.

See [docs/configuration.md](docs/configuration.md) for the full configuration reference.

## Development

For frontend development with hot-reload, run the API server and React dev server in separate terminals. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality tools, and contribution guidelines.

## Documentation

- **[Configuration Reference](docs/configuration.md)** — All settings and environment variables
- **[Architecture & How It Works](docs/architecture.md)** — System design, hook system, database schema, project structure
- **[Advanced Usage](docs/advanced-usage.md)** — CLI tools, Python scripts, manual export, custom prompts
- **[Manual Installation](docs/manual-installation.md)** — Step-by-step manual setup
- **[Troubleshooting](docs/troubleshooting.md)** — Common issues and fixes
- **[Contributing](CONTRIBUTING.md)** — Development setup, code quality, logging standards
- **[Deep Linking](docs/technical/deep-linking-implementation.md)** — Technical details on search-to-conversation navigation
- **[Search Feature](docs/technical/search-feature-requirements.md)** — Full-text search implementation
- **[MCP Server Analytics](docs/technical/mcp-server-analytics.md)** — Analytics for MCP servers
- **[Agent Knowledge Retention](docs/technical/agent-knowledge-retention.md)** — Knowledge retention strategies
- **[Custom Prompts](prompts/README.md)** — How to create custom analysis prompts

## Future Roadmap

- **Copyable excerpts** - Select message ranges and copy as formatted markdown for sharing
- **Session tags** - Auto-tag sessions by workflow type for browsable discovery
- **Cost tracking** - Monitor LLM API costs per analysis
- **Export formats** - HTML, PDF conversation exports

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - Use and modify freely.

## Resources

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Claude Code Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks)
- [OpenRouter API](https://openrouter.ai/)
- [Google Gemini API](https://ai.google.dev/)
