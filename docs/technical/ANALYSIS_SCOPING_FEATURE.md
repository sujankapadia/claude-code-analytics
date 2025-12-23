# Analysis Scoping Feature

## Overview

Enhance the AI-powered analysis feature to support scoped analysis instead of always analyzing entire sessions. This addresses context window limitations and cost concerns for large sessions.

## Features

### 1. Date/Time Range Filtering

**Goal:** Allow users to analyze only messages within a specific time range of a session.

**Use Cases:**
- "Analyze just yesterday's work"
- "Focus on the morning session before the bug appeared"
- "Skip the initial setup and analyze the main work"

**Implementation Details:**

#### Backend Changes

**File:** `claude_code_analytics/streamlit_app/services/analysis_service.py`

- Add method: `get_messages_in_range(session_id, start_time, end_time)`
  - Query messages table filtered by timestamp
  - Query tool_uses table filtered by timestamp
  - Format into simple transcript format (not pretty-printed)
  - Return formatted string

- Modify: `analyze_session()`
  - Add parameters: `start_time: Optional[datetime]`, `end_time: Optional[datetime]`
  - When time range provided, use `get_messages_in_range()` instead of reading transcript file
  - When no time range, use existing behavior (full session)

**Simple Transcript Format:**
```
[User - 2024-12-23 10:15:32]
Help me debug this error

[Assistant - 2024-12-23 10:15:45]
Let me check the logs.

[Tool: Bash - 2024-12-23 10:15:46]
Input: tail -n 50 /var/log/app.log
Result: Error: Connection timeout
```

**Token Estimation:**
- Use `tiktoken` library for accurate token counting
- Model: `cl100k_base` (compatible with most modern LLMs)
- Show estimation before running analysis

#### UI Changes

**File:** `claude_code_analytics/streamlit_app/pages/analysis.py`

Add new section after session selector, before analysis type:

```python
st.subheader("Analysis Scope")

scope_mode = st.radio(
    "Choose scope:",
    ["Entire Session", "Date/Time Range"],
    horizontal=True
)

if scope_mode == "Date/Time Range":
    # Date/time pickers
    # Preview: message count and estimated tokens
    # Warning if tokens > threshold
```

**Token Warning Thresholds:**
- 🟢 Green: < 100,000 tokens
- 🟡 Yellow: 100,000 - 200,000 tokens (+ cost estimate)
- 🔴 Red: > 200,000 tokens (may fail)

---

### 2. Search Hit Context Window (Future Phase)

**Goal:** Analyze a specific search result with configurable context messages before/after.

**Use Cases:**
- "Why did this error happen?" (analyze error message + surrounding context)
- "What led to this decision?" (analyze specific discussion + context)
- "Debug this tool failure" (analyze failed tool use + context)

**Workflow:**

1. **Search Page** (`pages/search.py`)
   - User searches for "error timeout"
   - Gets list of matching messages/tools
   - Selects ONE specific hit
   - Clicks "🔬 Analyze with Context" button
   - Redirects to analysis page with hit information

2. **Analysis Page** (`pages/analysis.py`)
   - New scope option: "Around Search Hit"
   - Shows: Selected hit details (message snippet, timestamp)
   - Slider: Context window (1-20 messages before/after)
   - Preview: Total messages and estimated tokens
   - Formats with markers for search hit vs context

**Implementation Details:**

#### Backend Changes

**File:** `claude_code_analytics/streamlit_app/services/analysis_service.py`

- Add method: `get_messages_around_index(session_id, message_index, context_window)`
  - Calculate range: `[message_index - context_window, message_index + context_window]`
  - Query messages in range
  - Query tool uses in range
  - Format with markers distinguishing search hit from context

**Format with Markers:**
```
[CONTEXT - Message 42]
Previous message...

[CONTEXT - Message 43]
Another message...

>>> SEARCH HIT - Message 44 <<<
[User - 2024-12-23 10:30:15]
Getting "error timeout" when connecting
>>> END SEARCH HIT <<<

[CONTEXT - Message 45]
Following message...
```

#### UI Changes

**Search Page:** Add analyze button for each result
**Analysis Page:** Add "Around Search Hit" scope mode

---

## Technical Decisions

### Format Choice
- **Decision:** Use simpler format instead of pretty-printed
- **Rationale:**
  - ~50% fewer tokens (more cost-efficient)
  - Same semantic content for LLM
  - Easier to parse programmatically
  - No visual formatting needed for LLM consumption

### Token Estimation
- **Decision:** Use `tiktoken` library
- **Rationale:**
  - Accurate token counts (not approximation)
  - Fast performance (<100ms even for large texts)
  - Industry standard for OpenAI-compatible models

### Implementation Order
1. **Phase 1:** Date/Time Range Filtering
   - Simpler to implement
   - More general use case
   - Tests the infrastructure

2. **Phase 2:** Search Hit Context Window
   - Builds on Phase 1 infrastructure
   - More complex UI integration
   - Requires search page modifications

---

## Dependencies

**New Dependency:**
- `tiktoken` - Token counting library

Add to `pyproject.toml`:
```toml
tiktoken = "^0.5.0"
```

---

## Testing Plan

### Date/Time Range
1. Small range (10 messages) - verify correct filtering
2. Large range (1000+ messages) - verify token estimation
3. Edge cases:
   - Start = session start
   - End = session end
   - Start = End (single timestamp)
   - Invalid range (start > end)

### Search Context (Phase 2)
1. Hit near start (limited "before" context)
2. Hit near end (limited "after" context)
3. Various context window sizes (1, 5, 20)
4. Edge cases:
   - First message as hit
   - Last message as hit

---

## Success Criteria

- ✅ Users can analyze date/time ranges with token preview
- ✅ Token estimation accurate within ±10%
- ✅ Cost warnings displayed appropriately
- ✅ Simple format reduces token usage by ~40-50% vs pretty-printed
- ✅ Search hit analysis works from search page (Phase 2)
- ✅ Context window configurable and preview accurate (Phase 2)

---

## Future Enhancements

- Multiple search hits analysis (with merged contexts)
- Message count limits ("First N" / "Last N")
- Tool-focused analysis (only messages with specific tool uses)
- Two-pass analysis for very large sessions (summarize + analyze)
- Smart sampling (first + last + every Nth message)
