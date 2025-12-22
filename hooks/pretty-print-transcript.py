#!/usr/bin/env python3
"""
Pretty print Claude Code conversation transcripts from JSONL format.
Usage: python pretty_print_transcript.py <transcript.jsonl>
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def format_timestamp(ts):
    """Convert timestamp to readable format."""
    try:
        dt = datetime.fromtimestamp(ts / 1000)  # Convert from milliseconds
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ""


def print_separator(char="─", length=80):
    """Print a visual separator line."""
    print(char * length)


def format_tool_input(tool_input):
    """Format tool input in a readable way."""
    if not tool_input:
        return ""
    
    lines = []
    for key, value in tool_input.items():
        if key == "command":
            lines.append(f"$ {value}")
        elif key == "file_path":
            lines.append(f"File: {value}")
        elif key == "content" and len(str(value)) > 200:
            lines.append(f"Content: {str(value)[:200]}... ({len(str(value))} chars)")
        elif key == "content":
            lines.append(f"Content:\n{value}")
        else:
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            lines.append(f"{key}: {value_str}")
    return "\n".join(lines)


def format_message_content(content):
    """Extract and format message content from various structures."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif item.get("type") == "tool_use":
                    tool_name = item.get("name", "unknown")
                    tool_id = item.get("id", "")
                    tool_input = item.get("input", {})
                    
                    parts.append(f"\n🔧 Tool: {tool_name} (ID: {tool_id[:8]}...)")
                    if tool_input:
                        formatted_input = format_tool_input(tool_input)
                        if formatted_input:
                            parts.append(formatted_input)
                elif item.get("type") == "tool_result":
                    tool_id = item.get("tool_use_id", "")
                    parts.append(f"\n✅ Tool Result (ID: {tool_id[:8]}...)")
                    
                    content_items = item.get("content")
                    
                    if isinstance(content_items, str):
                        # Content is a direct string
                        if len(content_items) > 1000:
                            parts.append(f"{content_items[:997]}...")
                        else:
                            parts.append(content_items)
                    elif isinstance(content_items, list):
                        # Content is a list of items
                        for content_item in content_items:
                            if isinstance(content_item, dict) and content_item.get("type") == "text":
                                result_text = content_item.get("text", "")
                                if len(result_text) > 1000:
                                    parts.append(f"{result_text[:997]}...")
                                else:
                                    parts.append(result_text)
                            elif isinstance(content_item, str):
                                parts.append(content_item)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def print_message(entry):
    """Print a single message entry."""
    message = entry.get("message", {})
    role = message.get("role", "unknown")
    content = message.get("content", "")
    timestamp = entry.get("ts", 0)
    
    # Format the header based on role
    if role == "user":
        print("\n" + "=" * 80)
        print("👤 USER")
        if timestamp:
            print(f"   {format_timestamp(timestamp)}")
        print("=" * 80)
    elif role == "assistant":
        print("\n" + "-" * 80)
        print("🤖 CLAUDE")
        if timestamp:
            print(f"   {format_timestamp(timestamp)}")
        print("-" * 80)
    else:
        print(f"\n[{role.upper()}]")
    
    # Format and print the content
    formatted_content = format_message_content(content)
    if formatted_content:
        print(formatted_content)


def print_tool_use(entry):
    """Print tool usage information."""
    tool_use = entry.get("toolUse", {})
    if tool_use:
        tool_name = tool_use.get("name", "unknown")
        tool_id = tool_use.get("id", "")
        print(f"\n🔧 Tool: {tool_name} (ID: {tool_id[:8]}...)")
        
        tool_input = tool_use.get("input", {})
        if tool_input:
            formatted_input = format_tool_input(tool_input)
            if formatted_input:
                print(formatted_input)


def print_tool_result(entry):
    """Print tool result information."""
    tool_result = entry.get("toolResult", {})
    if tool_result:
        tool_id = tool_result.get("toolUseId", "")
        print(f"\n✅ Tool Result (ID: {tool_id[:8]}...)")
        
        content = tool_result.get("content")
        
        if isinstance(content, str):
            # Content is a direct string
            if len(content) > 1000:
                print(f"{content[:997]}...")
            else:
                print(content)
        elif isinstance(content, list):
            # Content is a list of items
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if len(text) > 1000:
                        print(f"{text[:997]}...")
                    else:
                        print(text)
                elif isinstance(item, str):
                    print(item)


def pretty_print_transcript(filepath):
    """Read and pretty print a Claude Code transcript."""
    path = Path(filepath)
    
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1
    
    print("=" * 80)
    print(f"CLAUDE CODE CONVERSATION")
    print(f"File: {path.name}")
    print(f"Path: {path}")
    print("=" * 80)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            line_count = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    line_count += 1
                    
                    # Handle different entry types
                    if "message" in entry:
                        print_message(entry)
                    elif "toolUse" in entry:
                        print_tool_use(entry)
                    elif "toolResult" in entry:
                        print_tool_result(entry)
                    
                except json.JSONDecodeError as e:
                    print(f"\nWarning: Skipped malformed JSON on line {line_count}: {e}", file=sys.stderr)
                    continue
        
        print("\n" + "=" * 80)
        print(f"End of conversation ({line_count} entries)")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        return 1
    
    return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python pretty_print_transcript.py <transcript.jsonl>")
        print("\nExample:")
        print("  python pretty_print_transcript.py ~/.claude/projects/my-project/abc123.jsonl")
        return 1
    
    return pretty_print_transcript(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
