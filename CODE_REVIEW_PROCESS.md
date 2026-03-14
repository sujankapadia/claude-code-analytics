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
2. Run tests to verify nothing breaks
3. Commit with `Fixes #N` in the commit message (auto-closes the issue on merge)
4. Reply on the PR review comment confirming the fix with the commit SHA
5. Verify the issue is closed

### If dismissing:

1. Reply on the PR review comment explaining why the finding doesn't apply
2. Close the GitHub Issue as "not planned" with a brief explanation

### If deferring:

1. Reply on the PR review comment acknowledging the issue and noting it's deferred
2. Leave the GitHub Issue open for future work
3. Optionally add a label (e.g., `low-priority`) to the issue

## 4. Verify

After all findings are resolved, check that:
- All tests pass
- All issues are either closed or explicitly deferred with rationale
- All PR review comments have responses
