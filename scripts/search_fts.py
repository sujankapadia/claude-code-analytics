#!/usr/bin/env python3
"""
Search Claude Code conversations using Full-Text Search (FTS5).

Usage:
    search_fts.py "your search query" [options]

Examples:
    search_fts.py "async AND error"
    search_fts.py '"promise rejection"' --project=monolog
    search_fts.py "database performance" --messages --tools
    search_fts.py "typescript NOT react" --role=user --limit=5
"""

import argparse
import sqlite3
from pathlib import Path
import sys
from typing import List, Dict, Optional
from datetime import datetime


def get_message_context(
    db_path: str,
    session_id: str,
    message_index: int,
    context_size: int = 2
) -> Dict:
    """
    Fetch surrounding context for a message.

    Args:
        db_path: Path to SQLite database
        session_id: Session ID
        message_index: Index of the matched message
        context_size: Number of messages before/after to fetch

    Returns:
        Dict with previous, current, and next messages
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = """
    SELECT message_index, role, content, timestamp
    FROM messages
    WHERE session_id = ?
      AND message_index BETWEEN ? AND ?
    ORDER BY message_index
    """

    start_idx = max(0, message_index - context_size)
    end_idx = message_index + context_size

    cursor = conn.cursor()
    cursor.execute(query, (session_id, start_idx, end_idx))

    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()

    result = {
        "previous": [],
        "current": None,
        "next": []
    }

    for msg in messages:
        if msg['message_index'] < message_index:
            result['previous'].append(msg)
        elif msg['message_index'] == message_index:
            result['current'] = msg
        else:
            result['next'].append(msg)

    return result


def get_tool_context(
    db_path: str,
    session_id: str,
    tool_timestamp: str,
    context_size: int = 2
) -> Dict:
    """
    Fetch surrounding messages for a tool use based on timestamp.

    Args:
        db_path: Path to SQLite database
        session_id: Session ID
        tool_timestamp: Timestamp of the tool use
        context_size: Number of messages before/after to fetch

    Returns:
        Dict with previous and next messages
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get messages before the tool use
    query_before = """
    SELECT message_index, role, content, timestamp
    FROM messages
    WHERE session_id = ?
      AND timestamp < ?
    ORDER BY message_index DESC
    LIMIT ?
    """

    # Get messages after the tool use
    query_after = """
    SELECT message_index, role, content, timestamp
    FROM messages
    WHERE session_id = ?
      AND timestamp > ?
    ORDER BY message_index ASC
    LIMIT ?
    """

    cursor = conn.cursor()

    # Fetch before
    cursor.execute(query_before, (session_id, tool_timestamp, context_size))
    before = [dict(row) for row in cursor.fetchall()]
    before.reverse()  # Reverse to get chronological order

    # Fetch after
    cursor.execute(query_after, (session_id, tool_timestamp, context_size))
    after = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "previous": before,
        "next": after
    }


def format_timestamp(ts: Optional[str]) -> str:
    """Format timestamp for display."""
    if not ts:
        return "Unknown time"
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return ts


def highlight_match(text: str, query: str, max_length: int = 200) -> str:
    """
    Show a snippet of text with the match highlighted.

    Args:
        text: Full text
        query: Search query
        max_length: Maximum snippet length

    Returns:
        Highlighted snippet
    """
    # Simple implementation - just show first part
    # FTS5 has snippet() function but we'd need to use it in SQL
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def search_messages(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 10
) -> List[Dict]:
    """
    Search messages using FTS5.

    Args:
        conn: Database connection
        query: FTS5 search query
        project: Filter by project name
        role: Filter by role
        limit: Maximum results

    Returns:
        List of matching messages
    """
    # Build WHERE clause
    where_parts = [f"fts_messages MATCH ?"]
    params = [query]

    if project:
        where_parts.append("project_name LIKE ?")
        params.append(f"%{project}%")

    if role:
        where_parts.append("role = ?")
        params.append(role)

    where_clause = " AND ".join(where_parts)

    # Use FTS5 rank for relevance sorting
    sql = f"""
    SELECT
        message_id,
        session_id,
        message_index,
        role,
        content,
        project_name,
        timestamp,
        rank
    FROM fts_messages
    WHERE {where_clause}
    ORDER BY rank
    LIMIT ?
    """

    params.append(limit)

    cursor = conn.cursor()
    cursor.execute(sql, params)

    results = []
    for row in cursor.fetchall():
        results.append({
            'message_id': row[0],
            'session_id': row[1],
            'message_index': row[2],
            'role': row[3],
            'content': row[4],
            'project_name': row[5],
            'timestamp': row[6],
            'rank': row[7],
            'type': 'message'
        })

    return results


def search_tools(
    conn: sqlite3.Connection,
    query: str,
    project: Optional[str] = None,
    limit: int = 10
) -> List[Dict]:
    """
    Search tool uses using FTS5.

    Args:
        conn: Database connection
        query: FTS5 search query
        project: Filter by project name
        limit: Maximum results

    Returns:
        List of matching tool uses
    """
    where_parts = [f"fts_tool_uses MATCH ?"]
    params = [query]

    if project:
        where_parts.append("project_name LIKE ?")
        params.append(f"%{project}%")

    where_clause = " AND ".join(where_parts)

    sql = f"""
    SELECT
        tool_use_id,
        session_id,
        tool_name,
        tool_input,
        tool_result,
        project_name,
        timestamp,
        rank
    FROM fts_tool_uses
    WHERE {where_clause}
    ORDER BY rank
    LIMIT ?
    """

    params.append(limit)

    cursor = conn.cursor()
    cursor.execute(sql, params)

    results = []
    for row in cursor.fetchall():
        results.append({
            'tool_use_id': row[0],
            'session_id': row[1],
            'tool_name': row[2],
            'tool_input': row[3],
            'tool_result': row[4],
            'project_name': row[5],
            'timestamp': row[6],
            'rank': row[7],
            'type': 'tool'
        })

    return results


def display_results(results: List[Dict], db_path: str, context_size: int, show_json: bool):
    """Display search results."""
    if show_json:
        import json
        print(json.dumps(results, indent=2))
        return

    print(f"\n{'='*80}")
    print(f"Found {len(results)} result(s)")
    print(f"{'='*80}\n")

    for idx, result in enumerate(results, 1):
        if result['type'] == 'message':
            # Display message result
            print(f"[{idx}] MESSAGE")
            print(f"    Project: {result['project_name']}")
            print(f"    Session: {result['session_id']}")
            print(f"    Time: {format_timestamp(result.get('timestamp'))}")
            print(f"    Role: {result['role']}")
            print(f"    Relevance: {result['rank']:.4f}")
            print()

            if context_size > 0:
                context = get_message_context(
                    db_path,
                    result['session_id'],
                    result['message_index'],
                    context_size
                )

                if context['previous']:
                    print("    Context (before):")
                    for msg in context['previous']:
                        role_symbol = "👤" if msg['role'] == 'user' else "🤖"
                        preview = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                        print(f"      {role_symbol} {preview}")
                    print()

                print("    >>> MATCHED MESSAGE <<<")
                role_symbol = "👤" if result['role'] == 'user' else "🤖"
                print(f"    {role_symbol} {result['content']}")
                print()

                if context['next']:
                    print("    Context (after):")
                    for msg in context['next']:
                        role_symbol = "👤" if msg['role'] == 'user' else "🤖"
                        preview = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                        print(f"      {role_symbol} {preview}")
                    print()
            else:
                print(f"    {result['content']}")
                print()

        elif result['type'] == 'tool':
            # Display tool result
            print(f"[{idx}] TOOL: {result['tool_name']}")
            print(f"    Project: {result['project_name']}")
            print(f"    Session: {result['session_id']}")
            print(f"    Time: {format_timestamp(result.get('timestamp'))}")
            print(f"    Relevance: {result['rank']:.4f}")
            print()

            if context_size > 0:
                context = get_tool_context(
                    db_path,
                    result['session_id'],
                    result['timestamp'],
                    context_size
                )

                if context['previous']:
                    print("    Context (before):")
                    for msg in context['previous']:
                        role_symbol = "👤" if msg['role'] == 'user' else "🤖"
                        preview = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                        print(f"      {role_symbol} {preview}")
                    print()

            print("    >>> TOOL USE <<<")
            if result['tool_input']:
                print(f"    Input: {result['tool_input'][:200]}")
                print()

            if result['tool_result']:
                result_preview = result['tool_result'][:300]
                if len(result['tool_result']) > 300:
                    result_preview += "..."
                print(f"    Result:\n    {result_preview}")
                print()

            if context_size > 0 and context['next']:
                print("    Context (after):")
                for msg in context['next']:
                    role_symbol = "👤" if msg['role'] == 'user' else "🤖"
                    preview = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                    print(f"      {role_symbol} {preview}")
                print()

        print(f"{'-'*80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search Claude Code conversations using Full-Text Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
FTS5 Query Syntax:
  Boolean AND:     "async AND error"
  Boolean OR:      "database OR sqlite"
  Boolean NOT:     "typescript NOT react"
  Phrase:          '"promise rejection"'
  Prefix:          "data*"
  Column filter:   "role:user async"

Examples:
  %(prog)s "async AND error"
  %(prog)s '"promise rejection"' --project=monolog
  %(prog)s "database performance" --messages --limit=5
  %(prog)s "typescript NOT react" --role=user
        """
    )

    parser.add_argument("query", help="FTS5 search query")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results (default: 10)")
    parser.add_argument("--project", help="Filter by project name (substring match)")
    parser.add_argument("--role", choices=["user", "assistant"], help="Filter by speaker role (messages only)")
    parser.add_argument("--context", type=int, default=2, help="Number of messages to show before/after (default: 2)")
    parser.add_argument("--messages", action="store_true", help="Search only messages (default: both)")
    parser.add_argument("--tools", action="store_true", help="Search only tool uses")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Default paths
    home = Path.home()
    db_path = home / "claude-conversations" / "conversations.db"

    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    # Check if FTS tables exist
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fts_messages'")
    if not cursor.fetchone():
        print("❌ FTS index not found!")
        print("   Run create_fts_index.py first to create the full-text search index.")
        conn.close()
        sys.exit(1)

    # Perform search
    try:
        print(f"🔍 Searching for: \"{args.query}\"")

        all_results = []

        # Determine what to search
        search_messages_flag = args.messages or (not args.messages and not args.tools)
        search_tools_flag = args.tools or (not args.messages and not args.tools)

        if search_messages_flag:
            message_results = search_messages(
                conn,
                args.query,
                project=args.project,
                role=args.role,
                limit=args.limit
            )
            all_results.extend(message_results)

        if search_tools_flag:
            tool_results = search_tools(
                conn,
                args.query,
                project=args.project,
                limit=args.limit
            )
            all_results.extend(tool_results)

        # Sort by rank
        all_results.sort(key=lambda x: x['rank'])

        # Trim to limit
        all_results = all_results[:args.limit]

        if not all_results:
            print("\n❌ No results found")
            return

        # Display results
        display_results(all_results, str(db_path), args.context, args.json)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
