"""Service for detecting active Claude Code sessions via process inspection.

Uses psutil for cross-platform process detection (works on macOS, Linux, Windows).
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import psutil

from claude_code_analytics import config

# Minimum character length for a user message to be considered "substantial"
MIN_MESSAGE_LENGTH = 20

# How many bytes to read from end of JSONL for current_focus extraction
TAIL_BYTES = 262144  # 256KB — JSONL entries can be very large (tool results)

# Cache TTL in seconds — avoid redundant process scans from concurrent requests
_CACHE_TTL = 5.0
_cache: dict = {"result": None, "timestamp": 0.0}


@dataclass
class ActiveSession:
    """Represents a currently running Claude Code session."""

    pid: int
    tty: str
    project_dir: str
    project_name: str
    started_at: str
    status: str = "running"
    recent_messages: list[str] = field(default_factory=list)
    duration_minutes: int = 0


@dataclass
class RecentSession:
    """Represents a recently ended session from the database."""

    session_id: str
    project_name: str
    ended_at: str
    ended_minutes_ago: int
    message_count: int
    first_user_message: str | None = None


@dataclass
class ActiveSessionsResponse:
    """Combined active + recent sessions."""

    active: list[ActiveSession] = field(default_factory=list)
    recent: list[RecentSession] = field(default_factory=list)


def _get_claude_processes() -> list[dict]:
    """Find running Claude Code processes using psutil (cross-platform)."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd", "create_time", "terminal"]):
        try:
            info = proc.info
            name = info.get("name", "")
            cmdline = info.get("cmdline") or []

            # Match the main claude process
            # The process name is "claude" or the first cmdline arg ends with "claude"
            is_claude = name == "claude" or (cmdline and Path(cmdline[0]).name == "claude")
            if not is_claude:
                continue

            # Skip subprocesses (--child, --mcp, etc.)
            cmdline_str = " ".join(cmdline)
            if "--child" in cmdline_str or "--mcp" in cmdline_str:
                continue

            cwd = info.get("cwd")
            if not cwd:
                continue

            create_time = datetime.fromtimestamp(info["create_time"])
            terminal = info.get("terminal") or "??"
            # psutil returns full path like /dev/ttys007, extract just ttys007
            if "/" in terminal:
                terminal = terminal.split("/")[-1]

            processes.append(
                {
                    "pid": info["pid"],
                    "tty": terminal,
                    "cwd": cwd,
                    "started_at": create_time,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return processes


def _dir_to_projects_path(project_dir: str) -> str:
    """Convert a project directory to the ~/.claude/projects/ directory name.

    e.g., /Users/skapadia/dev/personal/claude-code-analytics
       -> -Users-skapadia-dev-personal-claude-code-analytics
    """
    return project_dir.replace("/", "-")


def _extract_user_content(entry: dict) -> str | None:
    """Extract clean text content from a user message JSONL entry.

    Returns None if the entry is not a user message or has no usable content.
    Filters out system-generated messages (command output, XML tags, etc.).
    """
    if entry.get("type") not in ("human", "user"):
        return None
    message = entry.get("message")
    if not isinstance(message, dict):
        return None

    content = message.get("content", "")
    # Handle multimodal content (list of content blocks)
    if isinstance(content, list):
        text_parts = [
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
        ]
        # If no text blocks found (e.g., all tool_result), not a real user message
        if not any(t.strip() for t in text_parts):
            return None
        content = " ".join(text_parts)

    if not isinstance(content, str):
        return None

    content = content.strip()

    # Filter out system-generated messages
    if content.startswith(("<local-command", "<command-name>", "<system-reminder>")):
        return None
    if content.startswith("This session is being continued from a previous conversation"):
        return None

    return content if content else None


def _extract_recent_messages(jsonl_path: Path, count: int = 3) -> list[str]:
    """Extract the last N substantial user messages from a JSONL file.

    Reads from the tail of the file to avoid loading large transcripts.
    Returns messages in chronological order (oldest first).
    """
    if not jsonl_path.exists():
        return []

    file_size = jsonl_path.stat().st_size
    if file_size == 0:
        return []

    messages: list[str] = []
    try:
        with open(jsonl_path, "rb") as f:
            seek_pos = max(0, file_size - TAIL_BYTES)
            f.seek(seek_pos)
            tail = f.read().decode("utf-8", errors="replace")

            for line in reversed(tail.split("\n")):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = _extract_user_content(entry)
                if content and len(content) >= MIN_MESSAGE_LENGTH:
                    messages.append(content[:200])
                    if len(messages) >= count:
                        break
    except OSError:
        pass

    # Reverse to chronological order (oldest first)
    messages.reverse()
    return messages


def _find_latest_jsonl(project_dir: str) -> Path | None:
    """Find the most recently modified JSONL file for a project."""
    projects_path = config.CLAUDE_CODE_PROJECTS_DIR / _dir_to_projects_path(project_dir)
    if not projects_path.exists():
        return None

    jsonl_files = list(projects_path.glob("*.jsonl"))
    if not jsonl_files:
        return None

    return max(jsonl_files, key=lambda p: p.stat().st_mtime)


def scan_active_sessions() -> list[ActiveSession]:
    """Detect all currently running Claude Code sessions."""
    processes = _get_claude_processes()

    sessions = []
    now = datetime.now()

    for proc in processes:
        cwd = proc["cwd"]
        project_name = Path(cwd).name
        started_at = proc["started_at"]
        duration = now - started_at
        # Extract recent user messages from JSONL
        jsonl_path = _find_latest_jsonl(cwd)
        recent_messages = _extract_recent_messages(jsonl_path) if jsonl_path else []

        sessions.append(
            ActiveSession(
                pid=proc["pid"],
                tty=proc["tty"],
                project_dir=cwd,
                project_name=project_name,
                started_at=started_at.isoformat(),
                recent_messages=recent_messages,
                duration_minutes=int(duration.total_seconds() / 60),
            )
        )

    return sessions


def get_active_sessions_cached() -> list[ActiveSession]:
    """Return active sessions with a short TTL cache."""
    now = time.time()
    if _cache["result"] is not None and (now - _cache["timestamp"]) < _CACHE_TTL:
        return _cache["result"]

    result = scan_active_sessions()
    _cache["result"] = result
    _cache["timestamp"] = now
    return result
