# MCP Server Analytics

This document explains how MCP (Model Context Protocol) server usage is tracked in Claude Code conversation transcripts and provides useful SQL queries for analysis.

## How MCP Tools Are Captured

MCP server tools are stored in the `tool_uses` table alongside built-in Claude Code tools (Bash, Read, Edit, etc.). They follow a specific naming convention that makes them easy to identify and analyze.

### Naming Convention

MCP tools use the format: `mcp__<server-name>__<tool-name>`

**Examples:**
- `mcp__context7__get-library-docs` - Context7 server's library docs tool
- `mcp__jellico__get_consultant_hours` - Jellico server's hours tracking tool
- `mcp__playwright__browser_click` - Playwright server's browser interaction tool

**Format breakdown:**
- Prefix: `mcp__`
- Server name: The MCP server identifier
- Separator: `__`
- Tool name: The specific tool/function name

## Database Schema

MCP tool usage is stored in the `tool_uses` table:

```sql
CREATE TABLE tool_uses (
    tool_use_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,           -- Contains "mcp__<server>__<tool>"
    tool_input TEXT,                   -- JSON input parameters
    tool_result TEXT,                  -- Result/output
    is_error BOOLEAN DEFAULT 0,        -- Whether the call failed
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

## Useful SQL Queries

### 1. List All MCP Servers Used

```sql
SELECT DISTINCT
    SUBSTR(tool_name, 6, INSTR(SUBSTR(tool_name, 6), '__') - 1) as mcp_server,
    COUNT(*) OVER (PARTITION BY SUBSTR(tool_name, 6, INSTR(SUBSTR(tool_name, 6), '__') - 1)) as total_calls
FROM tool_uses
WHERE tool_name LIKE 'mcp__%'
ORDER BY total_calls DESC;
```

### 2. MCP Tool Usage by Server

Count how many times each MCP server was used:

```sql
SELECT
    SUBSTR(tool_name, 6, INSTR(SUBSTR(tool_name, 6), '__') - 1) as mcp_server,
    COUNT(*) as usage_count,
    SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as error_count,
    ROUND(100.0 * SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_pct
FROM tool_uses
WHERE tool_name LIKE 'mcp__%'
GROUP BY mcp_server
ORDER BY usage_count DESC;
```

### 3. Most Used MCP Tools

Find the most frequently called MCP tools across all servers:

```sql
SELECT
    tool_name,
    SUBSTR(tool_name, 6, INSTR(SUBSTR(tool_name, 6), '__') - 1) as mcp_server,
    SUBSTR(tool_name, INSTR(tool_name, '__', 6) + 2) as tool_function,
    COUNT(*) as call_count
FROM tool_uses
WHERE tool_name LIKE 'mcp__%'
GROUP BY tool_name
ORDER BY call_count DESC
LIMIT 20;
```

### 4. Sessions Using a Specific MCP Server

Find all sessions that used a particular MCP server (e.g., "jellico"):

```sql
SELECT DISTINCT
    s.session_id,
    p.project_name,
    s.start_time,
    s.end_time,
    COUNT(t.tool_use_id) as tool_calls
FROM tool_uses t
JOIN sessions s ON t.session_id = s.session_id
JOIN projects p ON s.project_id = p.project_id
WHERE t.tool_name LIKE 'mcp__jellico__%'
GROUP BY s.session_id, p.project_name, s.start_time, s.end_time
ORDER BY s.start_time DESC;
```

### 5. MCP Tool Error Analysis

Identify which MCP tools have the highest error rates:

```sql
SELECT
    tool_name,
    COUNT(*) as total_calls,
    SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as errors,
    ROUND(100.0 * SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_pct
FROM tool_uses
WHERE tool_name LIKE 'mcp__%'
GROUP BY tool_name
HAVING COUNT(*) >= 5  -- Only tools called 5+ times
ORDER BY error_rate_pct DESC, total_calls DESC;
```

### 6. MCP vs Built-in Tool Usage Comparison

Compare usage of MCP tools vs built-in Claude Code tools:

```sql
SELECT
    CASE
        WHEN tool_name LIKE 'mcp__%' THEN 'MCP Tools'
        ELSE 'Built-in Tools'
    END as tool_type,
    COUNT(*) as total_calls,
    COUNT(DISTINCT tool_name) as unique_tools,
    SUM(CASE WHEN is_error = 1 THEN 1 ELSE 0 END) as total_errors
FROM tool_uses
GROUP BY tool_type;
```

### 7. MCP Server Usage Timeline

See when different MCP servers were used over time:

```sql
SELECT
    DATE(t.timestamp) as date,
    SUBSTR(t.tool_name, 6, INSTR(SUBSTR(t.tool_name, 6), '__') - 1) as mcp_server,
    COUNT(*) as calls_per_day
FROM tool_uses t
WHERE t.tool_name LIKE 'mcp__%'
GROUP BY date, mcp_server
ORDER BY date DESC, calls_per_day DESC;
```

### 8. Projects Using MCP Servers

Which projects use MCP servers and which specific servers:

```sql
SELECT
    p.project_name,
    SUBSTR(t.tool_name, 6, INSTR(SUBSTR(t.tool_name, 6), '__') - 1) as mcp_server,
    COUNT(*) as usage_count,
    MIN(t.timestamp) as first_used,
    MAX(t.timestamp) as last_used
FROM tool_uses t
JOIN sessions s ON t.session_id = s.session_id
JOIN projects p ON s.project_id = p.project_id
WHERE t.tool_name LIKE 'mcp__%'
GROUP BY p.project_name, mcp_server
ORDER BY p.project_name, usage_count DESC;
```

### 9. MCP Tool Input/Output Analysis

Examine what data is being passed to MCP tools (useful for debugging):

```sql
SELECT
    tool_name,
    SUBSTR(tool_input, 1, 100) as input_preview,
    SUBSTR(tool_result, 1, 100) as result_preview,
    is_error,
    timestamp
FROM tool_uses
WHERE tool_name LIKE 'mcp__jellico__%'  -- Replace with your MCP server
ORDER BY timestamp DESC
LIMIT 20;
```

### 10. MCP Tool Call Sequences

Find common sequences of MCP tool calls (what tools are used together):

```sql
SELECT
    t1.tool_name as first_tool,
    t2.tool_name as second_tool,
    COUNT(*) as sequence_count
FROM tool_uses t1
JOIN tool_uses t2 ON t1.session_id = t2.session_id
    AND t2.timestamp > t1.timestamp
    AND (julianday(t2.timestamp) - julianday(t1.timestamp)) * 86400 < 60  -- Within 60 seconds
WHERE t1.tool_name LIKE 'mcp__%' OR t2.tool_name LIKE 'mcp__%'
GROUP BY t1.tool_name, t2.tool_name
HAVING sequence_count >= 3
ORDER BY sequence_count DESC
LIMIT 20;
```

## Full-Text Search for MCP Usage

You can also use the FTS search to find conversations mentioning specific MCP servers:

```bash
# Find all messages where Jellico MCP server was discussed
python3 scripts/search_fts.py "jellico" --context=2

# Find tool uses from a specific MCP server
python3 scripts/search_fts.py "mcp__jellico" --context=3
```

## Analysis Script Integration

When running analysis scripts, MCP tool usage is automatically included in the transcript and can be analyzed:

```bash
# Decision analysis will show MCP-related decisions
python3 scripts/analyze_session.py <session-id> --type=decisions

# Error analysis will show MCP tool failures
python3 scripts/analyze_session.py <session-id> --type=errors
```

## Key Insights

From the data captured, you can determine:

1. ✅ **Which MCP servers are installed and used** in your Claude Code setup
2. ✅ **How frequently each MCP server/tool is called**
3. ✅ **Error rates for MCP tools** (reliability metrics)
4. ✅ **Which projects rely on which MCP servers**
5. ✅ **Temporal patterns** (when MCP servers are used)
6. ✅ **Tool input/output** (what data flows through MCP tools)
7. ✅ **Usage patterns** (which tools are used together)

## Example Use Cases

### Use Case 1: MCP Server Performance Audit
Run queries 2 and 5 to identify:
- Which MCP servers are most/least used
- Which have the highest error rates
- Whether to deprecate underutilized servers

### Use Case 2: Project MCP Dependencies
Run query 8 to understand:
- Which projects depend on which MCP servers
- Impact analysis before removing/updating an MCP server

### Use Case 3: MCP Tool Effectiveness
Compare MCP tool usage before/after deployment:
- Did the new MCP server get adopted?
- Are users discovering all available tools?
- Are there tools that never get used?

## Notes

- MCP tool calls are stored exactly like built-in tools
- Full input/output is captured (useful for debugging)
- Error status is tracked (useful for reliability analysis)
- Timestamps enable temporal analysis
- The naming convention makes MCP tools easy to filter and analyze
