# Prompt & Workflow Discovery

## Problem

Coworkers frequently ask for examples of prompts and workflows — "How do you get Claude Code to run Playwright tests?" or "Show me a prompt that does X." Today, answering these questions requires either:

1. Manually scanning conversation transcripts
2. Asking Claude Code to search through session histories directly (slow, expensive, not using FTS)

Neither scales well. We need a way to quickly find, extract, and share relevant conversation excerpts.

## Implementation

### Phase 1: Tool-Aware Search & Copyable Excerpts (No LLM) — Future

**Tool-name filtering on search and sessions pages**

Add the ability to filter sessions and search results by which tools were used. For example, searching for sessions that invoked `mcp__playwright__browser_navigate` or `Bash` immediately narrows the results to relevant workflows.

Implementation:
- Add a tool-name multi-select filter to the Search page and Sessions page
- Query is pure SQL against the existing `tool_uses` table — no LLM cost
- Combine with existing FTS text search for precision (e.g. "playwright" + tool filter for `mcp__playwright__*`)
- Expose a `/api/analytics/tools/names` endpoint (already exists) to populate the filter options

**Copyable session excerpts**

When you find the right conversation, you need to extract a clean chunk to share. Add a "Copy excerpt" feature to the conversation viewer:

- Select a range of messages (click start message, shift-click end message)
- "Copy as text" button formats the selection as a clean markdown block
- Formatted excerpt is ready to paste into Slack, a doc, or a wiki

### Phase 2: Hybrid FTS + LLM Example Search — Implemented

Two API endpoints for natural language discovery of prompts and sessions:

#### `POST /api/examples/sessions` — Find example sessions

Answers "show me sessions where I did X" — returns ranked sessions with excerpts.

**How it works:**
1. Extract search terms from natural language query (stop-word removal)
2. Detect tool name patterns from keywords (e.g. "playwright" → `mcp__playwright__*`)
3. FTS search + tool-filtered SQL to gather candidate sessions (capped at 20)
4. Build compact summaries (first message, tool breakdown, user message previews, FTS hit snippets)
5. LLM ranks candidates and explains why each is relevant
6. Returns `SessionMatch` objects with `matching_excerpts`

**Request:**
```json
{
  "query": "sessions where I used Playwright to test a UI component",
  "project_id": null,
  "max_results": 5,
  "scope": "All",
  "role": null
}
```

#### `POST /api/examples/prompts` — Find example prompts

Answers "show me a prompt that does X" — returns specific user messages that can be shared as templates.

**How it works:**
1. FTS search for user messages only (`role: "user"`)
2. Supplement with user messages from sessions that used matching tools (when FTS alone returns <20 hits)
3. Fetch full message content (not truncated FTS snippets)
4. Send up to 30 candidates (each ≤1000 chars) to LLM for ranking
5. LLM selects prompts that are self-contained, clearly show the technique, and work as templates
6. Returns `PromptMatch` objects with full prompt text and relevance explanation

**Request:**
```json
{
  "query": "How do I use Playwright to test a UI component?",
  "project_id": null,
  "max_results": 5
}
```

**LLM cost:** Minimal — ~3-8k input tokens per query. FTS + SQL does the heavy lifting; LLM only ranks a small pre-filtered set.

**Model:** DeepSeek v3.2 via OpenRouter (fast, cheap, good at structured ranking tasks).

## Status

| Phase | Status | LLM Cost | Value |
|-------|--------|----------|-------|
| 1. Tool filters + copy excerpts | Future | None | High — covers most "find me a prompt" requests |
| 2. Hybrid example search (sessions + prompts) | **Done** (API) | Low (per query) | High — natural language discovery |
| Frontend UI for example search | In progress | — | Exposes the API to users |
