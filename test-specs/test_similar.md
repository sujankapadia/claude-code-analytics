# test_similar.py Spec

Source: `claude_code_analytics/api/routers/similar.py`
Test: `tests/test_similar.py`

## _fts_session_search(db, query)

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| F1 | Query matches messages in 2 different sessions | Returns 2 sessions, each with correct hit count and score weighted at 1.0 per hit | Sessions with message matches don't appear in results |
| F2 | Query matches tool inputs in a session | Score is weighted at 1.5 per hit | Tool input matches (stronger signal) rank the same as messages, degrading result quality |
| F3 | Query matches both messages and tool inputs in same session | Single session entry with combined score from both scopes | Session appears twice or scores don't combine, producing wrong ranking |
| F4 | FTS raises OperationalError on messages | Returns tool input results only, no crash | One FTS failure crashes entire search instead of degrading gracefully |
| F5 | FTS raises OperationalError on both scopes | Returns empty dict, no crash | Malformed queries crash the endpoint |
| F6 | Hit snippets contain HTML tags | Tags stripped from match text | Raw `<mark>` tags rendered in frontend |

## _rrf_fusion(fts_results, semantic_results)

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| R1 | 3 sessions with different FTS scores | Ranked by RRF score descending (highest FTS score = highest RRF) | Results appear in wrong order |
| R2 | FTS only, no semantic results | Returns valid ranking from FTS alone | Endpoint fails when semantic search is unavailable |
| R3 | Session appears in both FTS and semantic results | RRF score is higher than session in only one list | Hybrid search doesn't boost sessions found by multiple methods |
| R4 | Empty FTS and empty semantic | Returns empty list | Empty inputs cause error |

## find_similar_sessions endpoint

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| E1 | Valid query with matches | Returns 200 with session results, each having sample_matches | Endpoint doesn't return data |
| E2 | Query shorter than 2 chars | Returns 400 with error detail | Single-character queries cause expensive unbounded searches |
| E3 | exclude_session parameter set | Excluded session not in results | User sees the session they're currently viewing in "similar" results |
| E4 | limit=2 with 5 matching sessions | Returns only 2 results, total_sessions=5, has_more=true | Limit not enforced, frontend gets more data than requested |
| E5 | No matches for query | Returns 200 with empty results list and total_sessions=0 | No-match case crashes or returns wrong status |
| E6 | Sample matches deduped by message_index | No duplicate message_index within a session's matches | Same message appears multiple times in a session's match list |
| E7 | offset=2 with 5 matching sessions, limit=2 | Returns sessions 3-4 (skipping first 2), has_more=true | Pagination broken, users can't see results beyond first page |
| E8 | offset beyond total results | Returns empty results, has_more=false | Out-of-range offset causes error or returns stale data |
| E9 | sort=date_asc with sessions having different start_times | Results ordered by start_time ascending (oldest first) | Temporal queries ("when did I first...") return wrong order |
| E10 | sort=date_desc with sessions having different start_times | Results ordered by start_time descending (newest first) | "Recent discussions about X" returns oldest sessions first |
| E11 | sort=relevance (default) | Results ordered by RRF score descending (same as before) | Default sort changed unexpectedly |
| E12 | Default limit is 20 (changed from 10) | Query without explicit limit returns up to 20 results | Users still see only 10 results by default |

## Notes
- Endpoint tests use a standalone FastAPI app with the similar router and FastAPI dependency_overrides for mock DB
- F6 constructs hit dict directly rather than using helper, since snippet field needs separate override
- Removed unused imports (asynccontextmanager, patch) after switching to dependency_overrides
- R3 uses dict() instead of dict comprehension per ruff C416
- Endpoint fixture overrides both get_db_service and get_embedding_service (None for FTS-only tests)
- Endpoint path changed from /sessions/similar to /search/sessions to avoid route conflict
- E7-E12: Pagination (offset) and sorting (sort param) tests use _make_session_summary helper with mock start_times
- E4 updated to also assert has_more=true (new response field)
- E9/E10 sorting tests need mock summaries with distinct start_times to verify order
- E12 creates 25 sessions to verify default limit of 20 is applied
