"""Conversation viewer page."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.services import DatabaseService

# Initialize service
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

db_service = st.session_state.db_service

st.title("💬 View Conversation")

# Check if a session is selected
if "selected_session_id" not in st.session_state:
    st.info("No session selected. Go to **Browse Sessions** to select a session.")
    if st.button("Browse Sessions →"):
        st.switch_page("pages/browser.py")
    st.stop()

session_id = st.session_state.selected_session_id

# Get session info
try:
    session = db_service.get_session(session_id)

    if not session:
        st.error(f"Session not found: {session_id}")
        st.stop()

    # Display session info
    st.subheader(f"Session: {session_id[:16]}...")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages", session.message_count)
    col2.metric("Tool Uses", session.tool_use_count)

    if session.start_time:
        col3.write(f"**Start:** {session.start_time.strftime('%Y-%m-%d %H:%M')}")
    if session.end_time:
        col4.write(f"**End:** {session.end_time.strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        role_filter = st.selectbox(
            "Filter by role:",
            options=["All", "User", "Assistant"],
        )

    with col2:
        search_query = st.text_input("Search in messages:")

    # Get messages
    messages = db_service.get_messages_for_session(session_id)

    # Apply filters
    if role_filter != "All":
        messages = [m for m in messages if m.role == role_filter.lower()]

    if search_query:
        messages = [
            m for m in messages
            if m.content and search_query.lower() in m.content.lower()
        ]

    st.write(f"**Showing {len(messages)} message(s)**")

    # Display messages
    for msg in messages:
        role_emoji = "👤" if msg.role == "user" else "🤖"
        role_color = "blue" if msg.role == "user" else "green"

        with st.container():
            st.markdown(f"### {role_emoji} **:{role_color}[{msg.role.title()}]** - {msg.timestamp.strftime('%H:%M:%S')}")

            if msg.content:
                st.markdown(msg.content)
            else:
                st.caption("(No text content)")

            # Show token usage for assistant messages
            if msg.role == "assistant" and msg.input_tokens:
                with st.expander("Token usage"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Input", f"{msg.input_tokens:,}")
                    col2.metric("Output", f"{msg.output_tokens or 0:,}")
                    if msg.cache_read_input_tokens:
                        col3.metric("Cache Read", f"{msg.cache_read_input_tokens:,}")

            st.divider()

    # Get tool uses
    st.subheader("Tool Uses")

    tool_uses = db_service.get_tool_uses_for_session(session_id)

    if not tool_uses:
        st.info("No tool uses in this session.")
    else:
        for tool in tool_uses:
            error_badge = "❌" if tool.is_error else "✅"

            with st.expander(f"{error_badge} {tool.tool_name} - {tool.timestamp.strftime('%H:%M:%S')}"):
                if tool.tool_input:
                    st.markdown("**Input:**")
                    st.code(tool.tool_input, language="json")

                if tool.tool_result:
                    st.markdown("**Result:**")
                    st.text(tool.tool_result[:1000] + ("..." if len(tool.tool_result) > 1000 else ""))

except Exception as e:
    st.error(f"Error loading conversation: {e}")
    import traceback
    with st.expander("Error details"):
        st.code(traceback.format_exc())
