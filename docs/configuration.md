# Configuration

[Back to README](../README.md)

Claude Code Analytics uses a centralized configuration system with smart defaults. All settings are stored in `~/.config/claude-code-analytics/.env`.

## Configuration File Location

The configuration file is automatically created during installation at:
```
~/.config/claude-code-analytics/.env
```

This location follows the [XDG Base Directory specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html).

## Configuration Variables

The `.env` file supports all standard environment variable syntax, including variable interpolation using `${VAR}` syntax.

### Data Directories

```bash
# Base directory for all conversation data
# All other paths default to subdirectories of this unless explicitly overridden
CLAUDE_CONVERSATIONS_DIR=~/claude-conversations

# Optional: Override specific directories
ANALYSIS_OUTPUT_DIR=${CLAUDE_CONVERSATIONS_DIR}/analyses
DATABASE_PATH=${CLAUDE_CONVERSATIONS_DIR}/conversations.db
```

### Pagination Settings

```bash
# Number of messages before enabling pagination in conversation viewer
PAGINATION_THRESHOLD=500

# Number of messages to show per page when paginated
MESSAGES_PER_PAGE=100
```

### Search Configuration

```bash
# Number of search results to show per page (FTS search)
SEARCH_RESULTS_PER_PAGE=10

# Session similarity search returns 20 results per page by default
```

### Display Settings

```bash
# Maximum length of tool results to display (characters)
# Results longer than this will be truncated
TOOL_RESULT_MAX_LENGTH=2000
```

### Similarity Search (ChromaDB + Query Expansion)

```bash
# ChromaDB persistent storage directory (for semantic embeddings)
CHROMA_DATA_DIR=${CLAUDE_CONVERSATIONS_DIR}/chroma

# Query expansion provider — any OpenAI-compatible endpoint (e.g. Ollama)
# Used to expand search queries with related terms for better recall
EXPANSION_BASE_URL=http://localhost:11434/v1   # Default: local Ollama
EXPANSION_MODEL=qwen3:8b                       # Default model for expansion
EXPANSION_API_KEY=                              # Optional: API key if required
```

### Debug Logging

```bash
# Location of export hook debug log
CLAUDE_EXPORT_DEBUG_LOG=~/.claude/export-debug.log
```

### LLM API Configuration (Required for AI Analysis)

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

### GitHub Integration (Optional - for Gist Publishing)

```bash
# GitHub Personal Access Token for publishing analysis as gists
# Get your token from: https://github.com/settings/tokens/new
# Required scope: 'gist' (create gists)
GITHUB_TOKEN=ghp_your_token_here
```

## Required vs Optional Settings

**Required for basic features** (browse, search, analytics):
- None! The defaults work out of the box.

**Required for AI analysis features**:
- Either `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`

**Required for GitHub Gist publishing**:
- `GITHUB_TOKEN` - Personal Access Token with `gist` scope

**Required for session similarity search (semantic mode)**:
- A running [Ollama](https://ollama.ai) instance (or any OpenAI-compatible endpoint) for query expansion
- Configure via `EXPANSION_BASE_URL`, `EXPANSION_MODEL`, `EXPANSION_API_KEY`

**Optional customization**:
- All other settings have sensible defaults
- Customize data directories if you want conversations stored elsewhere
- Adjust pagination/display settings for personal preferences

## Customizing Configuration

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

## Variable Interpolation

The configuration system supports referencing other variables using `${VAR}` syntax:

```bash
# Set base directory
CLAUDE_CONVERSATIONS_DIR=~/my-custom-location

# Derived paths automatically use the base
ANALYSIS_OUTPUT_DIR=${CLAUDE_CONVERSATIONS_DIR}/analyses
DATABASE_PATH=${CLAUDE_CONVERSATIONS_DIR}/conversations.db
```

## Environment Variables

You can override configuration file settings using environment variables:

```bash
# Temporary override for this session
export OPENROUTER_MODEL="anthropic/claude-sonnet-4.5"
claude-code-analytics

# Permanent override in shell profile (~/.bashrc, ~/.zshrc)
echo 'export OPENROUTER_API_KEY="sk-or-your-key"' >> ~/.zshrc
```

## Configuration Reference

For a complete list of all configuration variables with documentation, see [`.env.example`](../.env.example) in the repository.
