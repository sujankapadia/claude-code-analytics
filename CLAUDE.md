- Always test or ask the developer to test, depending on the nature of the implementation or fix, before committing and pushing changes.

## Architecture

This project has two frontends:

- **Streamlit dashboard** (legacy) — `claude_code_analytics/streamlit_app/` — launched via `claude-code-analytics` CLI
- **React frontend** (new) — `frontend/` — Vite + React + TypeScript + TanStack Query, served at `localhost:5173`

Both share a common backend:

- **FastAPI API** — `claude_code_analytics/api/` — REST endpoints under `/api`, SSE for real-time events, file watcher for auto-import
- **Database layer** — `claude_code_analytics/streamlit_app/services/database_service.py` — shared by both frontends via the API's dependency injection

## Development Workflow

```bash
# Start the API server (port 8000)
claude-code-api
# or: python -m uvicorn claude_code_analytics.api.app:create_app --factory --port 8000

# Start the React dev server (port 5173) — proxies API calls to 8000
cd frontend && npm run dev
```

The API includes a file watcher that auto-imports new sessions from `~/.claude/projects/` as they appear, with SSE events pushed to the frontend for cache invalidation.

## Key Conventions

- API routers live in `claude_code_analytics/api/routers/`, one file per domain (projects, sessions, search, analytics, analysis, examples, import_data, events)
- Frontend pages in `frontend/src/pages/`, one file per route
- API client in `frontend/src/api/client.ts` with typed responses from `frontend/src/api/types.ts`
- Pre-commit hooks run black, ruff, ruff-format, and bandit — black and ruff-format conflict on f-string quotes, use `SKIP=black` if needed
