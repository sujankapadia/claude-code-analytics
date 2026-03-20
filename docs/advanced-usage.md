# Advanced Usage

[Back to README](../README.md)

## Using the App

### Sessions

The **Sessions** page shows all your conversations in a split-view layout:
- Searchable session list with first user message preview
- Detail pane with stats cards (messages, tokens, duration)
- Filter by project
- Click to view the full conversation

### Conversation Viewer

The conversation viewer handles sessions with 1000+ messages:
- Virtual scrolling for performance
- Collapsible tool cards with syntax highlighting
- Minimap navigation for quick jumping
- In-conversation search (Cmd+F)
- Role filter (All / User / Assistant)
- Token usage bar

### Search

FTS5-powered search across all messages and tool content:
- Scope tabs: All, Messages, Tool Input, Tool Results, Sessions
- **Sessions tab** — hybrid similarity search (FTS + semantic embeddings + LLM query expansion) with sort by Relevance/Oldest/Newest and "Show more" pagination
- Project and tool name filters
- Search history with keyboard navigation
- Click results to jump directly to the matching message in context
- "Analyze" button to run scoped analysis on any search hit

### Analytics

Visual insights into your development patterns:
- Tool usage distribution, error rates, session usage
- Daily activity trends (messages, tokens, sessions)
- MCP server stats
- Project statistics

### AI Analysis

Analyze sessions with 300+ LLM models:
1. Select a session from the searchable picker
2. Choose scope: entire session, time range, or search hit context
3. Choose analysis type or write a custom prompt
4. Select model and run analysis
5. Optionally publish to GitHub Gist (with automatic security scanning)

## CLI Tools

The installation provides several CLI commands for working with your conversations.

### Search Conversations

```bash
claude-code-search "error handling"
```

### Run Analysis from CLI

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

### Import New Conversations

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

## Using Python Scripts Directly

If you prefer to use the Python scripts directly instead of CLI commands:

```bash
# Search
python3 scripts/search_fts.py "error handling"

# Analyze
python3 scripts/analyze_session.py <session-id> --type=decisions

# Import
python3 scripts/import_conversations.py
```

## Manual Export

Convert JSONL transcripts to readable text format:

```bash
~/.claude/scripts/pretty-print-transcript.py /path/to/transcript.jsonl output.txt

# Or via stdin/stdout
cat transcript.jsonl | ~/.claude/scripts/pretty-print-transcript.py > output.txt
```

## Custom Analysis Prompts

Create custom analysis templates in `prompts/`:

1. Create a new `.md` file with your Jinja2 template
2. Add metadata to `prompts/metadata.yaml`
3. Use from dashboard or CLI with `--type=your_template_name`

See `prompts/README.md` for detailed instructions.
