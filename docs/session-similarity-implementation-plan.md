# Session Similarity Search — Backend Implementation Plan

## Overview

Build the backend for hybrid session similarity search: FTS keyword search + ChromaDB message-level embeddings + LLM query expansion, fused via Reciprocal Rank Fusion (RRF).

See `docs/session-similarity-search-proposal.md` for the full design and prototype results.

## New Files

```
claude_code_analytics/
  services/
    embedding_service.py        # ChromaDB lifecycle, embed, query
  api/
    routers/
      similar.py                # GET /api/sessions/similar endpoint
```

## Modified Files

```
claude_code_analytics/
  api/
    app.py                      # Register similar router
    dependencies.py             # Add get_embedding_service()
    services/
      file_watcher.py           # Embed new messages after import
  config.py                     # Add CHROMA_DATA_DIR config
pyproject.toml                  # Add chromadb dependency
```

## Implementation Steps

### Step 1: Config and Dependencies

**`pyproject.toml`** — Add `chromadb` to dependencies.

**`config.py`** — Add:
```python
# Similarity search
CHROMA_DATA_DIR = _expanduser(
    os.getenv("CHROMA_DATA_DIR", str(CLAUDE_CONVERSATIONS_DIR / "chroma"))
)

# Query expansion provider (any OpenAI-compatible endpoint)
EXPANSION_BASE_URL = os.getenv("EXPANSION_BASE_URL", "http://localhost:11434/v1")
EXPANSION_MODEL = os.getenv("EXPANSION_MODEL", "qwen3:8b")
EXPANSION_API_KEY = os.getenv("EXPANSION_API_KEY", "")
```

### Step 2: EmbeddingService

**`claude_code_analytics/services/embedding_service.py`**

Responsibilities:
- Manage a persistent ChromaDB client and `user_messages` collection
- Provide `embed_session(session_id, messages)` for incremental indexing
- Provide `search(query, n_results)` for semantic search
- Provide `build_index(db_service)` for initial batch indexing
- Provide `collection_count()` for status checks

Key design decisions:
- **Persistent storage** at `config.CHROMA_DATA_DIR` — survives restarts
- **Collection name**: `user_messages`
- **Document ID format**: `{session_id}:{message_index}` — deduplicated by default
- **Metadata per document**: `session_id`, `project` (short name), `message_index`
- **Filtering**: Skip messages < 20 chars, skip compaction messages
- **Cap per message**: 1,000 chars before embedding (longer messages truncated)
- **Thread safety**: ChromaDB's PersistentClient is thread-safe for reads. Writes should be serialized (fine — imports are sequential per session)

```python
class EmbeddingService:
    def __init__(self, persist_dir: str | None = None):
        """Initialize with persistent ChromaDB storage."""

    def embed_session(self, session_id: str, messages: list[Message], project_name: str) -> int:
        """Embed user messages from a session. Returns count of new embeddings added."""

    def search(self, query: str, n_results: int = 20) -> list[dict]:
        """Semantic search. Returns list of {session_id, message_index, similarity, text, project}."""

    def search_expanded(self, query: str, expansions: list[str], n_results_per: int = 15) -> list[dict]:
        """Search with query + all expansions, deduplicate by session_id:message_index."""

    def build_index(self, db_service: DatabaseService) -> int:
        """Batch index all existing sessions. Returns total messages embedded."""

    def collection_count(self) -> int:
        """Number of documents in the collection."""
```

### Step 3: Query Expansion

Query expansion lives in the `/similar` router (not a separate service), since it's a simple OpenAI-compatible API call. If the provider is unavailable, it returns an empty list and the search falls back to FTS + unexpanded semantic.

```python
def _expand_query(query: str) -> list[str]:
    """Expand query via LLM. Returns empty list on failure."""
```

Prompt (validated in prototype):
```
List 6 alternative phrases a software developer might use
when discussing "{query}". Comma-separated only, no explanation.
```

**Provider configuration via env vars** (in `.env` or environment):

```
EXPANSION_BASE_URL=http://localhost:11434   # Any OpenAI-compatible endpoint
EXPANSION_MODEL=qwen3:8b                    # Small/cheap model preferred
EXPANSION_API_KEY=                           # Optional, depends on provider
```

Defaults to Ollama on localhost — works out of the box if the user has Ollama running. Can point at OpenRouter, LM Studio, or any OpenAI-compatible API.

Uses the existing `OpenAICompatibleProvider.generate()` infrastructure so we don't duplicate HTTP/auth logic. The expansion function creates a lightweight provider instance from these config values.

**`config.py`** additions:
```python
EXPANSION_BASE_URL = os.getenv("EXPANSION_BASE_URL", "http://localhost:11434/v1")
EXPANSION_MODEL = os.getenv("EXPANSION_MODEL", "qwen3:8b")
EXPANSION_API_KEY = os.getenv("EXPANSION_API_KEY", "")
```

A future settings page (#50) could manage these values via the UI instead of .env files.

### Step 4: FTS Session Search

A helper function in the `/similar` router that wraps existing `DatabaseService` search methods and aggregates by session:

```python
def _fts_session_search(db: DatabaseService, query: str) -> dict[str, FTSSessionResult]:
    """Run FTS across messages, tool inputs, tool results. Aggregate by session."""
```

Calls:
- `db.search_messages(query, limit=200)` — weight 1.0
- `db.search_tool_inputs(query, limit=200)` — weight 1.5

Tool results are excluded — they're too noisy (large file dumps, verbose command output) and the
prototype showed they inflate hit counts without improving ranking quality. Messages and tool inputs
are sufficient to identify relevant sessions.

Returns dict keyed by session_id with hit counts, weighted score, and sample snippets per session.

### Step 5: RRF Fusion

```python
def _rrf_fusion(
    fts_results: dict[str, FTSSessionResult],
    semantic_results: dict[str, SemanticSessionResult],
    k: int = 60,
) -> list[FusedResult]:
    """Reciprocal Rank Fusion of FTS and semantic ranked lists."""
```

Formula: `score(session) = Σ 1/(k + rank_in_fts) + Σ 1/(k + rank_in_semantic)`

Sessions appearing in both lists rank higher than either alone.

### Step 6: API Endpoint

**`claude_code_analytics/api/routers/similar.py`**

```
GET /api/sessions/similar?q=deploying+to+production&limit=10&exclude_session=abc123
```

Flow:
1. Validate query (min 2 chars)
2. Run query expansion in thread executor (async, ~1-2s)
3. Run FTS search (sync, ~200ms)
4. Run semantic search with expansions in thread executor (async, ~100ms)
5. RRF fusion
6. Enrich top N results with session metadata (project name, dates, message count)
7. Return top 5 matching messages per session (deduped, ranked by relevance) with `message_index` for deep-linking
8. Return response

Steps 2-4 can run in parallel with `asyncio.gather`.

Response shape:
```json
{
  "query": "deploying to production",
  "expansions": ["pushing to live", "going live", "rolling out"],
  "results": [
    {
      "session_id": "abc123",
      "project_name": "/Users/.../lxr",
      "score": 0.0292,
      "fts_hits": 3,
      "semantic_best": 0.53,
      "start_time": "2026-02-15T10:00:00Z",
      "message_count": 175,
      "tool_use_count": 45,
      "sample_matches": [
        {
          "source": "semantic",
          "similarity": 0.53,
          "message_index": 463,
          "text": "let's continue with the deploy",
          "matched_via": "rolling out to production"
        },
        {
          "source": "fts",
          "message_index": 107,
          "text": "How easy is this to deploy to Digital Ocean?"
        },
        {
          "source": "semantic",
          "similarity": 0.50,
          "message_index": 112,
          "text": "How much would Digital Ocean cost per month?",
          "matched_via": "pushing to live"
        }
      ]
    }
  ],
  "total_sessions": 15
}
```

### Step 7: Dependency Injection

**`dependencies.py`** — Add:
```python
@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
```

### Step 8: Register Router

**`app.py`** — Add:
```python
from claude_code_analytics.api.routers import similar
app.include_router(similar.router, prefix="/api")
```

### Step 9: File Watcher Integration

**`file_watcher.py`** — After a successful session import, embed the new messages:

```python
async def _import_session(self, path: Path) -> None:
    result = await loop.run_in_executor(None, import_single_session, path)
    if result:
        # Embed new messages for similarity search
        await loop.run_in_executor(None, self._embed_session, path.stem)
        await self.event_bus.publish(...)
```

The `_embed_session` method fetches messages from the DB and calls `embedding_service.embed_session()`. This is lazy — if ChromaDB isn't initialized yet (first run), it skips silently.

### Step 10: Initial Index Build

Two options for building the initial index:

**Option A: On-demand** — First call to `/api/sessions/similar` checks `collection_count()`. If zero, triggers a background index build and returns a "building index" response. Subsequent calls work normally.

**Option B: CLI command** — New entry point `claude-code-embed` that runs `build_index()`. User runs it once after install.

**Recommendation: Option A** with a status endpoint. The first search takes ~70s but subsequent ones are instant. The `/similar` endpoint returns `{"status": "indexing", "progress": 250, "total": 500}` during the build.

## Graceful Degradation

The system works at each layer independently:

| State | Behavior |
|-------|----------|
| ChromaDB empty (first run) | FTS-only results, plus "building index" status |
| Expansion provider unavailable | FTS + semantic (no expansion), still useful |
| ChromaDB + expansion unavailable | FTS-only, same quality as Phase 1 |
| FTS returns nothing | Semantic-only results |
| Everything available | Full hybrid with expansion |

No hard dependencies — the endpoint always returns something useful.

## Frontend Integration

### Approach: New Tab on Existing Search Page

Session similarity search lives as a **Sessions** tab alongside the existing scope tabs on the Search page: **All | Messages | Tool Inputs | Tool Results | Sessions**.

Same search input, same page. The tab changes what the user gets back.

### Behavior When "Sessions" Tab is Active

- Query runs the hybrid pipeline (FTS + semantic + expansion) via `GET /api/sessions/similar?q=...`
- Results render as **session cards** instead of individual message hits
- Each card shows: project name, session date, message/tool count, relevance score
- Each card contains up to **5 matching messages** with deep links (`/sessions/{id}#msg-{index}`)
- A subtle indicator shows query expansions: "Also searched: infinite scroll, load more, offset and limit"

### Progressive Loading

The Sessions tab is slower than other tabs (~2s for expansion vs ~200ms for FTS). To keep it responsive:

1. **Immediate**: Show FTS-only session results (~200ms) — keyword matches appear instantly
2. **Background**: Run query expansion + semantic search in parallel
3. **Enrich**: When expansion/semantic results arrive, merge via RRF and re-render the full hybrid results
4. **Indicator**: Show a subtle "Expanding search..." badge while the semantic layer loads

This way the user sees useful results immediately and they get better as the semantic layer completes.

### Modified Files (Frontend)

```
frontend/src/
  pages/
    search.tsx              # Add Sessions tab, session card rendering, progressive loading
  api/
    client.ts               # Add fetchSimilarSessions() API call
    types.ts                # Add SimilarSessionResult type
```

No new pages or routes needed — it's an enhancement to the existing search page.

### Session Card Design

```
┌─────────────────────────────────────────────────────┐
│ lxr                          Feb 15 · 175 msgs · 45 tools │
│ Score: ██████░░░░                                   │
│                                                     │
│ 🔍 "let's continue with the deploy"           #463  │
│ 🔍 "How easy is this to deploy to DO?"         #107  │
│ 📝 Tool: edited deploy/Dockerfile              #220  │
│                                                     │
│ Also matched via: rolling out to production         │
└─────────────────────────────────────────────────────┘
```

Each message line is a link to `/sessions/{id}#msg-{index}`. The icon indicates source (🔍 semantic, 📝 FTS).

## Testing Strategy

### Unit Tests
- `EmbeddingService`: embed, search, build_index with in-memory ChromaDB client
- `_expand_query`: mock Ollama response
- `_fts_session_search`: mock DatabaseService search methods
- `_rrf_fusion`: test ranking with known inputs

### Integration Test
- Full flow: create test DB with known sessions, embed, search, verify results

### Manual Verification (Playwright)
- Navigate to Search page, click Sessions tab
- Enter query, verify FTS results appear immediately
- Verify semantic results merge in after ~2s
- Verify session cards show project, date, matching messages
- Click a matching message link, verify deep-link scrolls to correct message
- Verify expansions indicator shows

## Estimated Scope

| Step | Files | Complexity |
|------|-------|-----------|
| 1. Config + deps | 2 | Trivial |
| 2. EmbeddingService | 1 new | Medium — core logic |
| 3. Query expansion | Part of router | Small |
| 4. FTS session search | Part of router | Small — wraps existing methods |
| 5. RRF fusion | Part of router | Small — pure function |
| 6. API endpoint | 1 new | Medium — orchestration |
| 7-8. DI + registration | 2 | Trivial |
| 9. File watcher | 1 | Small |
| 10. Initial index | Part of embedding service | Small |
| Tests | 1-2 new | Medium |

| Frontend: Sessions tab | 3 modified | Medium — new tab, card component, progressive loading |

Total: ~2 new backend files, ~5 modified backend files, ~3 modified frontend files.

## Iterative Build Plan

Each iteration delivers a working, testable increment. We don't move to the next iteration until the current one is verified.

### Iteration 1: FTS Session Search (backend only, no new deps)

**Build:**
- Step 4: `_fts_session_search()` — wraps existing DatabaseService methods
- Step 5: `_rrf_fusion()` — pure function (only FTS input for now, semantic input empty)
- Step 6: API endpoint `GET /api/sessions/similar?q=...` — FTS-only mode
- Steps 7-8: DI + router registration

**Test:**
- Unit tests for `_fts_session_search` and `_rrf_fusion`
- `curl` the endpoint, verify session-level results come back
- Compare results against prototype FTS output

**What this proves:**
- The API shape works
- FTS session aggregation produces useful results
- The endpoint is wired up and returning data

**Assumptions:**
- Existing `search_messages()` and `search_tool_inputs()` return enough data for session aggregation
- The weighting (messages 1.0 / tool inputs 1.5) produces reasonable ranking (**validate** — may need tuning)

**Failure modes:**
- FTS queries that return too many results (>1000 hits) could be slow to aggregate → mitigate with `limit=200` per scope

### Iteration 2: ChromaDB Embedding (backend, new dep)

**Build:**
- Step 1: Add `chromadb` dependency, `CHROMA_DATA_DIR` config
- Step 2: `EmbeddingService` — persist, embed, search, build_index
- Step 10: On-demand initial index build
- Wire semantic results into the `/similar` endpoint alongside FTS
- RRF fusion now merges both lists

**Test:**
- Unit tests for EmbeddingService with in-memory ChromaDB
- Run `build_index()`, verify message count matches expectations
- `curl` the endpoint, compare hybrid results vs FTS-only — are they better?
- Test the "pagination" query specifically — does semantic find sessions FTS missed?

**What this proves:**
- ChromaDB persistent storage works across restarts
- Message-level embeddings produce useful similarity scores
- Hybrid fusion improves results over FTS alone

**Assumptions:**
- ChromaDB's default embedding model (all-MiniLM-L6-v2) is sufficient (**validated** in prototype, but verify in production context)
- 3,500 messages embed in ~70s (**validated**, but verify with persistent client vs in-memory)
- ChromaDB PersistentClient runs in-process without issues (**verify** — prototype used ephemeral Client)

**Failure modes:**
- ChromaDB import adds ~50MB to install size → acceptable for the value, but document in install notes
- First search triggers 70s index build → return FTS-only results immediately with "indexing" status
- ChromaDB file corruption on crash → catch errors, fall back to FTS-only, log warning to rebuild
- PersistentClient startup time → measure; if slow, lazy-initialize on first search rather than app startup

### Iteration 3: Query Expansion (backend, requires LLM provider)

**Build:**
- Step 1 (continued): Add `EXPANSION_BASE_URL`, `EXPANSION_MODEL`, `EXPANSION_API_KEY` config
- Step 3: `_expand_query()` function using OpenAICompatibleProvider
- Wire expansions into semantic search (search original + expanded queries)
- Update API response to include `expansions` field

**Test:**
- Unit test with mocked provider response
- Manual test: verify expansion works with Ollama locally
- Manual test: verify expansion works with OpenRouter
- Test graceful degradation — kill Ollama, verify endpoint still returns FTS + semantic results
- Compare "pagination" results with and without expansion — does it find "infinite scroll" sessions?

**What this proves:**
- Provider-agnostic expansion works with different backends
- Graceful degradation when provider is unavailable
- Query expansion measurably improves recall

**Assumptions:**
- The simple prompt ("List 6 alternative phrases...") works across different models (**validated** with qwen3:8b, **verify** with at least one other model)
- Expansion adds ~1-2s latency (**validated**, but verify with OpenRouter which has network overhead)
- 6 expansions is the right number — too few misses synonyms, too many adds noise (**verify** — try 4 and 8 to compare)

**Failure modes:**
- LLM returns malformed response (not comma-separated) → parse defensively, return empty list on failure
- LLM returns irrelevant expansions → doesn't break anything, just adds noise to semantic search; low similarity scores filter it out
- Expansion provider has high latency (>5s) → timeout at 10s, fall back to no expansion
- Expansion costs money per search (if using paid API) → document this; recommend local model for expansion

### Iteration 4: File Watcher Integration (backend)

**Build:**
- Step 9: After session import, embed new messages in ChromaDB

**Test:**
- Start the app, create a new Claude Code session, end it
- Verify the file watcher imports the session AND embeds the messages
- Search for content from the new session — verify it appears in results

**What this proves:**
- New sessions are automatically searchable without manual re-indexing

**Assumptions:**
- Embedding a single session's messages is fast enough to not delay the import pipeline (**verify** — should be <1s for typical sessions)
- The EmbeddingService singleton is accessible from the file watcher context

**Failure modes:**
- Import succeeds but embedding fails → log error, don't block import; messages will be embedded on next `build_index`
- Race condition: search runs while embed is in progress → ChromaDB handles concurrent read/write, but verify

### Iteration 5: Frontend — Sessions Tab

**Build:**
- Add `fetchSimilarSessions()` to API client
- Add `SimilarSessionResult` type
- Add Sessions tab to Search page scope tabs
- Session card component with matching messages and deep links
- Progressive loading: FTS results first, semantic enriches

**Test (Playwright):**
- Navigate to Search, click Sessions tab
- Enter "pagination" — verify session cards appear
- Verify matching messages show with deep links
- Click a message link — verify it navigates to the correct session and scrolls to the message
- Verify expansion indicator shows
- Verify FTS results appear before semantic results (progressive loading)
- Test with expansion provider offline — verify FTS-only results still render

**What this proves:**
- End-to-end flow works from search input to deep-linked message
- Progressive loading provides good UX despite 2s expansion latency

**Assumptions:**
- The existing search page layout accommodates session cards without a redesign
- 5 matching messages per card is the right density — not too cluttered (**verify** visually)

**Failure modes:**
- Session cards take too much vertical space → add expand/collapse per card
- Deep links don't scroll correctly for virtualized message lists → already tested and working from earlier work

## Assumptions Summary

| Assumption | Status | How to Validate |
|-----------|--------|----------------|
| FTS weighting (messages 1.0 / tool inputs 1.5) produces good ranking | Validated in prototype | Compare top 5 results for test queries |
| all-MiniLM-L6-v2 handles natural language queries well | Validated in prototype | Test with production data |
| all-MiniLM-L6-v2 struggles with bare keywords | Validated in prototype | Query expansion compensates |
| 3,500 messages embed in ~70s | Validated (in-memory) | Verify with PersistentClient |
| ChromaDB PersistentClient works in-process | Not yet validated | Test in Iteration 2 |
| Simple expansion prompt works across models | Validated with qwen3:8b | Test with 1-2 other models |
| Expansion adds ~1-2s latency with Ollama | Validated | Verify with remote providers |
| 6 expansions is the right count | Reasonable default | Compare 4/6/8 in Iteration 3 |
| Embedding doesn't slow down file watcher imports | Likely true (<1s per session) | Measure in Iteration 4 |

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| ChromaDB adds 50MB to install | Low | Certain | Document; optional dependency if needed |
| First search is slow (70s index build) | Medium | Certain | Return FTS-only immediately, build in background |
| Expansion provider unavailable | Medium | Likely (local Ollama may not be running) | Graceful degradation to FTS + semantic |
| ChromaDB data corruption | High | Unlikely | Catch errors, rebuild from DB messages |
| Embedding model quality insufficient | Medium | Unlikely (validated) | Swap model via ChromaDB config |
| Expansion adds cost for paid providers | Low | Depends on config | Default to local Ollama; document cost implications |
