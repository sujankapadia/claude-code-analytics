# How It Works

[Back to README](../README.md)

## Architecture

```
Claude Code Session
       |
SessionEnd Hook (export-conversation.sh)
       |
~/.claude/projects/{encoded-path}/
  └── session-uuid.jsonl
       |                          |
File Watcher (auto)         Import Script (manual)
       |                          |
SQLite Database (conversations.db)
  ├── projects
  ├── sessions
  ├── messages
  ├── tool_uses
  └── fts_messages / fts_tool_uses (FTS5)
       |
FastAPI + React (port 8000)
  ├── REST API (/api/*)
  ├── SSE Events (/api/events)
  └── React SPA (static files)
       |
  ├── Dashboard
  ├── Active Sessions
  ├── Sessions
  ├── Bookmarks
  ├── Search (FTS + Session Similarity)
  ├── Analytics
  ├── Analysis
  └── Import
```

## Hook System

The `export-conversation.sh` hook runs automatically when you exit Claude Code:

1. Receives current working directory and transcript path
2. Finds the most recent transcript (handles session resumption)
3. Creates project-specific directory structure
4. Copies JSONL file with timestamp
5. Generates human-readable text version
6. Logs to `~/.claude/export-debug.log`

## Database Schema

The SQLite database uses a normalized schema:

- **projects** - Unique project directories
- **sessions** - Conversation sessions with metadata
- **messages** - Individual messages with token tracking
- **tool_uses** - Tool calls linked to messages via `message_index`
- **fts_messages** - FTS5 full-text search index
- **Views** - Pre-aggregated statistics for performance

See the technical documentation in `docs/technical/` for more details.

## Project Identification

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

## File Organization

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

## Readable Text Format

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

## Project Structure

```
claude-code-analytics/
├── claude_code_analytics/
│   ├── api/                            # FastAPI backend
│   │   ├── app.py                      # App factory, CORS, lifespan
│   │   ├── dependencies.py             # DI for database & analysis services
│   │   ├── routers/                    # API endpoints
│   │   │   ├── projects.py             # GET /projects
│   │   │   ├── sessions.py             # GET /sessions, messages, tokens, etc.
│   │   │   ├── active.py              # GET /active-sessions
│   │   │   ├── bookmarks.py           # CRUD /bookmarks
│   │   │   ├── search.py               # GET /search (FTS5)
│   │   │   ├── similar.py              # GET /search/sessions (hybrid similarity)
│   │   │   ├── analytics.py            # GET /analytics (daily, tools, heatmap)
│   │   │   ├── analysis.py             # POST /analysis/run, /analysis/publish
│   │   │   ├── import_data.py          # POST /import (SSE progress)
│   │   │   └── events.py               # GET /events (SSE stream)
│   │   └── services/                   # Background services
│   │       ├── event_bus.py            # Async fan-out for SSE
│   │       ├── file_watcher.py         # watchfiles-based auto-import
│   │       └── import_service.py       # Incremental import with FTS updates
│   ├── services/                       # Business logic layer
│   │   ├── database_service.py         # SQLite queries
│   │   ├── embedding_service.py        # ChromaDB semantic embeddings
│   │   ├── analysis_service.py         # LLM analysis orchestration
│   │   ├── llm_providers.py            # LLM provider abstraction
│   │   ├── gist_publisher.py           # GitHub Gist publishing
│   │   └── format_utils.py             # Duration/size formatting
│   ├── models/                         # Pydantic data models
│   │   ├── database_models.py          # Project, Session, Message, ToolUse
│   │   └── analysis_models.py          # AnalysisType, AnalysisResult
│   ├── prompts/                        # Analysis prompt templates (Jinja2)
│   └── scripts/                        # CLI scripts (import, search, analyze)
├── frontend/                           # React frontend
│   ├── src/
│   │   ├── api/                        # Typed API client + response types
│   │   ├── components/                 # UI components (sidebar, conversation viewer, etc.)
│   │   ├── hooks/                      # SSE hook for real-time updates
│   │   └── pages/                      # Route pages (dashboard, sessions, search, etc.)
│   └── package.json
├── hooks/                              # Claude Code SessionEnd hook
│   └── export-conversation.sh
├── docs/                               # Documentation + proposals
├── install.sh                          # Automated installer
├── uninstall.sh                        # Clean removal script
└── README.md
```
