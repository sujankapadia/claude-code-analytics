#!/usr/bin/env python3
"""
Search Claude Code conversation history using semantic similarity.

Usage:
    search_conversations.py "your search query" [options]

Examples:
    search_conversations.py "how to handle async errors"
    search_conversations.py "database optimization" --project=monolog --limit=5
    search_conversations.py "react hooks" --after=2024-10-01 --context=3
"""

import argparse
import chromadb
import sqlite3
from sentence_transformers import SentenceTransformer
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

    # Get surrounding messages
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

    # Organize into previous, current, next
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


def format_timestamp(ts: Optional[str]) -> str:
    """Format timestamp for display."""
    if not ts:
        return "Unknown time"
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return ts


def display_results(results: List[Dict], db_path: str, context_size: int, show_json: bool):
    """
    Display search results in a readable format.

    Args:
        results: List of search results from ChromaDB
        db_path: Path to SQLite for fetching context
        context_size: Number of context messages to show
        show_json: Output as JSON instead
    """
    if show_json:
        import json
        output = []
        for result in results:
            output.append({
                "score": result['score'],
                "message": result['document'],
                "metadata": result['metadata']
            })
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print(f"\n{'='*80}")
    print(f"Found {len(results)} result(s)")
    print(f"{'='*80}\n")

    for idx, result in enumerate(results, 1):
        meta = result['metadata']
        score = result['score']

        # Header
        print(f"[{idx}] Score: {score:.4f}")
        print(f"    Project: {meta['project_name']}")
        print(f"    Session: {meta['session_id']}")
        print(f"    Time: {format_timestamp(meta.get('timestamp'))}")
        print(f"    Role: {meta['role']}")
        print()

        # Get context if requested
        if context_size > 0:
            context = get_message_context(
                db_path,
                meta['session_id'],
                int(meta['message_index']),
                context_size
            )

            # Show previous messages
            if context['previous']:
                print("    Context (before):")
                for msg in context['previous']:
                    role_symbol = "👤" if msg['role'] == 'user' else "🤖"
                    preview = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                    print(f"      {role_symbol} {preview}")
                print()

            # Show matched message (highlighted)
            print("    >>> MATCHED MESSAGE <<<")
            role_symbol = "👤" if meta['role'] == 'user' else "🤖"
            print(f"    {role_symbol} {result['document']}")
            print()

            # Show next messages
            if context['next']:
                print("    Context (after):")
                for msg in context['next']:
                    role_symbol = "👤" if msg['role'] == 'user' else "🤖"
                    preview = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                    print(f"      {role_symbol} {preview}")
                print()

        else:
            # Just show the matched message
            print(f"    {result['document']}")
            print()

        print(f"{'-'*80}\n")


def search_conversations(
    query: str,
    chroma_path: str,
    db_path: str,
    limit: int = 10,
    project: Optional[str] = None,
    role: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    context_size: int = 2,
    show_json: bool = False
):
    """
    Search conversations using semantic similarity.

    Args:
        query: Search query text
        chroma_path: Path to ChromaDB storage
        db_path: Path to SQLite database
        limit: Maximum number of results
        project: Filter by project name (substring match)
        role: Filter by role (user/assistant)
        after: Only messages after this date
        before: Only messages before this date
        context_size: Number of messages to show before/after
        show_json: Output as JSON
    """
    # Load embedding model (same as used for indexing)
    print("📥 Loading embedding model...")
    model = SentenceTransformer('all-mpnet-base-v2')

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=chroma_path)

    try:
        collection = client.get_collection("conversations")
    except:
        print("❌ Collection 'conversations' not found!")
        print("   Run embed_conversations.py first to create embeddings.")
        sys.exit(1)

    # Build where clause for filtering
    where_conditions = []

    if role:
        where_conditions.append({"role": role})

    if after:
        where_conditions.append({"timestamp": {"$gte": after}})

    if before:
        where_conditions.append({"timestamp": {"$lte": before}})

    # Combine conditions
    where_clause = None
    if len(where_conditions) == 1:
        where_clause = where_conditions[0]
    elif len(where_conditions) > 1:
        where_clause = {"$and": where_conditions}

    # Perform search
    print(f"🔍 Searching for: \"{query}\"")
    if where_clause:
        print(f"   Filters: {where_clause}")

    # Embed the query using the same model
    query_embedding = model.encode(query, show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where=where_clause
    )

    # Format results
    formatted_results = []
    if results['ids'] and results['ids'][0]:
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]

            # Post-filter by project name (substring match)
            if project and project.lower() not in metadata.get('project_name', '').lower():
                continue

            # ChromaDB returns L2 distance by default
            # Convert to similarity score (1 / (1 + distance))
            distance = results['distances'][0][i]
            similarity = 1 / (1 + distance)

            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': metadata,
                'score': similarity
            })

        # Trim to limit after filtering
        formatted_results = formatted_results[:limit]

    if not formatted_results:
        print("\n❌ No results found")
        return

    # Display results
    display_results(formatted_results, db_path, context_size, show_json)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search Claude Code conversation history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "how to handle async errors"
  %(prog)s "database optimization" --project=monolog --limit=5
  %(prog)s "react hooks" --after=2024-10-01 --context=3
  %(prog)s "typescript errors" --role=user --json
        """
    )

    parser.add_argument("query", help="Search query text")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results (default: 10)")
    parser.add_argument("--project", help="Filter by project name (substring match)")
    parser.add_argument("--role", choices=["user", "assistant"], help="Filter by speaker role")
    parser.add_argument("--after", help="Only messages after this date (YYYY-MM-DD)")
    parser.add_argument("--before", help="Only messages before this date (YYYY-MM-DD)")
    parser.add_argument("--context", type=int, default=2, help="Number of messages to show before/after (default: 2)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Default paths
    home = Path.home()
    db_path = home / "claude-conversations" / "conversations.db"
    chroma_path = home / "claude-conversations" / "chroma_db"

    # Check if paths exist
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    if not chroma_path.exists():
        print(f"❌ ChromaDB not found: {chroma_path}")
        print("   Run embed_conversations.py first to create embeddings.")
        sys.exit(1)

    # Perform search
    try:
        search_conversations(
            query=args.query,
            chroma_path=str(chroma_path),
            db_path=str(db_path),
            limit=args.limit,
            project=args.project,
            role=args.role,
            after=args.after,
            before=args.before,
            context_size=args.context,
            show_json=args.json
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
