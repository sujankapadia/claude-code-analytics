# Test Spec: test_database_service

## Purpose
Tests for DatabaseService — SQLite queries for sessions, messages, search, analytics.

## Test fixes

### test_search_messages_invalid_fts_syntax
The `_sanitize_fts_query` function now escapes special characters (including unmatched quotes), so invalid FTS syntax no longer raises `sqlite3.OperationalError`. Update the test to verify that the sanitizer handles the query gracefully and returns empty results instead of raising.
