{#
PROMPT: Technical Decision Analysis
PURPOSE: Extract technical decisions, alternatives considered, and reasoning from conversation transcripts
AUTHOR: Claude Code Utilities
CREATED: 2025-10-15
LAST_UPDATED: 2025-10-15

Required Variables:
  - transcript (str): The full conversation text

Optional Variables:
  - None currently

Output Format:
  - Executive Summary
  - Key Technical Decisions (numbered list)
  - Revised Decisions (if any)

Notes:
  - Focus on architectural and implementation decisions
  - Skip minor formatting or style choices
  - Capture alternatives even if not explicitly discussed
#}

Review this Claude Code conversation transcript and identify moments where a technical decision was made.

For each decision, extract:
- What was decided
- What alternatives were discussed (if any)
- The reasoning given
- Whether it was later changed/revisited

Format your response as a structured report with:

1. **Executive Summary** (2-3 sentences about the project)

2. **Key Technical Decisions** (numbered list, each with):
   - What was decided
   - Alternatives discussed
   - Reasoning given
   - Changes/revisions (if any)

3. **Revised Decisions** (if any decisions were changed later):
   - Original decision
   - Revised to
   - Reason for change

Focus on architectural, technical, and implementation decisions. Skip minor formatting or style choices.

---

CONVERSATION TRANSCRIPT:

{{ transcript }}
