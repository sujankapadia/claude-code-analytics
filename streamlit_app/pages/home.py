"""Home page for Claude Code Analytics."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.services import DatabaseService

# Initialize service
db_service = DatabaseService()

st.title("🤖 Claude Code Analytics")

st.markdown("""
Welcome to the Claude Code Analytics Dashboard! This tool helps you analyze and
understand your Claude Code conversation transcripts.

## Features

### 📚 Browse Sessions
- View all your projects and conversation sessions
- See metadata like message counts, timestamps, and tool usage
- Filter and search through your conversations

### 💬 View Conversations
- Read full conversation transcripts
- Filter by role (user/assistant)
- Search within conversations

### 🔬 Run Analysis
- Perform AI-powered analysis on your conversations
- Available analysis types:
  - **Technical Decisions**: Extract decisions, alternatives, and reasoning
  - **Error Patterns**: Identify errors, root causes, and resolutions
- Export analysis results as markdown

### 📊 Analytics Dashboard
- Token usage statistics and trends
- Tool usage patterns and error rates
- Project and session metrics
- Daily activity charts

## Getting Started

Use the navigation menu on the left to explore your conversation data!
""")

# Display quick stats
st.divider()
st.subheader("Quick Statistics")

try:
    summaries = db_service.get_project_summaries()

    col1, col2, col3, col4 = st.columns(4)

    total_projects = len(summaries)
    total_sessions = sum(p.total_sessions for p in summaries)
    total_messages = sum(p.total_messages for p in summaries)
    total_tools = sum(p.total_tool_uses for p in summaries)

    col1.metric("Projects", total_projects)
    col2.metric("Sessions", total_sessions)
    col3.metric("Messages", f"{total_messages:,}")
    col4.metric("Tool Uses", f"{total_tools:,}")

except Exception as e:
    st.error(f"Error loading statistics: {e}")
    st.info("Make sure you've created the database and imported conversations.")
