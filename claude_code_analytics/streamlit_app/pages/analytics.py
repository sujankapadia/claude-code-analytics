"""Analytics dashboard page."""

import altair as alt
import pandas as pd
import streamlit as st

# Add parent directory to path for imports
from claude_code_analytics.streamlit_app.services import DatabaseService
from claude_code_analytics.streamlit_app.services.format_utils import (
    format_char_count,
    format_duration,
)

# Initialize service
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

db_service = st.session_state.db_service

st.title("📊 Analytics Dashboard")

st.markdown(
    """
View aggregated statistics and insights about your Claude Code usage.
"""
)

try:
    # === Tool Usage Statistics ===
    st.subheader("🔧 Tool Usage Statistics")

    tool_usage = db_service.get_tool_usage_summary()

    if not tool_usage:
        st.info("No tool usage data available.")
    else:
        # Create DataFrame
        tools_df = pd.DataFrame([t.model_dump() for t in tool_usage])

        # Display as table
        st.dataframe(
            tools_df,
            column_config={
                "tool_name": st.column_config.TextColumn("Tool", width="medium"),
                "total_uses": st.column_config.NumberColumn("Total Uses"),
                "error_count": st.column_config.NumberColumn("Errors"),
                "error_rate_percent": st.column_config.NumberColumn(
                    "Error Rate %",
                    format="%.2f%%",
                ),
                "sessions_used_in": st.column_config.NumberColumn("Sessions"),
                "first_used": st.column_config.DatetimeColumn("First Used"),
                "last_used": st.column_config.DatetimeColumn("Last Used"),
            },
            hide_index=True,
            width="stretch",
        )

        # Tool usage chart
        st.markdown("#### Tool Usage Distribution")

        chart_data = tools_df[["tool_name", "total_uses"]].head(10)

        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x=alt.X("total_uses:Q", title="Total Uses"),
                y=alt.Y("tool_name:N", sort="-x", title="Tool"),
                color=alt.Color("total_uses:Q", scale=alt.Scale(scheme="viridis"), legend=None),
                tooltip=["tool_name", "total_uses"],
            )
            .properties(height=400)
        )

        st.altair_chart(chart, width="stretch")

    st.divider()

    # === Daily Statistics ===
    st.subheader("📅 Daily Activity")

    days_to_show = st.slider("Days to show:", min_value=7, max_value=90, value=30)

    daily_stats = db_service.get_daily_statistics(days=days_to_show)

    if not daily_stats:
        st.info("No daily statistics available.")
    else:
        daily_df = pd.DataFrame(daily_stats)
        daily_df["date"] = pd.to_datetime(daily_df["date"])

        # Messages over time
        st.markdown("#### Messages Over Time")

        messages_chart = (
            alt.Chart(daily_df)
            .mark_area(opacity=0.7)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("messages:Q", title="Messages"),
                tooltip=["date:T", "messages:Q", "sessions:Q"],
            )
            .properties(height=300)
        )

        st.altair_chart(messages_chart, width="stretch")

        # Token usage over time
        if "input_tokens" in daily_df.columns:
            st.markdown("#### Token Usage Over Time")

            # Prepare data for stacked area chart
            token_df = daily_df[["date", "input_tokens", "output_tokens"]].copy()
            token_df_melted = token_df.melt(
                id_vars=["date"],
                value_vars=["input_tokens", "output_tokens"],
                var_name="token_type",
                value_name="tokens",
            )

            token_chart = (
                alt.Chart(token_df_melted)
                .mark_area(opacity=0.7)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("tokens:Q", title="Tokens"),
                    color=alt.Color(
                        "token_type:N",
                        title="Token Type",
                        scale=alt.Scale(scheme="category10"),
                    ),
                    tooltip=["date:T", "token_type:N", "tokens:Q"],
                )
                .properties(height=300)
            )

            st.altair_chart(token_chart, width="stretch")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        total_sessions = daily_df["sessions"].sum()
        total_messages = daily_df["messages"].sum()
        total_input_tokens = (
            daily_df["input_tokens"].sum() if "input_tokens" in daily_df.columns else 0
        )
        total_output_tokens = (
            daily_df["output_tokens"].sum() if "output_tokens" in daily_df.columns else 0
        )

        col1.metric("Total Sessions", f"{total_sessions:,}")
        col2.metric("Total Messages", f"{total_messages:,}")
        col3.metric("Input Tokens", f"{total_input_tokens:,}")
        col4.metric("Output Tokens", f"{total_output_tokens:,}")

    st.divider()

    # === Project Statistics ===
    st.subheader("📁 Project Statistics")

    projects = db_service.get_project_summaries()

    if not projects:
        st.info("No projects found.")
    else:
        projects_df = pd.DataFrame([p.model_dump() for p in projects])

        # Ensure proper sorting by total_messages
        projects_df = projects_df.sort_values("total_messages", ascending=False)

        st.dataframe(
            projects_df,
            column_config={
                "project_id": None,  # Hide
                "project_name": st.column_config.TextColumn("Project", width="large"),
                "total_sessions": st.column_config.NumberColumn("Sessions"),
                "total_messages": st.column_config.NumberColumn("Messages"),
                "total_tool_uses": st.column_config.NumberColumn("Tool Uses"),
                "first_session": st.column_config.DatetimeColumn("First Session"),
                "last_session": st.column_config.DatetimeColumn("Last Session"),
            },
            hide_index=True,
            width="stretch",
        )

        # Project distribution chart
        st.markdown("#### Messages by Project")

        project_chart_data = projects_df[["project_name", "total_messages"]].head(10)

        project_chart = (
            alt.Chart(project_chart_data)
            .mark_arc(innerRadius=50)
            .encode(
                theta=alt.Theta("total_messages:Q"),
                color=alt.Color("project_name:N", legend=alt.Legend(title="Project")),
                tooltip=["project_name", "total_messages"],
            )
            .properties(height=400)
        )

        st.altair_chart(project_chart, width="stretch")

    st.divider()

    # === Activity & Volume Metrics ===
    st.subheader("Activity & Volume Metrics")

    agg = db_service.get_aggregate_activity_metrics()

    # Row 1: Time metrics
    am1, am2, am3 = st.columns(3)
    am1.metric("Total Active Time", format_duration(agg["total_active_time_seconds"]))
    am2.metric(
        "Avg Active / Session",
        format_duration(agg["avg_active_time_per_session"]),
    )
    am3.metric("Sessions", f"{agg['session_count']:,}")

    # Row 2: Text volume
    vm1, vm2, vm3, vm4 = st.columns(4)
    vm1.metric(
        "Total User Text",
        format_char_count(agg["total_user_text_chars"]),
    )
    vm2.metric(
        "Total Asst Text",
        format_char_count(agg["total_assistant_text_chars"]),
    )
    vm3.metric(
        "Tool Output",
        format_char_count(agg["total_tool_output_chars"]),
    )
    if agg["total_user_text_chars"] > 0:
        ratio = agg["total_assistant_text_chars"] / agg["total_user_text_chars"]
        vm4.metric("Text Ratio (U:A)", f"1 : {ratio:.1f}")
    else:
        vm4.metric("Text Ratio (U:A)", "N/A")

    # Per-project breakdown
    st.markdown("#### Active Time by Project")

    project_rows = []
    for p in projects:
        p_agg = db_service.get_aggregate_activity_metrics(project_id=p.project_id)
        if p_agg["session_count"] > 0:
            project_rows.append(
                {
                    "Project": p.project_name,
                    "Active Time": format_duration(p_agg["total_active_time_seconds"]),
                    "Avg Active": format_duration(p_agg["avg_active_time_per_session"]),
                    "Sessions": p_agg["session_count"],
                    "User Chars": format_char_count(p_agg["total_user_text_chars"]),
                    "Asst Chars": format_char_count(p_agg["total_assistant_text_chars"]),
                    "Tool Output": format_char_count(p_agg["total_tool_output_chars"]),
                    "_active_seconds": p_agg["total_active_time_seconds"],
                }
            )

    if project_rows:
        proj_df = pd.DataFrame(project_rows)
        st.dataframe(
            proj_df.drop(columns=["_active_seconds"]),
            hide_index=True,
            width="stretch",
        )

        # Horizontal bar chart
        chart_df = proj_df[["Project", "_active_seconds"]].copy()
        chart_df = chart_df.rename(columns={"_active_seconds": "Active Seconds"})
        bar_chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X("Active Seconds:Q", title="Active Time (seconds)"),
                y=alt.Y("Project:N", sort="-x", title="Project"),
                color=alt.Color(
                    "Active Seconds:Q",
                    scale=alt.Scale(scheme="viridis"),
                    legend=None,
                ),
                tooltip=["Project", "Active Seconds"],
            )
            .properties(height=max(len(project_rows) * 40, 200))
        )
        st.altair_chart(bar_chart, width="stretch")
    else:
        st.info("No activity data available.")

except Exception as e:
    st.error(f"Error loading analytics: {e}")
    import traceback

    with st.expander("Error details"):
        st.code(traceback.format_exc())
