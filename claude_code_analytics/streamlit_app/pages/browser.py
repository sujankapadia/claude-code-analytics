"""Session browser page."""

import pandas as pd
import streamlit as st

# Add parent directory to path for imports
from claude_code_analytics.streamlit_app.services import DatabaseService
from claude_code_analytics.streamlit_app.services.format_utils import (
    format_char_count,
    format_duration,
    format_percentage,
)

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

                # Activity & Volume section
                st.markdown("#### Activity & Volume")

                active_time = db_service.get_active_time_for_session(selected_session_id)
                text_vol = db_service.get_text_volume_for_session(selected_session_id)

                # Get message counts from the session summary
                session_summary = None
                for s in sessions:
                    if s.session_id == selected_session_id:
                        session_summary = s
                        break

                # Row 1: Session-level metrics
                ac1, ac2, ac3 = st.columns(3)
                ac1.metric(
                    "Active Time",
                    format_duration(active_time["active_time_seconds"]),
                )
                if session_summary:
                    ac2.metric(
                        "Msgs (U:A)",
                        f"{session_summary.user_message_count} : {session_summary.assistant_message_count}",
                    )

                user_chars = text_vol["user_text_chars"]
                asst_chars = text_vol["assistant_text_chars"]
                tool_out_chars = text_vol["tool_output_chars"]
                total_chars = user_chars + asst_chars + tool_out_chars
                if user_chars > 0:
                    ratio = asst_chars / user_chars
                    ac3.metric("Text Ratio (U:A)", f"1 : {ratio:.1f}")
                else:
                    ac3.metric("Text Ratio (U:A)", "N/A")

                # Row 2: Text volume
                tv1, tv2, tv3 = st.columns(3)
                tv1.metric(
                    "User Text",
                    f"{format_char_count(user_chars)} ({format_percentage(user_chars, total_chars)})",
                )
                tv2.metric(
                    "Asst Text",
                    f"{format_char_count(asst_chars)} ({format_percentage(asst_chars, total_chars)})",
                )
                tv3.metric(
                    "Tool Output",
                    f"{format_char_count(tool_out_chars)} ({format_percentage(tool_out_chars, total_chars)})",
                )

                # Project-level totals
                st.markdown("#### Project Totals")
                proj_metrics = db_service.get_aggregate_activity_metrics(
                    project_id=selected_project_id
                )
                proj_user = proj_metrics["total_user_text_chars"]
                proj_asst = proj_metrics["total_assistant_text_chars"]
                proj_tool_out = proj_metrics["total_tool_output_chars"]
                proj_total = proj_user + proj_asst + proj_tool_out

                pm1, pm2, pm3 = st.columns(3)
                pm1.metric(
                    "Total Active Time",
                    format_duration(proj_metrics["total_active_time_seconds"]),
                )
                pm2.metric(
                    "Avg Active / Session",
                    format_duration(proj_metrics["avg_active_time_per_session"]),
                )
                pm3.metric("Sessions", f"{proj_metrics['session_count']:,}")

                pt1, pt2, pt3, pt4 = st.columns(4)
                pt1.metric(
                    "Total User Text",
                    f"{format_char_count(proj_user)} ({format_percentage(proj_user, proj_total)})",
                )
                pt2.metric(
                    "Total Asst Text",
                    f"{format_char_count(proj_asst)} ({format_percentage(proj_asst, proj_total)})",
                )
                pt3.metric(
                    "Tool Output",
                    f"{format_char_count(proj_tool_out)} ({format_percentage(proj_tool_out, proj_total)})",
                )
                if proj_user > 0:
                    proj_ratio = proj_asst / proj_user
                    pt4.metric("Text Ratio (U:A)", f"1 : {proj_ratio:.1f}")
                else:
                    pt4.metric("Text Ratio (U:A)", "N/A")

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
                width="stretch",
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
        width="stretch",
    )

except Exception as e:
    st.error(f"Error loading projects: {e}")
    import traceback

    with st.expander("Error details"):
        st.code(traceback.format_exc())
