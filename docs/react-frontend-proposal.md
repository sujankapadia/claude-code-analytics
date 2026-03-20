# React Frontend Proposal

## Status: Proposal

## Context

The app currently uses Streamlit as its frontend framework. Streamlit was chosen because it made it easy to stand up a Python-only app with built-in data visualization, data tables, and Pandas integration. That was the right call for getting something working quickly.

Now that the app has grown into a multi-page analytics platform with conversation browsing, full-text search, LLM-powered analysis, and Gist publishing, Streamlit's constraints are limiting the user experience in meaningful ways.

This document proposes replacing the Streamlit frontend with a React single-page application backed by a FastAPI server, while keeping all existing Python business logic intact.

## Problems with Streamlit

### Performance & Interaction Model

- **Full reruns on every interaction.** Every widget click (filter change, page navigation, checkbox toggle) re-executes the entire page script. This means re-querying data, re-rendering charts, and losing ephemeral state.
- **No client-side state.** Selecting a session in the browser page, navigating to the conversation viewer, then pressing back loses your selection. `st.session_state` helps but fights the rerun model.
- **No debounced input.** Search triggers a server round-trip on every keystroke. There's no way to implement typeahead or instant search.
- **Server-rendered pagination.** Scrolling through a 500+ message conversation requires server round-trips for each page. Virtual scrolling isn't possible.

### Layout & UX Constraints

- **Single-column bias.** Streamlit's layout primitives (`st.columns`, `st.sidebar`) don't support true split-pane views, resizable panels, or complex grid layouts.
- **No real routing.** Deep linking is hacked via `st.query_params`. There's no URL-based navigation, no browser history integration, no shareable URLs for specific views.
- **No keyboard navigation.** Can't implement Cmd+K command palette, arrow-key browsing, or keyboard shortcuts.
- **Poor mobile experience.** Streamlit's responsive behavior is limited and can't be customized.

### Component Limitations

- **Tables are basic.** `st.dataframe` provides read-only tables with limited sorting and no column resizing, row selection, or inline actions.
- **Fighting the framework for custom UI.** The conversation viewer (`conversation.py`) uses extensive CSS injection to create a chat-like interface — this is fragile and limited.
- **No rich interactions.** No drag-and-drop, context menus, collapsible sections with animation, or streaming text display.

## Proposed Architecture

### Overview

```
┌─────────────────────────────────┐
│  React SPA (Vite)               │
│  - All UI rendering             │
│  - Client-side state & caching  │
│  - Virtual scrolling            │
└──────────────┬──────────────────┘
               │ REST API (JSON) + SSE
┌──────────────▼──────────────────┐
│  FastAPI Server                  │
│  - Thin wrapper around existing  │
│    DatabaseService &             │
│    AnalysisService               │
│  - Serves built React SPA       │
│  - Streaming for LLM analysis   │
│  - File watcher for auto-import │
│  - SSE for real-time updates    │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  SQLite + FTS5 (unchanged)       │
└─────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | Vite + React Router | No SSR needed since FastAPI serves the built SPA. Simpler than Next.js with fewer concepts to manage. |
| Styling | Tailwind CSS + shadcn/ui | Fast iteration, dark mode, accessible components |
| Server state | TanStack Query | Fetch/cache/sync API data with loading/error states. Handles cache invalidation on SSE events. |
| Client state | React useState/useContext | Minimal UI state (selected filters, sidebar toggle) — no extra library needed |
| Charts | Recharts + D3 (for heatmap/treemap) | React-native charting with D3 for custom visualizations |
| Tables | TanStack Table | Virtual scrolling, sorting, filtering, column resizing |
| Virtual scroll | TanStack Virtual | Efficient rendering for conversation viewer and long lists |
| Code highlighting | Shiki | VS Code-quality syntax highlighting, supports diff rendering |
| API server | FastAPI | Wraps existing Python services as REST endpoints |
| File watching | watchfiles | Monitors conversations directory for auto-import |

### Deployment Model

FastAPI serves the built React app as static files. In production, `claude-code-analytics` launches a single FastAPI process that serves both the API and the SPA — no separate frontend server needed. During development, Vite's dev server runs alongside FastAPI with proxy config for API calls.

### What Changes, What Stays

**Stays the same:**
- `DatabaseService` — all SQL queries and data access
- `AnalysisService` — LLM orchestration and prompt templates
- `GistPublisher` — security scanning and Gist creation
- SQLite schema, FTS5 indexes
- Import scripts and CLI tools
- Data models (Pydantic — now also serve as API response schemas)

**Replaced:**
- All Streamlit page files (`streamlit_app/pages/*.py`)
- `streamlit_app/app.py` (entry point and CSS)
- Altair charts → Recharts/D3
- `st.dataframe` → TanStack Table
- `st.session_state` → TanStack Query cache + React state

**New:**
- FastAPI application with REST endpoints
- React component tree (Vite project in `frontend/`)
- File watcher for auto-import + SSE event broadcasting

## UI Design

### Navigation: Persistent Sidebar + Command Palette

Replace Streamlit's top-nav tabs with a collapsible sidebar:
- Project tree (expandable folders with sessions nested underneath)
- Quick-access list of recent sessions
- Global search trigger
- Collapsed state shows only icons

Cmd+K command palette for power users — fuzzy search to jump to any session, project, or page.

### Page 1: Home Dashboard

A responsive grid replacing the current Analytics + Browser overview pages.

```
┌─────────────────────────────────────────────────────┐
│  [KPI Cards Row]                                    │
│  Sessions | Messages | Tokens | Active Time         │
├──────────────────────┬──────────────────────────────┤
│  Activity Heatmap    │  Token Usage Sparklines      │
│  (GitHub-style       │  (per project, 30-day trend) │
│   contribution grid) │                              │
├──────────────────────┼──────────────────────────────┤
│  Tool Usage Treemap  │  Project Breakdown           │
│  (size = uses,       │  (sortable table with        │
│   color = error rate)│   inline sparklines)         │
└──────────────────────┴──────────────────────────────┘
```

- **Activity heatmap** (GitHub contribution grid style) shows patterns across days and hours of day — reveals when you're most active with Claude Code
- **Inline sparklines** in the project table show 30-day message trends without requiring a separate chart
- **Tool usage treemap** conveys both volume (size) and error rate (color) in one glance
- All cards are clickable drill-downs — click a project to filter the dashboard

### Page 2: Session Explorer

Master-detail layout with session list on the left and preview pane on the right.

```
┌──────────────────────┬──────────────────────────────┐
│  [Filter Bar]        │                              │
│  Project ▾ | Date ▾  │  Session Preview             │
├──────────────────────┤  ┌────────────────────────┐  │
│  ● Session abc123    │  │ Activity timeline       │  │
│    3/10 · 142 msgs   │  │ ████░░░░████████░░██   │  │
│                      │  ├────────────────────────┤  │
│  ○ Session def456    │  │ Key metrics + tags      │  │
│    3/9 · 89 msgs     │  │ Token breakdown donut   │  │
│                      │  │ Tools used (chips)      │  │
│  ○ Session ghi789    │  │ [View] [Analyze]        │  │
│    3/8 · 201 msgs    │  └────────────────────────┘  │
└──────────────────────┴──────────────────────────────┘
```

- **Activity timeline scrubber** — a minimap showing message density over the session's duration, revealing bursts of activity and idle gaps
- **Virtual scrolling** on the session list — no pagination, handles thousands of sessions
- **Keyboard navigation** — arrow keys to browse, Enter to open
- **Multi-select** for batch analysis or side-by-side comparison

### Page 3: Conversation Viewer

The highest-impact redesign. Replace CSS-hacked Streamlit with a proper chat interface.

```
┌──────────────────────────────────────────────────────┐
│  Session abc123 · project-name          [Analyze ▾]  │
├────────────┬─────────────────────────────────────────┤
│ Minimap    │  ┌─────────────────────────────────┐    │
│ ┃█         │  │ 👤 User                    10:32│    │
│ ┃█         │  │ Can you fix the auth bug in...  │    │
│ ┃          │  └─────────────────────────────────┘    │
│ ┃████      │  ┌─────────────────────────────────┐    │
│ ┃████      │  │ 🤖 Assistant               10:32│    │
│ ┃██        │  │ I'll investigate the auth...     │    │
│ ┃          │  │ ┌─ Read auth.py ──────────────┐ │    │
│ ┃██        │  │ │ (collapsible tool result)   │ │    │
│ ┃          │  │ └─────────────────────────────┘ │    │
│ ┃█         │  │ ┌─ Edit auth.py ──────────────┐ │    │
│            │  │ │ - old line                   │ │    │
│            │  │ │ + new line                   │ │    │
│            │  │ └─────────────────────────────┘ │    │
│            │  └─────────────────────────────────┘    │
├────────────┴─────────────────────────────────────────┤
│  [Token bar: ████████░░ 85k/100k input]              │
└──────────────────────────────────────────────────────┘
```

- **Conversation minimap** (VS Code style) — see the shape of the entire conversation, with color-coded blocks for user/assistant/tool-heavy regions. Click to jump.
- **Collapsible tool calls** — each tool invocation is a collapsible card. Edit tools render actual diffs with syntax highlighting (green/red lines). Read tools show syntax-highlighted file content.
- **Syntax highlighting** in all code blocks via Shiki
- **Virtual scrolling** — only renders visible messages, handles 1000+ message sessions without lag
- **Sticky token usage bar** at the bottom showing cumulative input/output usage
- **In-conversation search** (Cmd+F override) with match count and prev/next navigation
- **Right-click context menu** on any message: "Analyze from here", "Copy as Markdown", "Jump to tool output"

### Page 4: Search

Replace form-based search with an instant search experience.

- **Typeahead with debounce** — results appear as you type, no submit button needed
- **Faceted filters as a sidebar** — project, date range, role, tool name — each showing result counts
- **Result previews** with surrounding context lines, highlighted matches, and syntax highlighting for code matches
- **Keyboard-driven** — arrow keys to navigate results, Enter to open in conversation viewer with match highlighted
- **Search history** persisted in localStorage

### Page 5: Analysis

- **Inline trigger** — select a range of messages in the conversation viewer, right-click "Analyze selection"
- **Side-by-side view** — conversation on the left, analysis output streaming in real-time on the right
- **Analysis history** — browse past analyses for any session, compare results across different models
- **Live markdown rendering** as the LLM streams tokens

### Page 6: Import

- Keep it simple — a status page showing detected new/updated conversations with a one-click import button
- Progress bar with real-time updates via server-sent events

## FastAPI Endpoints

Thin wrappers around existing service methods. Pydantic models already define the response schemas.

### Projects
- `GET /api/projects` — list all projects with summary stats
- `GET /api/projects/{project_id}` — single project details

### Sessions
- `GET /api/sessions` — list sessions, filterable by project, date range. Paginated.
- `GET /api/sessions/{session_id}` — single session with full stats
- `GET /api/sessions/{session_id}/messages` — messages with optional role filter, supports cursor pagination
- `GET /api/sessions/{session_id}/tool-uses` — tool invocations for a session
- `GET /api/sessions/{session_id}/tokens/timeline` — token usage over time

### Search
- `GET /api/search` — full-text search with params: `q`, `scope`, `project_id`, `date_from`, `date_to`, `tool_name`, `page`, `per_page`

### Analytics
- `GET /api/analytics/daily` — daily message/token stats, configurable range
- `GET /api/analytics/tools` — tool usage summary
- `GET /api/analytics/tools/mcp` — MCP server/tool breakdown
- `GET /api/analytics/activity` — active time and text volume metrics

### Analysis
- `POST /api/analysis/run` — run analysis (returns streaming response)
- `GET /api/analysis/estimate` — estimate token count for a scope
- `POST /api/analysis/publish` — scan and publish to Gist

### Import
- `POST /api/import` — trigger manual import, returns SSE stream with progress

### Real-time Events
- `GET /api/events` — SSE stream for real-time updates. Events:
  - `session_imported` — new session imported (auto or manual), includes `session_id` and `project_id`
  - `import_progress` — progress updates during manual import

## Real-time Updates

New sessions are automatically detected and imported without manual intervention.

### How It Works

1. **File watcher** — FastAPI starts a background task using `watchfiles` to monitor the `CLAUDE_CONVERSATIONS_DIR` for new or modified `.jsonl` files. The watcher uses a debounce (2 seconds) to ensure files are fully written before processing — the SessionEnd hook copies the file, and we need to wait for that to complete.

2. **Auto-import** — When a new `.jsonl` file is detected, the server runs an incremental import: parses the file, inserts new messages and tool uses into the database, and updates FTS indexes in the same transaction.

3. **Incremental FTS** — Instead of rebuilding the full FTS5 index (as the current `create_fts_index.py` does), new rows are inserted directly into `fts_messages` and `fts_tool_uses` within the same transaction as the regular table inserts. FTS5 handles this natively — new content is immediately searchable.

4. **SSE broadcast** — After a successful import, the server pushes a `session_imported` event on the `/api/events` SSE stream with the session ID and project ID.

5. **Client-side cache invalidation** — The React app listens to the SSE stream via an `EventSource`. When a `session_imported` event arrives, TanStack Query invalidates the relevant query caches (session list, project summaries, analytics). The UI updates automatically — no page refresh needed.

```
Session ends → SessionEnd hook exports .jsonl
                     │
                     ▼
              watchfiles detects new file (2s debounce)
                     │
                     ▼
              FastAPI imports to SQLite + FTS5 (single transaction)
                     │
                     ▼
              SSE event: { type: "session_imported", session_id, project_id }
                     │
                     ▼
              TanStack Query invalidates caches → UI updates
```

## Implementation Plan

### Phase 1: FastAPI Backend (Python-side changes)

Create the FastAPI application that wraps existing services. This can coexist with Streamlit during the transition.

1. Add FastAPI + uvicorn + watchfiles to dependencies
2. Create `claude_code_analytics/api/` package:
   - `app.py` — FastAPI app, CORS config, lifespan (starts file watcher on startup)
   - `routers/projects.py`
   - `routers/sessions.py`
   - `routers/search.py`
   - `routers/analytics.py`
   - `routers/analysis.py`
   - `routers/import_data.py`
   - `routers/events.py` — SSE endpoint
   - `services/file_watcher.py` — watches conversations dir, triggers incremental import
   - `services/event_bus.py` — in-process pub/sub for SSE broadcasting
3. Refactor import logic to support incremental FTS inserts (insert into FTS tables in the same transaction as regular tables, instead of full rebuild)
4. Add CLI entry point: `claude-code-api` to start the FastAPI server
5. Verify all endpoints with manual testing / httpie

### Phase 2: Vite + React Project Scaffolding

1. Initialize Vite + React + TypeScript project in `frontend/`
2. Configure Tailwind CSS + shadcn/ui
3. Set up React Router with route structure matching the pages
4. Set up TanStack Query provider
5. Create the app shell: sidebar navigation, dark theme, basic routing
6. Implement the API client layer (typed fetch wrappers)
7. Set up SSE listener for real-time events + TanStack Query invalidation

### Phase 3: Conversation Viewer

Build the highest-impact page first.

1. Message list with virtual scrolling (TanStack Virtual)
2. Collapsible tool call cards with syntax highlighting
3. Diff rendering for Edit tool results
4. Conversation minimap
5. In-conversation search
6. Deep linking (URL reflects session + message index)

### Phase 4: Search

1. Search input with debounce
2. Results list with context previews
3. Faceted filter sidebar
4. Click-through to conversation viewer with highlight
5. Keyboard navigation

### Phase 5: Dashboard & Analytics

1. KPI cards with project/date filtering
2. Activity heatmap (D3)
3. Tool usage treemap (D3)
4. Project table with sparklines
5. Daily activity charts (Recharts)

### Phase 6: Session Explorer

1. Master-detail layout
2. Session list with virtual scrolling
3. Preview pane with activity timeline
4. Filter bar

### Phase 7: Analysis

1. Analysis form with scope selection
2. Streaming LLM output display
3. Side-by-side mode (conversation + analysis)
4. Gist publishing flow

### Phase 8: Polish & Migration

1. Import page with SSE progress
2. Command palette (Cmd+K)
3. Keyboard shortcuts throughout
4. Mobile responsive pass
5. Remove Streamlit dependency
6. Update CLI entry points and documentation

## Decisions

These were discussed and resolved during the proposal process:

- **Deployment model:** Single process. FastAPI serves the built React SPA as static files. One command (`claude-code-analytics`) starts everything. During development, Vite dev server runs separately with a proxy to FastAPI.
- **Framework:** Vite + React Router instead of Next.js. Since FastAPI serves the SPA, we don't need SSR, server components, or any of the features that justify Next.js's complexity.
- **State management:** TanStack Query for server state (the vast majority of app state). React's built-in useState/useContext for the small amount of client-only UI state. No Zustand or other external state library needed.
- **Real-time updates:** File watcher (watchfiles) monitors the conversations directory for new exports. Auto-imports into SQLite with incremental FTS updates. Broadcasts via SSE to the React app, which invalidates TanStack Query caches for automatic UI updates.
- **Electron/Tauri:** Not now. The single-process architecture makes this easy to add later if there's a clear reason (system tray, native file dialogs, etc.). A browser tab is fine for a local developer tool.
- **Auth:** Skip. This is a local tool reading local SQLite. Network exposure would be handled by a reverse proxy, not in-app auth.
