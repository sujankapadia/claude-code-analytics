# claude-code-utils

A collection of utilities and hooks for [Claude Code](https://claude.com/claude-code) that automatically exports and archives your conversation transcripts.

## Overview

The main feature of this toolkit is automatic conversation archiving using Claude Code's SessionEnd hooks. When a Claude Code session ends, your conversation is automatically:
- Exported from the internal JSONL transcript format
- Converted to a human-readable text format
- Organized by project in `~/claude-conversations/`
- Saved in both raw JSONL and formatted text versions

This makes it easy to review past conversations, track your development process, and maintain a searchable archive of your work with Claude.

## Features

### Core Features
- **Automatic export on session end** - No manual intervention required
- **Project-based organization** - Conversations are organized by the project directory where they occurred
- **Dual format storage** - Both raw JSONL (for programmatic access) and pretty-printed text (for human reading)
- **Rich formatting** - The text format includes:
  - Clear visual separation between user and Claude messages
  - Tool commands (e.g., `$ git push`)
  - Tool results with actual output
  - Timestamps
  - Proper handling of multiline content
- **Session resumption handling** - Correctly identifies the latest transcript even when resuming old sessions
- **Debug logging** - Troubleshoot issues with `~/.claude/export-debug.log`

### Analytics & Database Features
- **SQLite database** - Normalized schema with projects, sessions, messages, and tool uses
- **Incremental import** - Efficiently updates database with only new messages from active sessions
- **Message-level tool tracking** - Each tool use is linked to its message via `message_index`
- **Full-text search** - FTS5 search index for fast content search across all conversations
- **Token tracking** - Comprehensive token usage statistics including cache metrics
- **Tool analytics** - Track tool usage patterns, error rates, and performance
- **MCP server integration** - Analyze MCP server usage and patterns

### AI-Powered Analysis
- **Multiple LLM providers** - Use OpenRouter (300+ models) or Google Gemini directly
- **Curated model selection** - Quick-select from 13 newest premium models (2025):
  - **Budget tier**: Qwen3, Llama 4 Scout, Mistral Small ($0.06-$0.10 per 1M tokens)
  - **Balanced tier**: DeepSeek V3.2, Gemini 3 Flash, Claude Haiku 4.5, GPT-5.1/5.2 ($0.26-$1.75)
  - **Premium tier**: Gemini 3 Pro, Claude Sonnet 4.5, Grok 4, Claude Opus 4.5 ($2-$5)
- **Browse 300+ models** - Access full OpenRouter catalog with pricing and context info
- **Multiple analysis types**:
  - **Technical Decisions**: Extract decisions, alternatives considered, and reasoning
  - **Error Patterns**: Identify error patterns, root causes, and resolutions
  - **AI Agent Usage**: Analyze how developers use AI agents for prototyping, experimentation, and discovery
  - **Custom Analysis**: Enter your own analysis prompts
- **Templated prompts** - Jinja2-based prompt management for easy customization
- **Export results** - Save analysis as markdown files
- **Configurable temperature** - Control analysis determinism (default: 0.1)

### 🎨 Streamlit Dashboard (NEW!)
- **Interactive Web UI** - Beautiful dashboard for exploring your conversations
- **Session Browser** - View and filter all your conversation sessions
- **Terminal-Style Conversation Viewer** - Clean, minimal interface mimicking Claude Code sessions:
  - Inline tool calls and results
  - Message-level tool use tracking with `message_index`
  - Filtering by role and content search
  - Optional token usage display
  - Auto-hide empty messages
- **Analysis Runner** - Run AI-powered analysis directly from the UI
- **Analytics Dashboard** - Interactive charts and statistics:
  - Token usage trends over time
  - Tool usage distribution
  - Daily activity metrics
  - Project statistics

## Installation

### Quick Install (Recommended)

Clone the repository and run the installation script:

```bash
git clone https://github.com/yourusername/claude-code-utils.git
cd claude-code-utils
./install.sh
```

The install script will:
- Create necessary directories (`~/.claude/scripts/`, `~/claude-conversations/`)
- Copy scripts to `~/.claude/scripts/`
- Set executable permissions
- Update `~/.claude/settings.json` with the SessionEnd hook (backs up existing settings)

**Note:** The script uses `jq` for JSON manipulation if available. If not installed, it will provide manual configuration instructions. Install with: `brew install jq` (macOS) or `apt-get install jq` (Linux).

### Manual Installation

If you prefer to install manually:

#### 1. Create the scripts directory

```bash
mkdir -p ~/.claude/scripts
```

#### 2. Copy the scripts

Copy both `export-conversation.sh` and `pretty-print-transcript.py` to `~/.claude/scripts/`:

```bash
cp hooks/export-conversation.sh ~/.claude/scripts/
cp scripts/pretty-print-transcript.py ~/.claude/scripts/
```

#### 3. Make scripts executable

```bash
chmod +x ~/.claude/scripts/export-conversation.sh
chmod +x ~/.claude/scripts/pretty-print-transcript.py
```

#### 4. Configure the SessionEnd hook

Add the following to your `~/.claude/settings.json`:

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

If you already have other hooks configured, just add the `SessionEnd` entry to your existing `hooks` object.

#### 5. Create the conversations directory (optional)

The script will create this automatically, but you can create it manually if you prefer:

```bash
mkdir -p ~/claude-conversations
```

## Usage

### 1. Automatic Export

Once configured, conversations are automatically exported when you exit Claude Code. You don't need to do anything!

Your conversations will be saved to:
```
~/claude-conversations/
  └── project-name/
      ├── session-20250113-143022.jsonl
      ├── session-20250113-143022.txt
      ├── session-20250113-151430.jsonl
      └── session-20250113-151430.txt
```

### 2. Import to Database

Create and populate the SQLite database:

```bash
# Create the database schema
python3 scripts/create_database.py

# Import all conversations (initial import)
python3 scripts/import_conversations.py

# Create full-text search index (optional)
python3 scripts/create_fts_index.py
```

The database will be created at `~/claude-conversations/conversations.db`.

**Incremental Import:** The import script supports incremental updates! Run it anytime to import only new messages from active or completed sessions. It automatically:
- Detects existing sessions in the database
- Imports only messages newer than the last imported message
- Updates session metadata (end_time, message counts)
- Preserves all existing data with zero duplicates
- Works efficiently even while sessions are still active

### 3. Launch the Dashboard

Start the Streamlit dashboard:

```bash
# Using the launch script
./run_dashboard.sh

# Or directly
streamlit run streamlit_app/app.py
```

The dashboard will open at `http://localhost:8501`.

### 4. Run Analysis (CLI)

#### Setup API Key

**Option 1: OpenRouter (Recommended)** - Access 300+ models
```bash
export OPENROUTER_API_KEY="sk-or-your-key-here"
```
Get your key from [OpenRouter](https://openrouter.ai/keys)

**Option 2: Google Gemini (Direct)**
```bash
export GOOGLE_API_KEY="your-api-key-here"
```
Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)

#### Run Analysis

```bash
# Using default model (DeepSeek V3.2)
python3 scripts/analyze_session.py <session-id> --type=decisions

# Specify a model
python3 scripts/analyze_session.py <session-id> --type=errors --model=anthropic/claude-sonnet-4.5

# Analyze AI agent usage
python3 scripts/analyze_session.py <session-id> --type=agent_usage --model=openai/gpt-5.2-chat

# Custom analysis with your own prompt
python3 scripts/analyze_session.py <session-id> --type=custom --prompt="Summarize main topics discussed"

# Save to file
python3 scripts/analyze_session.py <session-id> --type=decisions --output=analysis.md
```

**Popular Models:**
- `deepseek/deepseek-v3.2` - Default, best balance ($0.26/1M)
- `anthropic/claude-sonnet-4.5` - Highest quality ($3.00/1M)
- `openai/gpt-5.2-chat` - Latest GPT ($1.75/1M)
- `google/gemini-3-flash-preview` - 1M context ($0.50/1M)
- `qwen/qwen3-vl-8b-instruct` - Cheapest ($0.06/1M)

### 5. Search Conversations

Use the FTS5 search (requires running `create_fts_index.py` first):

```bash
python3 scripts/search_fts.py "error handling"
```

### Manual Export

You can also manually convert existing JSONL transcripts to readable text:

```bash
~/.claude/scripts/pretty-print-transcript.py /path/to/transcript.jsonl output.txt
```

Or use stdin/stdout:

```bash
cat transcript.jsonl | ~/.claude/scripts/pretty-print-transcript.py > output.txt
```

## File Structure

### `export-conversation.sh`

The main hook script that:
- Receives the current working directory and transcript path from Claude Code
- Finds the most recent transcript file (handling session resumption)
- Creates the project-specific directory structure
- Copies the JSONL file
- Calls the pretty-print script to create the readable version
- Logs debug information

### `pretty-print-transcript.py`

Python script that converts JSONL transcripts to readable text:
- Parses the Claude Code JSONL format
- Formats messages with clear visual separation
- Displays tool usage (commands and results)
- Handles both string and structured object tool results
- Adds timestamps and proper text wrapping

### Output Format Example

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

## Troubleshooting

### Debug Log

If exports aren't working, check the debug log:

```bash
cat ~/.claude/export-debug.log
```

The log includes:
- Hook execution timestamps
- Paths being processed
- File operations
- Any errors encountered

### Common Issues

**Conversations not exporting**
- Verify the hook is configured in `~/.claude/settings.json`
- Check that scripts are executable (`chmod +x`)
- Review `~/.claude/export-debug.log` for errors

**Permission errors**
- Ensure `~/claude-conversations/` is writable
- Verify script files have execute permissions

**Missing Python or bash**
- The scripts require Python 3 and bash
- On macOS/Linux these are typically pre-installed
- Run `python3 --version` and `bash --version` to verify

## Project Structure

```
claude-code-utils/
├── hooks/                          # Claude Code hooks
│   └── export-conversation.sh      # SessionEnd hook for auto-export
├── scripts/                        # Python scripts
│   ├── pretty-print-transcript.py  # Convert JSONL to readable text
│   ├── create_database.py          # Create SQLite database
│   ├── import_conversations.py     # Import conversations to database
│   ├── create_fts_index.py         # Create full-text search index
│   ├── search_fts.py               # Search conversations
│   └── analyze_session.py          # CLI for running analysis
├── streamlit_app/                  # Streamlit dashboard
│   ├── app.py                      # Main entry point
│   ├── models/                     # Pydantic data models
│   ├── services/                   # Business logic layer
│   └── pages/                      # UI pages
├── prompts/                        # Analysis prompt templates
│   ├── metadata.yaml               # Analysis type metadata
│   ├── decisions.md                # Technical decisions prompt
│   ├── errors.md                   # Error patterns prompt
│   └── agent_usage.md              # AI agent usage analysis prompt
├── install.sh                      # Installation script
└── run_dashboard.sh                # Launch dashboard script
```

## Documentation

- **Main README** (this file): Overview and getting started
- **Database Documentation**: See `docs/database.md` for schema details
- **Streamlit App**: See `streamlit_app/README.md` for dashboard documentation
- **Prompts**: See `prompts/README.md` for customizing analysis prompts

## Future Ideas

- **PII/sensitive data detection** - Identify potential PII in conversations
- **Vector embeddings** - Add semantic search across all conversations
- **Export formats** - Support for additional export formats (HTML, PDF)
- **Cloud sync** - Optional backup to cloud storage
- **Comparative analysis** - Compare patterns across multiple sessions
- **Real-time analysis** - Analyze conversations as they happen
- **Cost tracking** - Track LLM API costs per analysis
- **Model comparison** - Compare analysis quality across different models

## Contributing

Contributions are welcome! Feel free to:
- Report bugs or issues
- Suggest new features
- Submit pull requests
- Share your own utilities and hooks

## License

MIT License - feel free to use and modify as needed.

## Related Resources

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Claude Code Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks)
