# Claude Code Analytics — React Frontend

The React frontend for Claude Code Analytics, replacing the legacy Streamlit dashboard with a modern single-page application.

## Stack

- **React 19** with TypeScript
- **Vite 7** for dev server and builds
- **TanStack Query v5** for data fetching and cache management
- **TanStack Virtual v3** for virtualized scrolling of large conversation lists
- **Base UI** (headless) + **Tailwind CSS v4** for styling
- **Lucide React** for icons
- **React Router v7** for client-side routing

## Getting Started

```bash
# Install dependencies
npm install

# Start dev server (port 5173) — requires the API server on port 8000
npm run dev

# Type check
npx tsc --noEmit

# Build for production
npm run build
```

The dev server proxies `/api` requests to the FastAPI backend at `localhost:8000`.

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | KPI cards, daily charts, activity heatmap, projects table |
| `/active` | Active | Live active Claude Code sessions |
| `/sessions` | Sessions | Split-view: filterable session list + detail preview |
| `/sessions/:id` | Session Detail | Full conversation viewer with virtual scrolling and minimap |
| `/bookmarks` | Bookmarks | Saved conversation bookmarks |
| `/search` | Search | FTS5 search with scope tabs, project/tool filters, keyboard nav |
| `/analytics` | Analytics | Tool usage, MCP stats, daily trends charts |
| `/analysis` | Analysis | LLM-powered session analysis with scoping and Gist publishing |
| `/examples` | Examples | Natural language prompt/session discovery (FTS + LLM) |
| `/import` | Import | Streaming import with SSE progress |

## Architecture

```
src/
├── api/
│   ├── client.ts          # Typed API client (get/post helpers)
│   └── types.ts           # TypeScript interfaces matching Pydantic models
├── components/
│   ├── app-sidebar.tsx     # Navigation sidebar with project list
│   ├── command-palette.tsx # Cmd+K command palette
│   ├── conversation/       # Conversation viewer components
│   │   ├── conversation-viewer.tsx
│   │   ├── conversation-message.tsx
│   │   └── conversation-minimap.tsx
│   └── ui/                # Base UI primitives (button, input, select, etc.)
├── hooks/
│   └── use-event-source.ts # SSE hook for real-time cache invalidation
├── pages/                  # One file per route
├── lib/
│   └── utils.ts           # cn() helper for Tailwind class merging
└── App.tsx                # Router + QueryClient setup
```

## Real-Time Updates

The app connects to `/api/events` via SSE. When the backend's file watcher detects a new session file, it imports it and publishes an event. The frontend's `useEventSource` hook invalidates relevant query caches (projects, sessions, analytics) so data refreshes automatically.
