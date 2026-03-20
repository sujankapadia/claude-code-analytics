# test_embedding_service.py Spec

Source: `claude_code_analytics/services/embedding_service.py`
Test: `tests/test_embedding_service.py`

## embed_session(session_id, messages, project_name)

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| E1 | Session with 3 user messages (>20 chars each) | Returns 3, collection count increases by 3 | Messages not indexed, semantic search returns nothing |
| E2 | Messages include non-user roles | Only user messages embedded | Assistant boilerplate pollutes the embedding index |
| E3 | Short messages (<20 chars) like "Yes", "ok" | Skipped, not embedded | Noise from approvals degrades search quality |
| E4 | Compaction message ("This session is being continued...") | Skipped, not embedded | Compaction summaries treated as user intent |
| E5 | Re-embed same session (upsert) | No duplicates, count stays same | Duplicate embeddings skew search results |

## search(query, n_results)

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| S1 | Query similar to indexed message | Returns hits with similarity > 0.2 | Semantic search returns nothing for valid queries |
| S2 | Empty collection | Returns empty list, no error | Search crashes on empty index |
| S3 | Results include session_id, message_index, similarity, text | All fields populated | Frontend can't display or deep-link results |

## search_expanded(query, expansions, n_results_per)

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| X1 | Query + 2 expansions, some overlap in results | Deduplicated by doc_id, best similarity kept | Duplicate results inflate scores |

## build_index(db_service)

| ID | Scenario | Assertion | Risk if broken |
|----|----------|-----------|----------------|
| B1 | DB with 2 sessions, 5 user messages total | Returns 5, collection count is 5 | Initial index fails, no semantic search available |

## Notes
- All tests use in-memory ChromaDB (ephemeral Client) with unique collection names for isolation
- ChromaDB's default sentence-transformer model runs locally, no API needed
