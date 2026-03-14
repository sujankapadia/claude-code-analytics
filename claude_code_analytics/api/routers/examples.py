"""Find Examples endpoint — hybrid FTS + LLM search for workflow discovery."""

import asyncio
import contextlib
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from claude_code_analytics.api.dependencies import get_analysis_service, get_db_service
from claude_code_analytics.services.analysis_service import AnalysisService
from claude_code_analytics.services.database_service import DatabaseService

router = APIRouter(prefix="/examples", tags=["examples"])

# Common tool name keywords mapped to actual tool name patterns
# Prefix of auto-generated compaction messages — not useful as shareable examples
COMPACTION_PREFIX = "This session is being continued from a previous conversation"

TOOL_KEYWORDS = {
    "playwright": "mcp__playwright__",
    "browser": "mcp__playwright__",
    "bash": "Bash",
    "edit": "Edit",
    "write": "Write",
    "read": "Read",
    "grep": "Grep",
    "glob": "Glob",
    "git": "Bash",  # git commands go through Bash
    "commit": "Bash",
    "test": "Bash",
    "notebook": "NotebookEdit",
}


class FindExamplesRequest(BaseModel):
    """Request body for finding example sessions."""

    query: str
    project_id: Optional[str] = None
    max_results: int = 5
    scope: str = "All"  # "All", "Messages", "Tool Inputs", "Tool Results"
    role: Optional[str] = None  # "user", "assistant" — filters message results only


class FindPromptsRequest(BaseModel):
    """Request body for finding example prompts."""

    query: str
    project_id: Optional[str] = None
    max_results: int = 5


class PromptMatch(BaseModel):
    """A single user prompt that matches the query."""

    session_id: str
    message_index: int
    project_name: str
    content: str  # full message text
    timestamp: Optional[str] = None
    relevance: str  # LLM-generated explanation


class FindPromptsResponse(BaseModel):
    """Response from find-prompts endpoint."""

    query: str
    prompts: list[PromptMatch]
    candidate_count: int
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model_name: Optional[str] = None


class MatchingExcerpt(BaseModel):
    """A specific message that matched the search within a session."""

    message_index: int
    role: str
    content: str  # truncated to ~300 chars
    timestamp: Optional[str] = None


class SessionMatch(BaseModel):
    """A matched session with explanation."""

    session_id: str
    project_name: str
    first_user_message: Optional[str]
    message_count: int
    tool_use_count: int
    relevance: str  # LLM-generated explanation of why this matches
    suggested_excerpt_range: Optional[str] = None  # e.g. "messages 12-25"
    matching_excerpts: list[MatchingExcerpt] = []  # actual FTS hits in this session


class FindExamplesResponse(BaseModel):
    """Response from find-examples endpoint."""

    query: str
    matches: list[SessionMatch]
    candidate_count: int  # how many sessions were considered
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model_name: Optional[str] = None


def _extract_search_terms(query: str) -> list[str]:
    """Extract meaningful search terms from a natural language query.

    Strips common filler words to produce better FTS queries.
    """
    stop_words = {
        "a",
        "an",
        "the",
        "how",
        "do",
        "i",
        "you",
        "we",
        "my",
        "me",
        "to",
        "in",
        "on",
        "at",
        "for",
        "of",
        "with",
        "and",
        "or",
        "is",
        "it",
        "that",
        "this",
        "what",
        "when",
        "where",
        "which",
        "can",
        "does",
        "did",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "show",
        "give",
        "example",
        "examples",
        "prompt",
        "prompts",
        "use",
        "used",
        "using",
        "like",
        "way",
        "get",
        "something",
        "about",
        "from",
        "into",
        "some",
    }
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_.-]*", query.lower())
    return [w for w in words if w not in stop_words and len(w) > 1]


def _detect_tool_patterns(terms: list[str]) -> list[str]:
    """Detect tool name patterns from search terms."""
    patterns = set()
    for term in terms:
        if term in TOOL_KEYWORDS:
            patterns.add(TOOL_KEYWORDS[term])
    return list(patterns)


def _build_candidate_summaries(
    db: DatabaseService,
    session_ids: list[str],
) -> list[dict]:
    """Build compact summaries for candidate sessions."""
    summaries = []
    all_sessions = db.get_session_summaries()
    session_map = {s.session_id: s for s in all_sessions}

    for sid in session_ids:
        session = session_map.get(sid)
        if not session:
            continue

        # Get tool breakdown for this session
        tool_uses = db.get_tool_uses_for_session(sid)
        tool_counts: dict[str, int] = {}
        for t in tool_uses:
            tool_counts[t.tool_name] = tool_counts.get(t.tool_name, 0) + 1

        # Get first few user messages for context
        messages = db.get_messages_for_session(sid)
        user_messages = [
            m.content[:200]
            for m in messages
            if m.role == "user"
            and m.content
            and m.content.strip()
            and not m.content.startswith(COMPACTION_PREFIX)
        ][:5]

        summaries.append(
            {
                "session_id": sid,
                "project_name": session.project_name,
                "first_user_message": session.first_user_message,
                "message_count": session.message_count,
                "tool_use_count": session.tool_use_count,
                "duration_seconds": session.duration_seconds,
                "tools_used": dict(sorted(tool_counts.items(), key=lambda x: -x[1])[:10]),
                "user_messages_preview": user_messages,
            }
        )

    return summaries


RANKING_PROMPT = """\
You are helping a developer find relevant examples from their Claude Code conversation history.

The developer is looking for: "{query}"

Below are summaries of {count} candidate sessions. For each session you see:
- session_id, project name
- First user message (the opening prompt)
- Tool breakdown (which tools were used and how many times)
- First few user messages for additional context
- search_hits: specific messages that matched the search keywords (with message index and role)

CANDIDATES:
{candidates}

INSTRUCTIONS:
Select the {max_results} most relevant sessions that best match what the developer is looking for.

For each match, explain in 1-2 sentences WHY it's relevant — what specific workflow, technique, or prompt pattern it demonstrates.

If a session contains a particularly relevant section, suggest an approximate message range to look at (e.g. "messages 5-20 cover the Playwright testing setup").

Respond with ONLY valid JSON in this format (no markdown fencing):
{{
  "matches": [
    {{
      "session_id": "...",
      "relevance": "This session demonstrates ... because ...",
      "suggested_excerpt_range": "messages 12-25"
    }}
  ]
}}

If fewer than {max_results} sessions are genuinely relevant, return fewer. Do not pad with irrelevant results.\
"""


@router.post("/sessions", response_model=FindExamplesResponse)
async def find_example_sessions(
    req: FindExamplesRequest,
    db: DatabaseService = Depends(get_db_service),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """Find example sessions matching a natural language query.

    Uses FTS + tool filtering to find candidates, then LLM to rank them.
    """
    terms = _extract_search_terms(req.query)
    if not terms:
        raise HTTPException(
            status_code=400, detail="Query too vague — try including specific keywords"
        )

    tool_patterns = _detect_tool_patterns(terms)

    # Step 1: Gather candidate session IDs from multiple signals
    candidate_ids: set[str] = set()
    fts_results: list[dict] = []

    # 1a. FTS search — use scoped/role-filtered search when requested
    fts_query = " ".join(terms)
    try:
        if req.role or req.scope == "Messages":
            # Use message-specific search with optional role filter
            fts_results_raw = db.search_messages(
                query=fts_query,
                project_id=req.project_id,
                role=req.role,
                limit=200,
            )
            # Normalize to match search_all format
            fts_results = [
                {
                    "session_id": r["session_id"],
                    "message_index": r["message_index"],
                    "result_type": "message",
                    "detail": r.get("role", "unknown"),
                    "matched_content": r.get("content", ""),
                    "snippet": r.get("snippet", ""),
                    "timestamp": r.get("timestamp"),
                }
                for r in fts_results_raw
            ]
        elif req.scope == "Tool Inputs":
            fts_results = db.search_tool_inputs(
                query=fts_query,
                project_id=req.project_id,
                limit=200,
            )
        elif req.scope == "Tool Results":
            fts_results = db.search_tool_results(
                query=fts_query,
                project_id=req.project_id,
                limit=200,
            )
        else:
            fts_results = db.search_all(
                query=fts_query,
                project_id=req.project_id,
                limit=200,
            )
        for r in fts_results:
            candidate_ids.add(r["session_id"])
    except Exception:
        pass  # FTS may fail on unusual queries; continue with other signals

    # 1b. Find sessions that used matching tools (direct SQL for performance)
    if tool_patterns:
        import sqlite3

        from claude_code_analytics import config

        conn = sqlite3.connect(str(config.DATABASE_PATH))
        try:
            for pattern in tool_patterns:
                like = f"%{pattern}%"
                if req.project_id:
                    rows = conn.execute(
                        "SELECT DISTINCT tu.session_id FROM tool_uses tu "
                        "JOIN sessions s ON tu.session_id = s.session_id "
                        "WHERE tu.tool_name LIKE ? AND s.project_id = ?",
                        (like, req.project_id),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT DISTINCT session_id FROM tool_uses WHERE tool_name LIKE ?",
                        (like,),
                    ).fetchall()
                for (sid,) in rows:
                    candidate_ids.add(sid)
        finally:
            conn.close()

    if not candidate_ids:
        return FindExamplesResponse(
            query=req.query,
            matches=[],
            candidate_count=0,
        )

    # Step 2: Build per-session FTS hit index
    hit_counts: dict[str, int] = {}
    fts_hits_by_session: dict[str, list[dict]] = {}
    for r in fts_results:
        sid = r["session_id"]
        hit_counts[sid] = hit_counts.get(sid, 0) + 1
        if sid not in fts_hits_by_session:
            fts_hits_by_session[sid] = []
        # Keep user messages preferentially, cap at 5 per session
        if len(fts_hits_by_session[sid]) < 5:
            fts_hits_by_session[sid].append(r)

    # Cap candidates and build summaries, prioritizing sessions with more FTS hits
    max_candidates = 20
    sorted_candidates = sorted(
        candidate_ids,
        key=lambda sid: hit_counts.get(sid, 0),
        reverse=True,
    )[:max_candidates]

    loop = asyncio.get_event_loop()
    summaries = await loop.run_in_executor(
        None,
        lambda: _build_candidate_summaries(db, sorted_candidates),
    )

    if not summaries:
        return FindExamplesResponse(
            query=req.query,
            matches=[],
            candidate_count=len(candidate_ids),
        )

    # Step 3: Format candidates for LLM
    candidates_text = ""
    for i, s in enumerate(summaries, 1):
        tools_str = ", ".join(f"{name} x{count}" for name, count in s["tools_used"].items())
        user_msgs = "\n    ".join(
            f"- {msg[:150]}{'...' if len(msg) > 150 else ''}" for msg in s["user_messages_preview"]
        )

        # Include FTS hit snippets for this session
        hits = fts_hits_by_session.get(s["session_id"], [])
        hits_text = ""
        if hits:
            hit_lines = []
            for h in hits:
                role = h.get("detail", "unknown")
                snippet = (h.get("snippet") or h.get("matched_content", ""))[:200]
                msg_idx = h.get("message_index", "?")
                result_type = h.get("result_type", "message")
                label = role if result_type == "message" else f"tool:{role}"
                hit_lines.append(f"- [msg {msg_idx}, {label}] {snippet}")
            hits_text = "\nsearch_hits:\n    " + "\n    ".join(hit_lines)

        candidates_text += f"""
--- Session {i} ---
session_id: {s["session_id"]}
project: {s["project_name"].split("/")[-1]}
first_message: {(s["first_user_message"] or "(none)")[:200]}
messages: {s["message_count"]}, tools: {s["tool_use_count"]}, duration: {s["duration_seconds"] or 0}s
tools_used: {tools_str}
user_messages:
    {user_msgs}{hits_text}
"""

    prompt = RANKING_PROMPT.format(
        query=req.query,
        count=len(summaries),
        candidates=candidates_text,
        max_results=req.max_results,
    )

    # Step 4: Call LLM to rank
    try:
        llm_response = await loop.run_in_executor(
            None,
            lambda: analysis.provider.generate(prompt),
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error: {e}",
        ) from e

    # Step 5: Parse LLM response
    try:
        # Strip markdown fencing if present
        text = llm_response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM ranking response: {e}",
        ) from e

    # Build response with full session info and FTS excerpts
    summary_map = {s["session_id"]: s for s in summaries}
    matches = []
    for m in parsed.get("matches", []):
        sid = m.get("session_id", "")
        info = summary_map.get(sid)
        if not info:
            continue

        # Build matching excerpts from FTS hits
        excerpts = []
        for hit in fts_hits_by_session.get(sid, []):
            content = hit.get("snippet") or hit.get("matched_content", "")
            role = hit.get("detail", "unknown")  # 'detail' holds role for messages
            if hit.get("result_type") != "message":
                role = f"tool:{role}"
            excerpts.append(
                MatchingExcerpt(
                    message_index=hit.get("message_index", 0),
                    role=role,
                    content=content[:300],
                    timestamp=hit.get("timestamp"),
                )
            )

        matches.append(
            SessionMatch(
                session_id=sid,
                project_name=info["project_name"],
                first_user_message=info["first_user_message"],
                message_count=info["message_count"],
                tool_use_count=info["tool_use_count"],
                relevance=m.get("relevance", ""),
                suggested_excerpt_range=m.get("suggested_excerpt_range"),
                matching_excerpts=excerpts,
            )
        )

    return FindExamplesResponse(
        query=req.query,
        matches=matches,
        candidate_count=len(candidate_ids),
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        model_name=llm_response.model_name,
    )


# ---------------------------------------------------------------------------
# Prompts endpoint — find specific user prompts that demonstrate a technique
# ---------------------------------------------------------------------------

PROMPT_RANKING_PROMPT = """\
You are helping a developer find example prompts from their Claude Code conversation history.

They want to share with a coworker how they prompted Claude Code to do something specific.

The developer is looking for: "{query}"

Below are {count} user messages (prompts) that matched a keyword search. For each you see:
- An ID (prompt_N), the session and project it came from
- The full text of the user's message

CANDIDATE PROMPTS:
{candidates}

INSTRUCTIONS:
Select the {max_results} prompts that best demonstrate the technique or workflow the developer is looking for. Prefer prompts that:
1. Are self-contained and understandable without prior context
2. Clearly show HOW the developer asked Claude to do the thing
3. Would be useful as a template for someone else to adapt

For each selected prompt, explain in 1 sentence what makes it a good example.

Respond with ONLY valid JSON in this format (no markdown fencing):
{{
  "prompts": [
    {{
      "id": "prompt_1",
      "relevance": "Shows how to ask Claude to ..."
    }}
  ]
}}

If fewer than {max_results} prompts are genuinely useful examples, return fewer. Do not pad with irrelevant results.\
"""


@router.post("/prompts", response_model=FindPromptsResponse)
async def find_example_prompts(
    req: FindPromptsRequest,
    db: DatabaseService = Depends(get_db_service),
    analysis: AnalysisService = Depends(get_analysis_service),
):
    """Find specific user prompts that demonstrate a technique or workflow.

    Searches user messages via FTS, fetches full content, then uses LLM to
    rank which prompts are the best shareable examples.
    """
    terms = _extract_search_terms(req.query)
    if not terms:
        raise HTTPException(
            status_code=400, detail="Query too vague — try including specific keywords"
        )

    tool_patterns = _detect_tool_patterns(terms)

    # Step 1: FTS search for user messages only
    fts_query = " ".join(terms)
    fts_hits: list[dict] = []
    with contextlib.suppress(Exception):
        fts_hits = db.search_messages(
            query=fts_query,
            project_id=req.project_id,
            role="user",
            limit=100,
        )

    # Filter out compaction/continuation messages
    fts_hits = [
        h
        for h in fts_hits
        if not (h.get("content") or h.get("snippet") or "").startswith(COMPACTION_PREFIX)
    ]

    # Step 2: If tool patterns detected, also find sessions with those tools
    # and grab their user messages that mention any of the search terms
    if tool_patterns and len(fts_hits) < 20:
        import sqlite3

        from claude_code_analytics import config

        conn = sqlite3.connect(str(config.DATABASE_PATH))
        try:
            existing_keys = {(h["session_id"], h["message_index"]) for h in fts_hits}
            for pattern in tool_patterns:
                like = f"%{pattern}%"
                # Find sessions using this tool, then get their user messages
                sql = """
                    SELECT DISTINCT m.session_id, m.message_index, m.role,
                           m.content, m.timestamp, p.project_name
                    FROM messages m
                    JOIN sessions s ON m.session_id = s.session_id
                    JOIN projects p ON s.project_id = p.project_id
                    WHERE m.role = 'user'
                      AND m.content IS NOT NULL AND m.content != ''
                      AND m.content NOT LIKE 'This session is being continued%'
                      AND m.session_id IN (
                          SELECT DISTINCT session_id FROM tool_uses
                          WHERE tool_name LIKE ?
                      )
                """
                params: list = [like]
                if req.project_id:
                    sql += " AND s.project_id = ?"
                    params.append(req.project_id)
                sql += " ORDER BY m.timestamp DESC LIMIT 50"
                rows = conn.execute(sql, params).fetchall()
                for row in rows:
                    sid, midx, role, content, ts, pname = row
                    if (sid, midx) not in existing_keys and content and content.strip():
                        fts_hits.append(
                            {
                                "session_id": sid,
                                "message_index": midx,
                                "role": role,
                                "content": content,
                                "snippet": content[:200],
                                "timestamp": ts,
                                "project_name": pname,
                            }
                        )
                        existing_keys.add((sid, midx))
        finally:
            conn.close()

    if not fts_hits:
        return FindPromptsResponse(
            query=req.query,
            prompts=[],
            candidate_count=0,
        )

    # Step 3: Fetch full message content and project names for FTS hits
    all_sessions = db.get_session_summaries()
    session_map = {s.session_id: s for s in all_sessions}

    candidates = []
    for hit in fts_hits:
        sid = hit["session_id"]
        msg_idx = hit["message_index"]
        session = session_map.get(sid)
        project_name = hit.get("project_name") or (session.project_name if session else "unknown")

        # Get full message content (FTS snippet is truncated)
        full_content = hit.get("content", "")
        if not full_content or len(full_content) < 50:
            messages = db.get_messages_for_session(sid)
            for m in messages:
                if m.message_index == msg_idx:
                    full_content = m.content or ""
                    break

        if not full_content.strip():
            continue

        # Skip compaction/continuation messages
        if full_content.startswith(COMPACTION_PREFIX):
            continue

        candidates.append(
            {
                "session_id": sid,
                "message_index": msg_idx,
                "project_name": project_name,
                "content": full_content,
                "timestamp": hit.get("timestamp"),
            }
        )

    # Cap at 30 candidates for LLM context
    candidates = candidates[:30]

    # Step 4: Format candidates for LLM — include full prompt text
    candidates_text = ""
    for i, c in enumerate(candidates, 1):
        # Truncate very long messages for LLM context, but keep enough to judge
        content_for_llm = c["content"][:1000]
        if len(c["content"]) > 1000:
            content_for_llm += f"\n... [{len(c['content']) - 1000} more chars]"

        candidates_text += f"""
--- prompt_{i} ---
session: {c["session_id"][:12]}  project: {c["project_name"].split("/")[-1]}
message_index: {c["message_index"]}

{content_for_llm}
"""

    prompt = PROMPT_RANKING_PROMPT.format(
        query=req.query,
        count=len(candidates),
        candidates=candidates_text,
        max_results=req.max_results,
    )

    # Step 5: Call LLM to rank
    loop = asyncio.get_event_loop()
    try:
        llm_response = await loop.run_in_executor(
            None,
            lambda: analysis.provider.generate(prompt),
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error: {e}",
        ) from e

    # Step 6: Parse LLM response
    try:
        text = llm_response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse LLM ranking response: {e}",
        ) from e

    # Step 7: Build response with full prompt content
    candidate_by_id = {f"prompt_{i + 1}": c for i, c in enumerate(candidates)}
    prompts = []
    for p in parsed.get("prompts", []):
        pid = p.get("id", "")
        c = candidate_by_id.get(pid)
        if not c:
            continue
        prompts.append(
            PromptMatch(
                session_id=c["session_id"],
                message_index=c["message_index"],
                project_name=c["project_name"],
                content=c["content"],
                timestamp=c["timestamp"],
                relevance=p.get("relevance", ""),
            )
        )

    return FindPromptsResponse(
        query=req.query,
        prompts=prompts,
        candidate_count=len(fts_hits),
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        model_name=llm_response.model_name,
    )
