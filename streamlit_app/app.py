"""
Claude Code Analytics Dashboard

A Streamlit application for analyzing Claude Code conversation transcripts.
"""

import streamlit as st
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Claude Code Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define pages
home_page = st.Page(
    "pages/home.py",
    title="Home",
    icon="🏠",
    default=True,
)

browser_page = st.Page(
    "pages/browser.py",
    title="Browse Sessions",
    icon="📚",
)

analysis_page = st.Page(
    "pages/analysis.py",
    title="Run Analysis",
    icon="🔬",
)

analytics_page = st.Page(
    "pages/analytics.py",
    title="Analytics Dashboard",
    icon="📊",
)

conversation_page = st.Page(
    "pages/conversation.py",
    title="View Conversation",
    icon="💬",
)

# Build navigation
pg = st.navigation(
    {
        "Main": [home_page],
        "Conversations": [browser_page, conversation_page],
        "Analysis": [analysis_page, analytics_page],
    }
)

# Run the selected page
pg.run()
