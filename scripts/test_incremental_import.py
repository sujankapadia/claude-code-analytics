#!/usr/bin/env python3
"""
Test script for incremental import logic.
Analyzes what would be imported without modifying the database.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

# Database path
DB_PATH = Path.home() / "claude-conversations" / "conversations.db"

# Test session
SESSION_ID = "0bd6a9b6-c060-454b-ac10-5b39e823ba74"
SESSION_FILE = Path.home() / ".claude" / "projects" / "-Users-skapadia-dev-personal-claude-code-utils" / f"{SESSION_ID}.jsonl"


def get_current_state(session_id: str) -> dict:
    """Get current state of session in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get message count and max index
    cursor.execute("""
        SELECT COUNT(*), MAX(message_index)
        FROM messages
        WHERE session_id = ?
    """, (session_id,))

    message_count, max_index = cursor.fetchone()

    # Get tool use count
    cursor.execute("""
        SELECT COUNT(*)
        FROM tool_uses
        WHERE session_id = ?
    """, (session_id,))

    tool_use_count = cursor.fetchone()[0]

    conn.close()

    return {
        'message_count': message_count or 0,
        'max_index': max_index if max_index is not None else -1,
        'tool_use_count': tool_use_count or 0
    }


def analyze_jsonl_file(file_path: Path, skip_until_index: int = -1):
    """Analyze JSONL file and show what would be imported."""

    messages = []
    tool_uses_count = 0

    with open(file_path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                # Skip non-message entries
                if 'message' not in entry:
                    continue

                msg = entry['message']
                role = msg.get('role')

                # Only count user and assistant messages
                if role not in ['user', 'assistant']:
                    continue

                message_index = len(messages)

                # Count tool uses in this message
                content = msg.get('content', [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'tool_use':
                            tool_uses_count += 1

                # Track message info
                messages.append({
                    'index': message_index,
                    'role': role,
                    'timestamp': entry.get('timestamp'),
                    'is_new': message_index > skip_until_index
                })

            except json.JSONDecodeError:
                continue

    return messages, tool_uses_count


def main():
    print("=" * 70)
    print("INCREMENTAL IMPORT TEST (DRY RUN)")
    print("=" * 70)
    print()

    # Get current database state
    print(f"Session: {SESSION_ID}")
    print(f"File: {SESSION_FILE}")
    print()

    current = get_current_state(SESSION_ID)
    print("Current Database State:")
    print(f"  Messages: {current['message_count']}")
    print(f"  Max Index: {current['max_index']}")
    print(f"  Tool Uses: {current['tool_use_count']}")
    print()

    # Analyze JSONL file
    print("Analyzing JSONL file...")
    messages, tool_uses = analyze_jsonl_file(SESSION_FILE, current['max_index'])

    total_messages = len(messages)
    new_messages = [m for m in messages if m['is_new']]

    print(f"JSONL File State:")
    print(f"  Total Messages: {total_messages}")
    print(f"  Total Tool Uses: {tool_uses}")
    print()

    print("=" * 70)
    print("INCREMENTAL IMPORT ANALYSIS")
    print("=" * 70)
    print()

    if not new_messages:
        print("✅ No new messages to import - database is up to date!")
    else:
        print(f"📊 NEW MESSAGES TO IMPORT: {len(new_messages)}")
        print(f"   Starting from index: {current['max_index'] + 1}")
        print()

        # Show first 3 new messages
        print("First 3 new messages:")
        for msg in new_messages[:3]:
            print(f"  [{msg['index']}] {msg['role']:10s} @ {msg['timestamp']}")

        if len(new_messages) > 6:
            print("  ...")

        # Show last 3 new messages
        if len(new_messages) > 3:
            print()
            print("Last 3 new messages:")
            for msg in new_messages[-3:]:
                print(f"  [{msg['index']}] {msg['role']:10s} @ {msg['timestamp']}")

        print()
        print(f"Estimated new tool uses: ~{tool_uses - current['tool_use_count']}")
        print()
        print("=" * 70)
        print("RECOMMENDATION")
        print("=" * 70)
        print()
        print("✅ Safe to implement incremental import!")
        print(f"   Will add {len(new_messages)} new messages")
        print(f"   Will preserve existing {current['message_count']} messages")
        print()
        print("Logic:")
        print(f"   1. Check if session '{SESSION_ID}' exists")
        print(f"   2. Get max message_index (currently {current['max_index']})")
        print(f"   3. Only import messages with index > {current['max_index']}")
        print(f"   4. Update session end_time and message_count")


if __name__ == '__main__':
    main()
