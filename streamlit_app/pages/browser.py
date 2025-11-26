"""Session browser page."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.services import DatabaseService

# Initialize service
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

db_service = st.session_state.db_service

st.title("📚 Browse Sessions")

st.markdown("""
Browse and explore your Claude Code conversation sessions organized by project.
""")

# Get all projects
try:
    projects = db_service.get_project_summaries()

    if not projects:
        st.warning("No projects found. Import conversations first.")
        st.stop()

    # Project selector
    st.subheader("Select a Project")

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
        use_container_width=True,
    )

    # Select project
    project_names = {p.project_name: p.project_id for p in projects}
    selected_project_name = st.selectbox(
        "Choose a project to view sessions:",
        options=list(project_names.keys()),
    )

    if selected_project_name:
        selected_project_id = project_names[selected_project_name]

        st.divider()
        st.subheader(f"Sessions in {selected_project_name}")

        # Get sessions for selected project
        sessions = db_service.get_session_summaries(project_id=selected_project_id)

        if not sessions:
            st.info("No sessions found for this project.")
        else:
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
                use_container_width=True,
            )

            # Session selector for detailed view
            st.divider()
            st.subheader("Session Details")

            session_options = {
                f"{s.session_id[:8]}... ({s.start_time})": s.session_id
                for s in sessions
            }

            selected_session_display = st.selectbox(
                "Select a session to view details:",
                options=list(session_options.keys()),
            )

            if selected_session_display:
                selected_session_id = session_options[selected_session_display]

                # Get token usage
                token_usage = db_service.get_token_usage_for_session(selected_session_id)

                col1, col2, col3 = st.columns(3)

                col1.metric("Input Tokens", f"{token_usage.get('input_tokens', 0):,}")
                col2.metric("Output Tokens", f"{token_usage.get('output_tokens', 0):,}")
                col3.metric(
                    "Cache Read Tokens",
                    f"{token_usage.get('cache_read_tokens', 0):,}",
                )

                # Store selected session in session state for other pages
                st.session_state.selected_session_id = selected_session_id

                # Add button to view conversation
                if st.button("View Full Conversation →"):
                    st.switch_page("pages/conversation.py")

                # Add button to analyze
                if st.button("Analyze This Session →"):
                    st.switch_page("pages/analysis.py")

except Exception as e:
    st.error(f"Error loading projects: {e}")
    import traceback
    with st.expander("Error details"):
        st.code(traceback.format_exc())
