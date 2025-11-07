{#
PROMPT: Error Pattern Analysis
PURPOSE: Identify error patterns, root causes, and resolutions from conversation transcripts
AUTHOR: Claude Code Utilities
CREATED: 2025-10-15
LAST_UPDATED: 2025-10-15

Required Variables:
  - transcript (str): The full conversation text

Optional Variables:
  - None currently

Output Format:
  - Error/Problem Breakdown (numbered list, each with context, root cause, detection, resolution, time to fix, prevention)
  - Error Pattern Summary (common types, longest to resolve, quick wins, root causes, prevention strategies, tool-specific issues)

Notes:
  - Focus on meaningful errors requiring debugging or rework
  - Skip typos or trivial formatting issues
  - Capture both the error and the learning/prevention aspect
  - Time to fix should be approximate (quick fix, moderate debugging, extensive troubleshooting)
#}

Analyze this Claude Code conversation transcript for error patterns and problem resolution.

For each significant error or obstacle encountered:

1. **Error/Problem:** What went wrong (be specific)
2. **Context:** What was being attempted when the error occurred
3. **Root Cause:** Why it happened (if discussed or evident)
4. **Detection:** How was it discovered (test failure, runtime error, Claude noticed, user spotted, tool error)
5. **Resolution:** How it was fixed
6. **Time to Fix:** Approximate effort (quick fix, moderate debugging, extensive troubleshooting)
7. **Prevention:** Any safeguards added to prevent recurrence

Then provide an **Error Pattern Summary**:

- **Most Common Error Types:** (e.g., syntax, logic, configuration, API misunderstanding, tooling issues)
- **Longest to Resolve:** Which issues took the most back-and-forth
- **Quick Wins:** Errors that were fixed immediately
- **Root Cause Patterns:** Recurring reasons for errors (unclear requirements, wrong assumptions, missing documentation)
- **Prevention Strategies:** What was learned or implemented to avoid future errors
- **Tool-Specific Issues:** If certain tools (Edit, Bash, Read, etc.) had higher error rates

Focus on meaningful errors that required debugging or rework. Skip typos or trivial formatting issues.

---

CONVERSATION TRANSCRIPT:

{{ transcript }}
