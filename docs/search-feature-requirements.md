# Search Feature Requirements

## Implementation Progress

**Branch:** `feature/search-functionality`
**Last Updated:** 2025-12-20

### Completed ✅

**Backend (Phase 1)**
- [x] Create FTS5 indexes (3,100 messages, 2,372 tool uses indexed)
- [x] Add SearchResult data model to `database_models.py`
- [x] Update `search_messages()` to use correct `fts_messages` table with offset/date params
- [x] Implement `search_tool_inputs()` method with FTS5
- [x] Implement `search_tool_results()` method with FTS5
- [x] Implement `search_all()` combined search method
- [x] Implement `get_unique_tool_names()` for filter dropdown (35 unique tools)
- [x] Implement `get_mcp_tool_stats()` for MCP analysis (154 uses, 5 servers)
- [x] Test all search methods successfully

**UI (Phase 1)**
- [x] Create search page UI (`pages/search.py`)
- [x] Implement unified search input with scope selector (All/Messages/Tool Inputs/Tool Results)
- [x] Add filter controls:
  - [x] Project dropdown (All Projects + 15 projects)
  - [x] Date range selector (All Time, Last 7/30/90 Days, Custom)
  - [x] Tool name dropdown (All Tools + 35 tools)
- [x] Implement results display grouped by session
- [x] Add pagination controls (10 results per page, Previous/Next buttons)
- [x] Add search result count summary ("X results across Y sessions")
- [x] Style results with role badges, timestamps, snippets
- [x] Test search page with multiple queries successfully

**Deep Linking (Phase 2)**
- [x] Update conversation page to read query params (`session_id`, `message_index`)
- [x] Add message IDs (`msg-{index}`) to conversation display
- [x] Implement highlight CSS with gold border and yellow background
- [x] Add fade animation (3s from 30% to 15% opacity)
- [x] Add JavaScript scroll injection (smooth scroll to center)
- [x] Generate deep link URLs in search results
- [x] Test deep linking end-to-end successfully

### In Progress 🚧
- [ ] MCP Analysis section/tab

### Not Started 📋
- [ ] Loading states polish
- [ ] Mobile responsiveness testing
- [ ] Performance optimization for large result sets
- [ ] Search tips/empty states
- [ ] Keyboard shortcuts

### Testing Results
- ✅ Backend: All 6 search methods working (5 message results, 35 tools, git/error searches working)
- ✅ UI: Search page loads, filters work, pagination tested (Page 1 ↔ Page 2)
- ✅ Scope Filter: Successfully tested Messages scope (10 results across 4 sessions)
- ✅ Deep Linking: URL navigation works, session loads correctly from query params
- ✅ FTS5 Highlighting: Search terms wrapped in `<mark>` tags and displayed correctly

---

## Feature Overview

Add comprehensive search functionality to the Claude Code Analytics dashboard, enabling users to search across conversation messages and tool usage data. The feature includes full-text search, tool-specific search, and MCP (Model Context Protocol) tool analysis.

### Key Capabilities
- Full-text search across all message content
- Search tool inputs and results
- Filter by project, date range, and tool name
- Deep linking to specific messages in conversations
- MCP tool usage analysis and patterns

---

## UI Design

### Page Layout

The search functionality will be implemented as a unified search page with the following structure:

```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search                                                   │
├─────────────────────────────────────────────────────────────┤
│ [Search box.............................................] 🔍 │
│                                                             │
│ Scope: ○ All  ○ Messages  ○ Tool Inputs  ○ Tool Results   │
├─────────────────────────────────────────────────────────────┤
│ Filters:                                                    │
│ Project: [All Projects ▼]  Date Range: [Start - End]       │
│ Tool Name: [All Tools ▼]                                    │
├─────────────────────────────────────────────────────────────┤
│ Results: 47 matches across 12 sessions                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Session: abc123... | claude-code-utils | Dec 19, 2025      │
│ 3 matches in this session                                   │
│                                                             │
│   [User, 10:23 AM]                                         │
│   "...context before... **search term** ...context..."     │
│   [View in Conversation →]                                  │
│                                                             │
│   [Assistant, 10:24 AM]                                    │
│   "...context before... **search term** ...context..."     │
│   [View in Conversation →]                                  │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│                                                             │
│ Session: def456... | wordle-ai | Dec 18, 2025             │
│ 2 matches in this session                                   │
│   ...                                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Pagination: < 1 2 3 ... 10 >                               │
└─────────────────────────────────────────────────────────────┘
```

### Search Input
- **Single search box** for all queries
- **Scope filter** (radio buttons):
  - **All** (default) - searches messages and tools
  - **Messages** - searches only message content
  - **Tool Inputs** - searches only tool input parameters
  - **Tool Results** - searches only tool output/results

### Filters (Inline, above results)
- **Project dropdown**: Filter by specific project or "All Projects"
- **Date range picker**: Start date and end date
- **Tool name dropdown**: Filter by specific tool (e.g., "Bash", "Read", "mcp__playwright__*")
  - Populated from distinct tool names in database
  - Alphabetically sorted
  - MCP tools grouped/highlighted

### Results Display
- **Grouped by session** (collapsible sections)
- **10 results per page** with pagination
- **Each session group shows**:
  - Session ID (truncated), project name, date
  - Count of matches in this session
- **Each individual match shows**:
  - Role badge (User/Assistant) and timestamp
  - Context snippet with highlighted search term
  - "View in Conversation →" link
- **Result count summary**: "X matches across Y sessions"

### MCP Analysis Section
Separate section accessible via tab or toggle on the search page.

**Overview Display**:
- Total MCP tool uses across all sessions
- Breakdown by MCP server (e.g., playwright: 45 uses, context7: 23 uses)
- List of unique MCP tools with usage counts

**Detailed View**:
- Click MCP server or tool to filter search results
- Show example use cases with conversation context
- Highlight problems being solved

**Example Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ MCP Tool Usage Analysis                                     │
├─────────────────────────────────────────────────────────────┤
│ Total MCP Uses: 127 across 24 sessions                      │
│                                                             │
│ By Server:                                                  │
│ ├─ mcp__playwright__ (68 uses)                             │
│ ├─ mcp__context7__ (45 uses)                               │
│ └─ mcp__github__ (14 uses)                                 │
│                                                             │
│ Top MCP Tools:                                              │
│ 1. mcp__playwright__browser_snapshot (23 uses) [View →]    │
│ 2. mcp__context7__get-library-docs (20 uses) [View →]      │
│ 3. mcp__playwright__browser_click (18 uses) [View →]       │
│    ...                                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Deep Linking to Conversations

**URL Structure**:
```
/View_Conversation?session_id=abc123&message_index=42
```

**Implementation**:
1. Search results link to conversation page with query params
2. Conversation page reads `st.query_params`
3. Loads session and displays messages
4. Adds `message-highlight` class to target message
5. JavaScript injection scrolls to message

**Scroll & Highlight Code**:
```python
# CSS for highlight with fade
st.markdown("""
    <style>
    .message-highlight {
        animation: highlight-fade 3s ease-in-out;
        border-left: 4px solid #ffc107;
        background-color: rgba(255, 193, 7, 0.1);
    }

    @keyframes highlight-fade {
        0% {
            background-color: rgba(255, 193, 7, 0.3);
            border-left-color: #ffc107;
        }
        70% {
            background-color: rgba(255, 193, 7, 0.3);
            border-left-color: #ffc107;
        }
        100% {
            background-color: rgba(255, 193, 7, 0.1);
            border-left-color: #ffc107;
        }
    }
    </style>
""", unsafe_allow_html=True)

# JavaScript to scroll
if target_message_index is not None:
    st.markdown(f"""
        <script>
        setTimeout(() => {{
            const elem = document.getElementById('message-{target_message_index}');
            if (elem) {{
                elem.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}
        }}, 500);
        </script>
    """, unsafe_allow_html=True)
```

**Highlight Behavior**:
- **0-2.1s**: Full highlight (bright yellow background)
- **2.1-3s**: Fade transition
- **After 3s**: Subtle highlight remains (light background + left border)

**Message Rendering**:
```python
# Add ID to all messages for scrolling
# Add highlight class to target message
if idx == target_message_index:
    st.markdown(f'<div id="message-{idx}" class="message-highlight">{content}</div>',
                unsafe_allow_html=True)
else:
    st.markdown(f'<div id="message-{idx}">{content}</div>',
                unsafe_allow_html=True)
```

### Database Queries Needed

**1. Full-Text Search (Messages)**
Uses FTS5 virtual table if available, otherwise LIKE query:

```sql
-- With FTS5
SELECT
    m.session_id,
    m.message_index,
    m.role,
    m.content,
    m.timestamp,
    s.project_id,
    p.project_name,
    snippet(messages_fts, -1, '**', '**', '...', 32) as snippet
FROM messages_fts
JOIN messages m ON messages_fts.rowid = m.rowid
JOIN sessions s ON m.session_id = s.session_id
JOIN projects p ON s.project_id = p.project_id
WHERE messages_fts MATCH ?
    AND (? IS NULL OR s.project_id = ?)
    AND (? IS NULL OR m.timestamp >= ?)
    AND (? IS NULL OR m.timestamp <= ?)
ORDER BY rank
LIMIT 10 OFFSET ?;

-- Without FTS5 (fallback)
SELECT
    m.session_id,
    m.message_index,
    m.role,
    m.content,
    m.timestamp,
    s.project_id,
    p.project_name
FROM messages m
JOIN sessions s ON m.session_id = s.session_id
JOIN projects p ON s.project_id = p.project_id
WHERE m.content LIKE '%' || ? || '%'
    AND (? IS NULL OR s.project_id = ?)
    AND (? IS NULL OR m.timestamp >= ?)
    AND (? IS NULL OR m.timestamp <= ?)
ORDER BY m.timestamp DESC
LIMIT 10 OFFSET ?;
```

**2. Tool Search (Inputs)**
```sql
SELECT
    t.tool_use_id,
    t.session_id,
    t.message_index,
    t.tool_name,
    t.tool_input,
    t.timestamp,
    s.project_id,
    p.project_name
FROM tool_uses t
JOIN sessions s ON t.session_id = s.session_id
JOIN projects p ON s.project_id = p.project_id
WHERE t.tool_input LIKE '%' || ? || '%'
    AND (? IS NULL OR s.project_id = ?)
    AND (? IS NULL OR t.timestamp >= ?)
    AND (? IS NULL OR t.timestamp <= ?)
    AND (? IS NULL OR t.tool_name = ?)
ORDER BY t.timestamp DESC
LIMIT 10 OFFSET ?;
```

**3. Tool Search (Results)**
```sql
SELECT
    t.tool_use_id,
    t.session_id,
    t.message_index,
    t.tool_name,
    t.tool_result,
    t.is_error,
    t.timestamp,
    s.project_id,
    p.project_name
FROM tool_uses t
JOIN sessions s ON t.session_id = s.session_id
JOIN projects p ON s.project_id = p.project_id
WHERE t.tool_result LIKE '%' || ? || '%'
    AND (? IS NULL OR s.project_id = ?)
    AND (? IS NULL OR t.timestamp >= ?)
    AND (? IS NULL OR t.timestamp <= ?)
    AND (? IS NULL OR t.tool_name = ?)
ORDER BY t.timestamp DESC
LIMIT 10 OFFSET ?;
```

**4. Combined Search (All)**
```sql
-- Union of message search and tool search
SELECT * FROM (
    -- Messages
    SELECT
        m.session_id,
        m.message_index,
        'message' as result_type,
        m.role as detail,
        m.content as matched_content,
        m.timestamp,
        s.project_id,
        p.project_name
    FROM messages m
    JOIN sessions s ON m.session_id = s.session_id
    JOIN projects p ON s.project_id = p.project_id
    WHERE m.content LIKE '%' || ? || '%'
        AND (? IS NULL OR s.project_id = ?)
        AND (? IS NULL OR m.timestamp >= ?)
        AND (? IS NULL OR m.timestamp <= ?)

    UNION ALL

    -- Tool inputs
    SELECT
        t.session_id,
        t.message_index,
        'tool_input' as result_type,
        t.tool_name as detail,
        t.tool_input as matched_content,
        t.timestamp,
        s.project_id,
        p.project_name
    FROM tool_uses t
    JOIN sessions s ON t.session_id = s.session_id
    JOIN projects p ON s.project_id = p.project_id
    WHERE t.tool_input LIKE '%' || ? || '%'
        AND (? IS NULL OR s.project_id = ?)
        AND (? IS NULL OR t.timestamp >= ?)
        AND (? IS NULL OR t.timestamp <= ?)
        AND (? IS NULL OR t.tool_name = ?)

    UNION ALL

    -- Tool results
    SELECT
        t.session_id,
        t.message_index,
        'tool_result' as result_type,
        t.tool_name as detail,
        t.tool_result as matched_content,
        t.timestamp,
        s.project_id,
        p.project_name
    FROM tool_uses t
    JOIN sessions s ON t.session_id = s.session_id
    JOIN projects p ON s.project_id = p.project_id
    WHERE t.tool_result LIKE '%' || ? || '%'
        AND (? IS NULL OR s.project_id = ?)
        AND (? IS NULL OR t.timestamp >= ?)
        AND (? IS NULL OR t.timestamp <= ?)
        AND (? IS NULL OR t.tool_name = ?)
)
ORDER BY timestamp DESC
LIMIT 10 OFFSET ?;
```

**5. Get Unique Tool Names**
```sql
SELECT DISTINCT tool_name
FROM tool_uses
ORDER BY tool_name;
```

**6. MCP Tool Analysis**
```sql
-- MCP tool usage summary
SELECT
    tool_name,
    COUNT(*) as use_count,
    COUNT(DISTINCT session_id) as session_count
FROM tool_uses
WHERE tool_name LIKE 'mcp__%'
GROUP BY tool_name
ORDER BY use_count DESC;

-- MCP by server
SELECT
    SUBSTR(tool_name, 1, INSTR(SUBSTR(tool_name, 6), '__') + 4) as mcp_server,
    COUNT(*) as total_uses,
    COUNT(DISTINCT session_id) as sessions
FROM tool_uses
WHERE tool_name LIKE 'mcp__%'
GROUP BY mcp_server
ORDER BY total_uses DESC;
```

### Database Service Methods

Add to `DatabaseService` class:

```python
def search_messages(
    self,
    query: str,
    project_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[SearchResult]:
    """Search message content using FTS5 or LIKE."""
    pass

def search_tool_inputs(
    self,
    query: str,
    project_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[SearchResult]:
    """Search tool input parameters."""
    pass

def search_tool_results(
    self,
    query: str,
    project_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[SearchResult]:
    """Search tool output/results."""
    pass

def search_all(
    self,
    query: str,
    project_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[SearchResult]:
    """Combined search across messages and tools."""
    pass

def get_unique_tool_names(self) -> List[str]:
    """Get list of all tool names used."""
    pass

def get_mcp_tool_stats(self) -> Dict[str, Any]:
    """Get MCP tool usage statistics."""
    pass
```

### Data Models

```python
from pydantic import BaseModel
from typing import Optional, Literal

class SearchResult(BaseModel):
    """Search result item."""
    session_id: str
    message_index: int
    result_type: Literal["message", "tool_input", "tool_result"]
    detail: str  # role for messages, tool_name for tools
    matched_content: str  # full content or snippet
    timestamp: str
    project_id: str
    project_name: str

class MCPToolStat(BaseModel):
    """MCP tool usage statistics."""
    tool_name: str
    use_count: int
    session_count: int

class MCPServerStat(BaseModel):
    """MCP server statistics."""
    server_name: str
    total_uses: int
    session_count: int
```

---

## Implementation Plan

### Phase 1: Core Search Functionality
1. Create `pages/search.py` with basic layout
2. Implement search input and scope selector
3. Add filter controls (project, date range, tool name)
4. Implement `DatabaseService` search methods
5. Display search results grouped by session
6. Add pagination

### Phase 2: Deep Linking
1. Update conversation page to read query params
2. Add message IDs to conversation display
3. Implement highlight CSS and fade animation
4. Add JavaScript scroll injection
5. Test deep linking from search results

### Phase 3: MCP Analysis
1. Create MCP analysis section/tab
2. Implement MCP statistics queries
3. Display MCP server breakdown
4. Show top MCP tools with usage counts
5. Link MCP tools to filtered search results

### Phase 4: Polish & Optimization
1. Add loading states and error handling
2. Optimize FTS5 queries for performance
3. Add result count summaries
4. Implement snippet highlighting
5. Add keyboard shortcuts (Enter to search, etc.)
6. Mobile responsiveness testing

---

## Open Questions / Future Enhancements

### Potential Future Features
- **Search history**: Save recent searches
- **Saved searches**: Bookmark frequently used queries
- **Advanced filters**:
  - Token usage range
  - Message count range
  - Regex search support
- **Export results**: Download search results as CSV/JSON
- **Search term highlighting in snippets**: Highlight actual search terms in the snippet text
- **Context expansion**: Click to expand snippet to show more surrounding messages
- **Search suggestions**: Auto-complete based on common searches
- **Search analytics**: Track most searched terms, popular filters

### Technical Considerations
- **FTS5 index**: Ensure it's created during database setup
- **Performance**: Monitor search performance with large datasets
- **Caching**: Consider caching search results for repeated queries
- **Rate limiting**: If search becomes slow, add debouncing to search input

### UX Considerations
- **Empty states**: What to show when no results found
- **Search tips**: Help users construct effective queries
- **Result preview**: Hover to preview more context?
- **Keyboard navigation**: Tab through results, Enter to open

---

## Success Metrics

- Users can find specific conversations/messages in < 5 seconds
- Search covers 100% of message and tool data
- Deep linking works reliably across all browsers
- MCP analysis provides actionable insights into tool usage patterns
- Page load time remains under 2 seconds even with 10K+ messages
