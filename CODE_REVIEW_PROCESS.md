# Code Review Resolution Process

This document describes how to handle findings from automated code review tools (e.g., CodeRabbit) and human reviewers.

## 1. Capture

Create a GitHub Issue for each finding so nothing is lost. Include:
- Problem description
- Affected file(s) and line numbers
- Suggested fix (if provided)
- Severity (Critical / Major / Minor)
- Source (e.g., "CodeRabbit PR #9 review")

## 2. Evaluate

For each finding, read the issue and the actual code. Decide on one of three outcomes:

- **Fix** — The issue is real and worth addressing now
- **Dismiss** — The finding is a false positive or doesn't apply to our context (e.g., a security concern about a public API that only runs locally)
- **Defer** — The issue is real but low priority or requires larger changes

When evaluating, consider:
- Does the issue actually exist in the current code, or is the reviewer working from stale/incomplete context?
- Does the severity match our deployment model? (e.g., localhost-only tool vs. public-facing service)
- Is the fix straightforward or does it require architectural changes?

## 3. Resolve

### If fixing:

1. Make the code change
2. Add or update tests (see [Testing Guidance](#4-testing-guidance) below)
3. Run tests to verify nothing breaks
4. Commit with `Fixes #N` in the commit message (auto-closes the issue on merge)
5. Reply on the PR review comment confirming the fix with the commit SHA
6. Verify the issue is closed

### If dismissing:

1. Reply on the PR review comment explaining why the finding doesn't apply
2. Close the GitHub Issue as "not planned" with a brief explanation

### If deferring:

1. Reply on the PR review comment acknowledging the issue and noting it's deferred
2. Leave the GitHub Issue open for future work
3. Optionally add a label (e.g., `low-priority`) to the issue

## 4. Testing Guidance

Every fix should have a corresponding test. The type of test depends on what's being fixed and what infrastructure exists.

### Choosing the right test type

| Fix type | Test approach | Example |
|----------|--------------|---------|
| Pure logic (validation, sanitization, query building) | Unit test with `pytest` | Input validation, FTS query escaping |
| API endpoint behavior (status codes, guards, error responses) | Integration test with FastAPI `TestClient` | SPA fallback returning 404 for `/api/` paths |
| Database operations (threading, transactions, queries) | Unit test with in-memory SQLite | Connection thread safety, import service |
| Frontend rendering (XSS, state, error states) | Manual verification with Playwright MCP | `dangerouslySetInnerHTML` sanitization |
| Frontend interaction (forms, navigation, accessibility) | Manual verification with Playwright MCP | Bookmark button keyboard access |

### When a test file already exists

Add a new test case to the existing file covering the specific fix. Name it clearly so the regression is obvious if it ever fails again.

### When no test file exists

- **If unit-testable** — create a new test file (e.g., `tests/test_app.py` for FastAPI endpoint tests)
- **If only manually testable** — document the verification steps in the PR comment and note that automated coverage is pending

### What we have today

- **Unit tests** (`pytest`) — services, models, providers, formatters
- **No frontend tests** — no Jest/Vitest setup (potential future addition)
- **No automated E2E tests** — Playwright MCP is used for manual verification
- **No FastAPI integration tests** — `TestClient` not yet set up (should be added as needed)

### Manual verification

For fixes that can't be unit-tested (frontend behavior, E2E flows), include in the PR comment:
- What you tested (steps to reproduce)
- What you observed (expected vs. actual)
- Screenshot or Playwright snapshot if applicable

## 5. Verify

After all findings are resolved, check that:
- All tests pass (including any new tests added for fixes)
- All issues are either closed or explicitly deferred with rationale
- All PR review comments have responses
