"""Conversation viewer page with terminal-style chat interface."""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.services import DatabaseService

# Initialize service
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

db_service = st.session_state.db_service

# Custom CSS for message styling and highlighting
st.markdown("""
<style>
    .msg-divider {
        border-top: 1px solid #333;
        margin: 1.5rem 0;
    }

    /* Highlight animation for target message */
    .message-highlight {
        border-left: 4px solid #ffd700;
        padding-left: 1rem;
        margin-left: -1rem;
        background-color: rgba(255, 215, 0, 0.15);
        animation: fadeHighlight 3s ease-in-out;
    }

    @keyframes fadeHighlight {
        0% {
            background-color: rgba(255, 215, 0, 0.3);
        }
        70% {
            background-color: rgba(255, 215, 0, 0.3);
        }
        100% {
            background-color: rgba(255, 215, 0, 0.15);
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("💬 View Conversation")

# Check for deep link via query parameters
query_params = st.query_params
target_message_index = None

if "session_id" in query_params:
    # Deep link from search results
    session_id = query_params["session_id"]
    if "message_index" in query_params:
        try:
            target_message_index = int(query_params["message_index"])
        except (ValueError, TypeError):
            target_message_index = None
elif "selected_session_id" in st.session_state:
    # Normal navigation from browser
    session_id = st.session_state.selected_session_id
else:
    # No session selected
    st.info("No session selected. Go to **Browse Sessions** to select a session.")
    if st.button("Browse Sessions →"):
        st.switch_page("pages/browser.py")
    st.stop()

# Get session info
try:
    session = db_service.get_session(session_id)

    if not session:
        st.error(f"Session not found: {session_id}")
        st.stop()

    # Session header
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader(f"Session: {session_id[:16]}...")

    with col2:
        if st.button("← Back to Browser"):
            st.switch_page("pages/browser.py")

    # Session metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages", session.message_count)
    col2.metric("Tool Uses", session.tool_use_count)

    if session.start_time:
        col3.write(f"**Start:** {session.start_time.strftime('%Y-%m-%d %H:%M')}")
    if session.end_time:
        col4.write(f"**End:** {session.end_time.strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        role_filter = st.selectbox(
            "Filter by role:",
            options=["All", "User", "Assistant"],
        )

    with col2:
        search_query = st.text_input("Search in messages:")

    with col3:
        st.write("")  # Spacing
        st.write("")
        show_tokens = st.checkbox("Show tokens", value=False)

    # Get messages
    messages = db_service.get_messages_for_session(session_id)

    # Get tool uses and create a lookup by message index
    tool_uses = db_service.get_tool_uses_for_session(session_id)
    tools_by_message = {}
    for tool in tool_uses:
        if tool.message_index not in tools_by_message:
            tools_by_message[tool.message_index] = []
        tools_by_message[tool.message_index].append(tool)

    # Apply filters
    if role_filter != "All":
        messages = [m for m in messages if m.role == role_filter.lower()]

    if search_query:
        messages = [
            m for m in messages
            if m.content and search_query.lower() in m.content.lower()
        ]

    # Filter out messages with no content UNLESS they have tool uses
    messages = [
        m for m in messages
        if (m.content and m.content.strip()) or (m.message_index in tools_by_message)
    ]

    st.write(f"**Showing {len(messages)} message(s)**")

    # Scroll to bottom button
    if len(messages) > 5:
        if st.button("⬇️ Scroll to Bottom"):
            st.markdown('<script>window.scrollTo(0, document.body.scrollHeight);</script>', unsafe_allow_html=True)

    st.divider()

    # Display messages in simple terminal style
    for msg in messages:
        # Determine if this message should be highlighted
        is_target = target_message_index is not None and msg.message_index == target_message_index

        # Create container with ID for deep linking
        message_id = f"msg-{msg.message_index}"
        container_class = "message-highlight" if is_target else ""

        # Build header line
        role_emoji = "👤" if msg.role == "user" else "🤖"
        role_label = msg.role.upper()
        timestamp = msg.timestamp.strftime('%H:%M:%S')

        header_parts = [f"{role_emoji} **{role_label}**", f"`{timestamp}`"]

        # Add token info if enabled
        if show_tokens and msg.role == "assistant" and msg.input_tokens:
            token_parts = [f"↓{msg.input_tokens:,}"]
            if msg.output_tokens:
                token_parts.append(f"↑{msg.output_tokens:,}")
            if msg.cache_read_input_tokens:
                token_parts.append(f"⚡{msg.cache_read_input_tokens:,}")
            header_parts.append(f"`{' '.join(token_parts)}`")

        # Start message container with ID
        st.markdown(f'<div id="{message_id}" class="{container_class}">', unsafe_allow_html=True)
        st.markdown(" · ".join(header_parts))

        # Message content
        if msg.content and msg.content.strip():
            st.markdown(msg.content)

        # Tool uses
        message_tools = tools_by_message.get(msg.message_index, [])
        if message_tools:
            for tool in message_tools:
                error_indicator = " ❌" if tool.is_error else ""
                st.markdown(f"🔧 **{tool.tool_name}**{error_indicator}")

                if tool.tool_result:
                    result_text = tool.tool_result[:2000]
                    if len(tool.tool_result) > 2000:
                        result_text += "\n... (output truncated)"
                    st.code(result_text, language="text")

        # Close message container
        st.markdown('</div>', unsafe_allow_html=True)

        # Divider between messages
        st.markdown('<div class="msg-divider"></div>', unsafe_allow_html=True)

    # Scroll to target message using scrollIntoView
    if target_message_index is not None:
        import streamlit.components.v1 as components
        components.html(f"""
        <script>
            setTimeout(function() {{
                const targetElement = window.parent.document.getElementById('msg-{target_message_index}');
                if (targetElement) {{
                    targetElement.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                }}
            }}, 100);
        </script>
        """, height=0)

    # Scroll to top button at bottom
    if len(messages) > 5:
        st.divider()
        if st.button("⬆️ Scroll to Top"):
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading conversation: {e}")
    import traceback
    with st.expander("Error details"):
        st.code(traceback.format_exc())
