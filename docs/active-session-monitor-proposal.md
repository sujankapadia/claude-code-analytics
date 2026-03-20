# Active Session Monitor — Proposal

## Problem

When running Claude Code across multiple projects simultaneously in iTerm tabs, it's difficult to:

1. **Identify tabs** — Which tab is which project?
2. **See what's active** — Which sessions are running right now vs recently finished?
3. **Recall context** — What was I working on in each project?
4. **Get a unified view** — See all active/recent sessions at a glance without cycling through tabs

## Goals

- At-a-glance visibility into all active and recently active Claude Code sessions
- Automatic iTerm tab labeling (no manual effort)
- A consolidated dashboard view showing all sessions in one place
- Minimal resource overhead — event-driven where possible, no aggressive polling

## Non-Goals (for now)

- Managing "what's next" or task queues per project
- Controlling sessions remotely (stopping, sending input)
- Notifications or alerts

---

## Data Sources

All data is available without modifying Claude Code itself.

### Process Detection (`ps` + `lsof`)

```bash
# Find running Claude Code processes
ps -eo pid,tty,lstart,pcpu,command | grep '[c]laude'

# Get working directory for each process
lsof -p <pid> | grep cwd
```

Yields: PID, TTY (maps to iTerm tab), start time, CPU % (active vs idle indicator), project directory.

### JSONL Session Files (`~/.claude/projects/`)

Each project directory contains `.jsonl` files with the conversation transcript. The latest messages provide context about what's being worked on. These files are written to during the session, not just at session end.

### Claude Code Hooks

Claude Code supports `SessionStart` and `SessionEnd` hooks that fire shell commands with session metadata (JSON on stdin). These provide event-driven signals for session lifecycle.

### iTerm2 Escape Sequences

iTerm2 supports setting tab titles via ANSI escape sequences:
```bash
# Set tab title
echo -ne "\e]1;My Title\a"

# Set tab badge (overlay text)
printf "\e]1337;SetBadge=%s\a" $(echo -n "badge text" | base64)
```

No iTerm2 Python API or special integration needed — plain escape sequences work from any shell.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     iTerm2 Tabs                         │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ analytics ▶  │ │   lxr ▶      │ │ layer8 ■     │    │
│  │ active       │ │ active       │ │ finished     │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│        ▲                ▲                ▲              │
│        └────────────────┴────────────────┘              │
│              SessionStart / SessionEnd hooks            │
│              set tab title via escape sequences         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              React Frontend — Active Page                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ claude-code-analytics    ▶ active  37m          │    │
│  │ "Build active session monitor feature"          │    │
│  │ ttys007 · started 5:30 PM · CPU 5.9%            │    │
│  ├─────────────────────────────────────────────────┤    │
│  │ lxr                      ▶ active  2h 14m       │    │
│  │ "Fix auth middleware for SSO integration"       │    │
│  │ ttys004 · started 3:16 PM · CPU 0.1%            │    │
│  ├─────────────────────────────────────────────────┤    │
│  │ layer8                   ■ ended   45m ago      │    │
│  │ "Refactor database connection pooling"          │    │
│  │ 23 messages · 1,247 tokens                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│        polls GET /api/sessions/active every 30s         │
│        (only while tab is visible)                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                         │
│  GET /api/sessions/active                               │
│  ├── Scan ps for running 'claude' processes             │
│  ├── lsof to get working directory per process          │
│  ├── Map directory → project name                       │
│  ├── Read latest JSONL messages for context             │
│  ├── Merge with recently ended sessions from DB         │
│  └── Return unified list                                │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: iTerm Tab Titles (Hook-Driven)

**Effort:** Small — two hook scripts, no API changes.

#### 1a. SessionStart Hook

**Confirmed:** Claude Code supports `SessionStart` hooks with matchers for `startup`, `resume`, `clear`, and `compact`.

Create `hooks/set-tab-title.sh`:
- Runs on session start (and resume/compact, so the title is always current)
- Extracts the project directory from the working directory
- Sets the iTerm tab title via escape sequence: `\e]1;<project-name> ▶\a`
- Optionally sets a badge with the short project name
- Stdout from SessionStart hooks is visible to the user and Claude, so use stderr for escape sequences or redirect to `/dev/tty`

```bash
#!/bin/bash
# hooks/set-tab-title.sh — SessionStart hook
PROJECT_NAME=$(basename "$PWD")
# Write escape sequences directly to the terminal, not stdout
# (stdout from SessionStart hooks becomes context for Claude)
echo -ne "\e]1;${PROJECT_NAME} ▶\e\\" > /dev/tty
printf "\e]1337;SetBadge=%s\a" $(echo -n "$PROJECT_NAME" | base64) > /dev/tty
```

Register in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/hooks/set-tab-title.sh"
          }
        ]
      }
    ]
  }
}
```

Using an empty matcher (or omitting it) means it fires on all SessionStart events: `startup`, `resume`, `clear`, and `compact`. This ensures the tab title stays correct even after resuming a session.

#### 1b. SessionEnd Hook Update

Modify `hooks/export-conversation.sh` to also:
- Update the tab title to indicate the session ended: `\e]1;<project-name> ■\a`
- Clear the badge (or update it to show "done")

#### 1c. Register Hooks

The SessionStart hook is registered separately from the existing SessionEnd hook — both coexist in `settings.json` under their respective keys.

#### Limitations

- Only updates on session start/end — doesn't show what you're currently working on mid-session
- If you run `claude` outside a project directory, the title may be generic
- Tab title resets if you exit Claude and start a new shell in the same tab (which is actually desired behavior)

---

### Phase 2: Active Sessions API Endpoint

**Effort:** Medium — new endpoint with process inspection logic.

#### 2a. Process Scanner Service

Create `claude_code_analytics/api/services/process_scanner.py`:

```python
@dataclass
class ActiveSession:
    pid: int
    tty: str
    project_dir: str
    project_name: str
    started_at: datetime
    cpu_percent: float
    status: str  # "active" | "idle"
    last_user_message: str | None
    session_duration: str

async def scan_active_sessions() -> list[ActiveSession]:
    """
    1. Run `ps` to find claude processes
    2. Run `lsof` to get cwd for each
    3. Map cwd to project name (basename or DB lookup)
    4. Read latest JSONL to extract last user message
    5. Return list of ActiveSession
    """
```

Key decisions:
- Run `ps` and `lsof` via `asyncio.create_subprocess_exec` (non-blocking)
- Cache results for 5 seconds to avoid redundant process scans if multiple clients poll simultaneously
- CPU % > 1% = "active", otherwise "idle" (Claude thinking vs waiting for input)
- Read only the last ~20 lines of the JSONL file (tail) to find the most recent user message — don't parse the entire file

#### 2b. API Endpoint

Create route in `claude_code_analytics/api/routers/sessions.py` (or a new `active.py` router):

```
GET /api/sessions/active?include_recent=true&recent_minutes=60
```

Response:
```json
{
  "active": [
    {
      "pid": 3470,
      "tty": "ttys007",
      "project_name": "claude-code-analytics",
      "project_dir": "/Users/skapadia/dev/personal/claude-code-analytics",
      "started_at": "2026-03-12T17:30:33",
      "duration_minutes": 37,
      "cpu_percent": 5.9,
      "status": "active",
      "goal": "Build active session monitor feature",
      "current_focus": "Let's write out the entire plan to a document"
    }
  ],
  "recent": [
    {
      "session_id": "abc-123",
      "project_name": "layer8",
      "ended_at": "2026-03-12T16:45:00",
      "ended_minutes_ago": 45,
      "message_count": 23,
      "first_user_message": "Refactor database connection pooling"
    }
  ]
}
```

The `recent` section comes from the existing database — sessions that ended within the last N minutes. This gives a complete picture of "what have I been doing."

#### 2c. JSONL Context Extraction

To get the "what am I working on" context from an active session:

1. Map the process's working directory to the `~/.claude/projects/` directory name (replace `/` with `-`, prepend `-`)
2. Find the most recently modified `.jsonl` file in that project directory
3. **First user message**: Read from the start of the file — scan the first ~8KB for the first `user` role message longer than 20 characters. This is the session's goal/intent.
4. **Last user message**: Read the last ~4KB of the file (seek to end minus 4KB). Parse the last few JSON lines to find the most recent `user` role message longer than 20 characters (skip acknowledgments like "yes", "ok", "do it"). This is the current focus.
5. Return both, truncated to 200 characters each.

This gives a two-line context summary:
- **Goal**: "Build active session monitor feature" (first substantial user message)
- **Current**: "Let's write out the entire plan" (latest substantial user message)

If both are the same message (short session), show it once. This avoids reading entire multi-MB transcript files.

---

### Phase 3: React Frontend — Active Sessions Page

**Effort:** Medium — new page, follows existing patterns.

#### 3a. New Page: `/active`

Create `frontend/src/pages/active.tsx`:

- **Active Sessions section** — Cards for each running Claude process
  - Project name (prominent)
  - Status indicator: green dot = active (CPU > 1%), yellow = idle
  - Duration (auto-updating via `setInterval`)
  - Last user message as context summary
  - TTY identifier (so you know which tab to switch to)

- **Recently Ended section** — Cards for sessions that ended in the last hour
  - Project name
  - "Ended X minutes ago"
  - First user message
  - Message count and token usage
  - Click to open full session detail

#### 3b. Polling Strategy

- Poll `GET /api/sessions/active` every 30 seconds
- Only poll when the browser tab is visible (`document.visibilityState`)
- Use TanStack Query's `refetchInterval` with `refetchIntervalInBackground: false`
- Instant refetch on window focus (already default TanStack Query behavior)

#### 3c. Navigation

- Add to sidebar: "Active" with a `Radio` or `Activity` icon from Lucide
- Show a count badge on the nav item indicating number of active sessions
- Position it at the top of the nav list (above Dashboard) since it's the "what's happening now" entry point

---

## Future Enhancements (Out of Scope)

These ideas are noted for later consideration:

- **Recent agent activity summary** — Parse the last few tool uses from the JSONL to show what the agent just did (e.g., "edited auth.py", "ran 3 tests — all passed"). No LLM needed for simple cases, but collapsing noisy sequences (10 sequential Grep calls → "searched 8 files") would need heuristic logic. Could be very useful for knowing what's happening when Claude is mid-task and the user is watching.
- **"What's Next" per project** — Manual notes or auto-inferred from the last assistant message
- **iTerm2 tab color coding** — Different colors per project or status
- **macOS menu bar widget** — Show active session count without opening a browser (e.g., via `rumps` or SwiftBar)
- **Mid-session context updates** — Watch the live JSONL file for changes to update the tab title with the current task (requires `watchfiles` on individual JSONL files, higher resource cost)
- **Session grouping by "work stream"** — Tag related sessions across projects as part of the same initiative
- **Push notifications** — Alert when a long-running session completes

---

## Verified Assumptions

1. **JSONL files are written live during active sessions** — Confirmed. Claude Code writes directly to `~/.claude/projects/<project-id>/<session-id>.jsonl` throughout the session, not just at session end. The current session's file (17MB) has a modification time matching the present moment. This means we can read the latest messages from active sessions to extract context.

2. **`lsof` works for own processes** — Confirmed. `lsof -p <pid> | grep cwd` reliably returns the working directory for the user's own Claude Code processes without elevated privileges.

3. **Process detection is reliable** — Confirmed. `ps -eo pid,tty,lstart,pcpu,command | grep claude` finds all running Claude instances with their TTY, start time, and CPU usage.

## Open Questions

1. **Cross-platform** — This proposal assumes macOS + iTerm2. The API endpoint is platform-agnostic, but the tab-title mechanism (iTerm escape sequences) and process scanning (`lsof`) are macOS/Linux-specific. Acceptable for now since this is a personal tool.
