"""About page for Claude Code Analytics."""

import streamlit as st

st.title("ℹ️ About")

st.markdown(
    """
**Claude Code Analytics** is a tool for analyzing and exploring your Claude Code conversation transcripts.

## Features

### 📥 Import Data
- Import conversation transcripts from your Claude Code projects
- Incremental updates - only imports new messages
- Automatic detection of new data available
- Never duplicates existing data

### 📚 Browse Sessions
- View all your projects and conversation sessions
- See metadata like message counts, timestamps, and tool usage
- Quick access to conversations and analysis
- Filter and explore session data

### 💬 View Conversations
- Read full conversation transcripts
- Filter by role (user/assistant)
- Search within conversations
- View tool uses linked to messages

### 🔬 Run Analysis
- Perform AI-powered analysis on your conversations
- Available analysis types:
  - **Technical Decisions**: Extract decisions, alternatives, and reasoning
  - **Error Patterns**: Identify errors, root causes, and resolutions
- Export analysis results as markdown
- Multiple AI provider options (Google Gemini, OpenRouter)

### 📊 Analytics Dashboard
- Token usage statistics and trends
- Tool usage patterns and error rates
- Project and session metrics
- Daily activity charts

## Getting Started

1. **Import Data**: Use the Import Data page to load your conversations into the database
2. **Browse Sessions**: Explore your projects and sessions
3. **View & Analyze**: Read conversations and run AI-powered analysis
4. **Monitor Metrics**: Track your usage patterns on the Analytics Dashboard

## Data Storage

- **Database**: `~/claude-conversations/conversations.db` (SQLite)
- **Source Files**: `~/.claude/projects/` (JSONL transcripts)
- **Exports**: Analysis results downloaded as markdown files

## Need Help?

Check the [Claude Code documentation](https://docs.claude.com/claude-code) for more information.
"""
)
