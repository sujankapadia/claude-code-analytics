# Shared Services

This directory contains the shared business logic layer used by the FastAPI API:

- **`services/database_service.py`** — SQLite queries (sessions, messages, search, analytics)
- **`services/analysis_service.py`** — LLM analysis orchestration (OpenRouter, Gemini)
- **`services/format_utils.py`** — Duration, character count, and percentage formatting
- **`models/`** — Pydantic data models matching the database schema

> **Note:** This directory retains the `streamlit_app` name for backwards compatibility.
> The Streamlit dashboard has been removed; the React frontend is the only UI.
