#!/usr/bin/env python3
"""Quick test of search functionality."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from streamlit_app.services import DatabaseService

def test_search():
    db = DatabaseService()

    print("=" * 70)
    print("SEARCH FUNCTIONALITY TESTS")
    print("=" * 70)
    print()

    # Test 1: Search messages
    print("1. Testing search_messages('import')...")
    results = db.search_messages("import", limit=5)
    print(f"   Found {len(results)} results")
    if results:
        print(f"   First result: {results[0]['role']} - {results[0]['snippet'][:80]}...")
    print()

    # Test 2: Get unique tool names
    print("2. Testing get_unique_tool_names()...")
    tools = db.get_unique_tool_names()
    print(f"   Found {len(tools)} unique tools")
    print(f"   First 10: {tools[:10]}")
    print()

    # Test 3: Search tool inputs
    print("3. Testing search_tool_inputs('git')...")
    results = db.search_tool_inputs("git", limit=5)
    print(f"   Found {len(results)} results")
    if results:
        print(f"   First result: {results[0]['tool_name']} - {results[0].get('tool_input', '')[:80]}...")
    print()

    # Test 4: Search tool results
    print("4. Testing search_tool_results('error')...")
    results = db.search_tool_results("error", limit=5)
    print(f"   Found {len(results)} results")
    if results:
        print(f"   First result: {results[0]['tool_name']} - {results[0].get('tool_result', '')[:80]}...")
    print()

    # Test 5: Combined search
    print("5. Testing search_all('database')...")
    results = db.search_all("database", limit=10)
    print(f"   Found {len(results)} results")
    if results:
        for i, r in enumerate(results[:3], 1):
            print(f"   {i}. {r['result_type']:12s} - {r['detail']:20s} - {r['project_name'][:30]}")
    print()

    # Test 6: MCP tool stats
    print("6. Testing get_mcp_tool_stats()...")
    stats = db.get_mcp_tool_stats()
    print(f"   Total MCP uses: {stats['total_uses']}")
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Unique MCP tools: {len(stats['by_tool'])}")
    if stats['by_server']:
        print(f"   MCP servers:")
        for server in stats['by_server'][:5]:
            print(f"     - {server['mcp_server']}: {server['total_uses']} uses")
    print()

    print("=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)

if __name__ == "__main__":
    test_search()
