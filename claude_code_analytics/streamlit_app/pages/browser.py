"""Session browser page."""

import pandas as pd
import streamlit as st

# Add parent directory to path for imports
from claude_code_analytics.streamlit_app.services import DatabaseService

# Initialize service
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

db_service = st.session_state.db_service

st.title("📚 Browse Sessions")

st.markdown(
    """
Browse and explore your Claude Code conversation sessions organized by project.
"""
)

# Display quick stats at the top
try:
    projects = db_service.get_project_summaries()

    col1, col2, col3, col4 = st.columns(4)

    total_projects = len(projects)
    total_sessions = sum(p.total_sessions for p in projects)
    total_messages = sum(p.total_messages for p in projects)
    total_tools = sum(p.total_tool_uses for p in projects)

    col1.metric("Projects", total_projects)
    col2.metric("Sessions", total_sessions)
    col3.metric("Messages", f"{total_messages:,}")
    col4.metric("Tool Uses", f"{total_tools:,}")

    st.divider()

except Exception as e:
    st.error(f"Error loading statistics: {e}")
    st.info("Make sure you've created the database and imported conversations.")
    st.stop()

# Get all projects
try:
    projects = db_service.get_project_summaries()

    if not projects:
        st.warning("No projects found. Import conversations first.")
        st.stop()

    # Project selector at the top
    project_names = {p.project_name: p.project_id for p in projects}
    selected_project_name = st.selectbox(
        "Choose a project:",
        options=list(project_names.keys()),
    )

    if selected_project_name:
        selected_project_id = project_names[selected_project_name]

        # Get sessions for selected project
        sessions = db_service.get_session_summaries(project_id=selected_project_id)

        if not sessions:
            st.info("No sessions found for this project.")
        else:
            # Session selector
            session_options = {
                f"{s.session_id[:8]}... ({s.start_time})": s.session_id for s in sessions
            }

            selected_session_display = st.selectbox(
                "Select a session:",
                options=list(session_options.keys()),
            )

            if selected_session_display:
                selected_session_id = session_options[selected_session_display]

                # Store selected session in session state for other pages
                st.session_state.selected_session_id = selected_session_id

                # Action buttons at the top
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📖 View Full Conversation", width="stretch"):
                        st.switch_page("pages/conversation.py")
                with col2:
                    if st.button("🔬 Analyze This Session", width="stretch"):
                        st.switch_page("pages/analysis.py")

                # Session details below
                st.divider()
                st.subheader("Session Details")

                # Get token usage
                token_usage = db_service.get_token_usage_for_session(selected_session_id)

                col1, col2, col3 = st.columns(3)

                col1.metric("Input Tokens", f"{token_usage.get('input_tokens', 0):,}")
                col2.metric("Output Tokens", f"{token_usage.get('output_tokens', 0):,}")
                col3.metric(
                    "Cache Read Tokens",
                    f"{token_usage.get('cache_read_tokens', 0):,}",
                )

            # Display sessions table
            st.divider()
            st.subheader(f"All Sessions in {selected_project_name}")

            # Create DataFrame
            sessions_df = pd.DataFrame([s.model_dump() for s in sessions])

            # Display sessions
            st.dataframe(
                sessions_df,
                column_config={
                    "session_id": st.column_config.TextColumn("Session ID", width="medium"),
                    "project_name": None,  # Hide
                    "project_id": None,  # Hide
                    "start_time": st.column_config.DatetimeColumn("Start Time"),
                    "end_time": st.column_config.DatetimeColumn("End Time"),
                    "duration_seconds": st.column_config.NumberColumn(
                        "Duration (s)",
                        format="%d",
                    ),
                    "message_count": st.column_config.NumberColumn("Messages"),
                    "tool_use_count": st.column_config.NumberColumn("Tool Uses"),
                    "user_message_count": st.column_config.NumberColumn("User Msgs"),
                    "assistant_message_count": st.column_config.NumberColumn("Assistant Msgs"),
                },
                hide_index=True,
                width="column",
            )

    # Display all projects table at the bottom
    st.divider()
    st.subheader("All Projects")

    # Create a DataFrame for better display
    projects_df = pd.DataFrame([p.model_dump() for p in projects])

    # Display projects as a table
    st.dataframe(
        projects_df,
        column_config={
            "project_id": st.column_config.TextColumn("Project ID", width="medium"),
            "project_name": st.column_config.TextColumn("Project Name", width="large"),
            "total_sessions": st.column_config.NumberColumn("Sessions"),
            "total_messages": st.column_config.NumberColumn("Messages"),
            "total_tool_uses": st.column_config.NumberColumn("Tool Uses"),
            "first_session": st.column_config.DatetimeColumn("First Session"),
            "last_session": st.column_config.DatetimeColumn("Last Session"),
        },
        hide_index=True,
        width="column",
    )

except Exception as e:
    st.error(f"Error loading projects: {e}")
    import traceback

    with st.expander("Error details"):
        st.code(traceback.format_exc())
