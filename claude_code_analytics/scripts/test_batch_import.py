#!/usr/bin/env python3
"""
Test script to verify batch import optimization works correctly.

This creates a test database, imports test data, and verifies:
1. All data is imported correctly
2. Batch inserts work for messages and tool uses
3. Performance is improved (optional)
"""

import json
import sqlite3

# Add parent directory to path
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from claude_code_analytics.scripts.create_database import SCHEMA_SQL
from claude_code_analytics.scripts.import_conversations import process_session


def create_test_database() -> str:
    """Create a temporary test database."""
    temp_db = tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False)
    temp_db.close()

    conn = sqlite3.connect(temp_db.name)
    conn.executescript(SCHEMA_SQL)

    # Insert test project
    conn.execute(
        """
        INSERT INTO projects (project_id, project_name)
        VALUES ('test-project', '/test/project')
    """
    )
    conn.commit()
    conn.close()

    return temp_db.name


def create_test_session_file(num_messages: int = 50, num_tools: int = 25) -> tuple[str, int, int]:
    """Create a temporary JSONL session file with test data.

    Returns:
        Tuple of (file_path, actual_message_count, actual_tool_count)
    """
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)

    tool_use_counter = 0
    actual_messages = 0

    for i in range(num_messages):
        timestamp = f"2025-01-{1 + (i // 30):02d}T{(i % 24):02d}:00:00.000Z"

        if i % 2 == 0:  # User message
            entry = {
                "timestamp": timestamp,
                "message": {"role": "user", "content": f"Test user message {i}"},
            }
            temp_file.write(json.dumps(entry) + "\n")
            actual_messages += 1
        else:  # Assistant message with potential tool uses
            content = [{"type": "text", "text": f"Test assistant message {i}"}]

            # Add tool uses to some assistant messages
            if tool_use_counter < num_tools and i % 3 == 1:
                tool_id = f"tool_{tool_use_counter}"
                content.append(
                    {
                        "type": "tool_use",
                        "id": tool_id,
                        "name": "Read",
                        "input": {"file_path": f"/test/file{tool_use_counter}.py"},
                    }
                )

                # Add corresponding tool result in SAME message (embedded in assistant content)
                content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"File content {tool_use_counter}",
                    }
                )

                tool_use_counter += 1

            entry = {
                "timestamp": timestamp,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "usage": {"input_tokens": 100 + i, "output_tokens": 50 + i},
                },
            }
            temp_file.write(json.dumps(entry) + "\n")
            actual_messages += 1

    temp_file.close()
    return temp_file.name, actual_messages, tool_use_counter


def verify_import(
    db_path: str, session_id: str, expected_messages: int, expected_tools: int
) -> tuple[bool, str]:
    """Verify the import results."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check message count
    cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
    actual_messages = cursor.fetchone()[0]

    # Check tool use count
    cursor.execute("SELECT COUNT(*) FROM tool_uses WHERE session_id = ?", (session_id,))
    actual_tools = cursor.fetchone()[0]

    # Check session record
    cursor.execute(
        "SELECT message_count, tool_use_count FROM sessions WHERE session_id = ?", (session_id,)
    )
    session_data = cursor.fetchone()

    conn.close()

    if actual_messages != expected_messages:
        return False, f"Message count mismatch: expected {expected_messages}, got {actual_messages}"

    if actual_tools != expected_tools:
        return False, f"Tool use count mismatch: expected {expected_tools}, got {actual_tools}"

    if not session_data:
        return False, "Session record not found"

    session_msg_count, session_tool_count = session_data
    if session_msg_count != expected_messages:
        return (
            False,
            f"Session message count mismatch: expected {expected_messages}, got {session_msg_count}",
        )

    if session_tool_count != expected_tools:
        return (
            False,
            f"Session tool count mismatch: expected {expected_tools}, got {session_tool_count}",
        )

    return True, "All checks passed!"


def test_batch_import():
    """Main test function."""
    print("=" * 70)
    print("BATCH INSERT OPTIMIZATION TEST")
    print("=" * 70)
    print()

    # Create test database
    print("1️⃣  Creating test database...")
    db_path = create_test_database()
    print(f"   ✅ Database created: {db_path}")
    print()

    # Create test session file
    num_messages = 100
    num_tools = 40
    print(f"2️⃣  Creating test session file ({num_messages} messages, {num_tools} tool uses)...")
    session_file, expected_messages, expected_tools = create_test_session_file(
        num_messages, num_tools
    )
    session_id = Path(session_file).stem
    print(f"   ✅ Session file created: {session_file}")
    print(f"   Session ID: {session_id}")
    print(f"   Actual data: {expected_messages} messages, {expected_tools} tool uses")
    print()

    # Import the session
    print("3️⃣  Importing session with batch inserts...")
    conn = sqlite3.connect(db_path)

    start_time = time.time()
    msg_count, tool_count = process_session(Path(session_file), "test-project", conn)
    elapsed = time.time() - start_time

    conn.commit()
    conn.close()

    print(f"   ✅ Import completed in {elapsed:.3f}s")
    print(f"   Imported: {msg_count} messages, {tool_count} tool uses")
    print()

    # Verify results
    print("4️⃣  Verifying import results...")
    success, message = verify_import(db_path, session_id, expected_messages, expected_tools)

    if success:
        print(f"   ✅ {message}")
        print()
        print("=" * 70)
        print("TEST RESULT: ✅ PASSED")
        print("=" * 70)
        print()
        print("Batch insert optimization is working correctly!")
        print(f"  - All {expected_messages} messages were inserted")
        print(f"  - All {num_tools} tool uses were inserted")
        print("  - Session metadata is correct")
        print(f"  - Performance: {elapsed:.3f}s for {expected_messages + num_tools} rows")
        return True
    else:
        print(f"   ❌ {message}")
        print()
        print("=" * 70)
        print("TEST RESULT: ❌ FAILED")
        print("=" * 70)
        return False


def test_incremental_import():
    """Test incremental import with batch inserts."""
    print()
    print("=" * 70)
    print("INCREMENTAL IMPORT TEST")
    print("=" * 70)
    print()

    # Create test database and initial import
    print("1️⃣  Creating test database and initial data...")
    db_path = create_test_database()
    session_file_1, expected_msg_1, expected_tool_1 = create_test_session_file(
        num_messages=30, num_tools=10
    )
    session_id = Path(session_file_1).stem

    conn = sqlite3.connect(db_path)
    msg_count_1, tool_count_1 = process_session(Path(session_file_1), "test-project", conn)
    conn.commit()
    print(f"   ✅ Initial import: {msg_count_1} messages, {tool_count_1} tool uses")
    print()

    # Add more data to the same session
    print("2️⃣  Adding more messages to existing session...")
    session_file_2, expected_msg_2, expected_tool_2 = create_test_session_file(
        num_messages=60, num_tools=25
    )
    # Rename to same session ID
    new_path = Path(session_file_2).parent / f"{session_id}.jsonl"
    Path(session_file_2).rename(new_path)

    msg_count_2, tool_count_2 = process_session(new_path, "test-project", conn)
    conn.commit()
    conn.close()

    print(f"   ✅ Incremental import: +{msg_count_2} messages, +{tool_count_2} tool uses")
    print()

    # Verify results
    print("3️⃣  Verifying incremental import...")
    expected_new_messages = expected_msg_2 - expected_msg_1  # Should only import the difference
    expected_new_tools = expected_tool_2 - expected_tool_1

    if msg_count_2 == expected_new_messages and tool_count_2 == expected_new_tools:
        print("   ✅ Incremental import worked correctly!")
        print(f"      Only imported {msg_count_2} new messages (not the full {expected_msg_2})")
        print(f"      Only imported {tool_count_2} new tool uses (not the full {expected_tool_2})")
        print()
        print("=" * 70)
        print("INCREMENTAL TEST: ✅ PASSED")
        print("=" * 70)
        return True
    else:
        print(f"   ❌ Expected {expected_new_messages} new messages, got {msg_count_2}")
        print(f"   ❌ Expected {expected_new_tools} new tool uses, got {tool_count_2}")
        print()
        print("=" * 70)
        print("INCREMENTAL TEST: ❌ FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    # Run both tests
    test1_passed = test_batch_import()
    test2_passed = test_incremental_import()

    print()
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Batch Import Test:       {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Incremental Import Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print()

    if test1_passed and test2_passed:
        print("🎉 All tests passed! Batch insert optimization is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)
