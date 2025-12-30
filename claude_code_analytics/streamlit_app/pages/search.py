"""Search page for Claude Code Analytics."""

from datetime import datetime, timedelta

import streamlit as st

# Add parent directory to path for imports
from claude_code_analytics import config
from claude_code_analytics.streamlit_app.services import DatabaseService

# Initialize service
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

db_service = st.session_state.db_service

st.title("🔍 Search")

st.markdown(
    """
Search across all your conversations, messages, and tool usage.
"""
)

# Search input
search_query = st.text_input(
    "Search", placeholder="Enter search terms...", key="search_input", label_visibility="collapsed"
)

# Scope selector
scope = st.radio(
    "Search in:",
    options=["All", "Messages", "Tool Inputs", "Tool Results"],
    horizontal=True,
    key="search_scope",
)

st.divider()

# Filters
with st.expander("Filters", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        # Project filter
        try:
            projects = db_service.get_all_projects()
            project_options = ["All Projects"] + [p.project_name for p in projects]
            selected_project = st.selectbox("Project", project_options)

            # Get project_id if specific project selected
            project_id = None
            if selected_project != "All Projects":
                project_id = next(
                    p.project_id for p in projects if p.project_name == selected_project
                )
        except Exception as e:
            st.error(f"Error loading projects: {e}")
            project_id = None

    with col2:
        # Date range filter
        date_range = st.selectbox(
            "Date Range",
            options=["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom"],
        )

        start_date = None
        end_date = None

        if date_range == "Last 7 Days":
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
        elif date_range == "Last 30 Days":
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
        elif date_range == "Last 90 Days":
            start_date = (datetime.now() - timedelta(days=90)).isoformat()
        elif date_range == "Custom":
            col_start, col_end = st.columns(2)
            with col_start:
                start = st.date_input("From")
                if start:
                    start_date = datetime.combine(start, datetime.min.time()).isoformat()
            with col_end:
                end = st.date_input("To")
                if end:
                    end_date = datetime.combine(end, datetime.max.time()).isoformat()

    with col3:
        # Tool name filter (only show if searching tools)
        tool_name = None
        selected_tool = "All Tools"  # Default
        if scope in ["All", "Tool Inputs", "Tool Results"]:
            try:
                tool_names = db_service.get_unique_tool_names()
                tool_options = ["All Tools"] + tool_names
                selected_tool = st.selectbox("Tool", tool_options)

                if selected_tool != "All Tools":
                    tool_name = selected_tool
            except Exception as e:
                st.error(f"Error loading tools: {e}")

# Pagination controls at top
if "search_page" not in st.session_state:
    st.session_state.search_page = 0

RESULTS_PER_PAGE = config.SEARCH_RESULTS_PER_PAGE

# Reset page when search query or filters change (BEFORE executing search)
if "last_search_state" not in st.session_state:
    st.session_state.last_search_state = {}

# Build current search state
current_state = {
    "query": search_query,
    "scope": scope,
    "project": selected_project,
    "date_range": date_range,
    "tool": selected_tool,
}

# Reset page if search state changed
if current_state != st.session_state.last_search_state:
    st.session_state.search_page = 0
    st.session_state.last_search_state = current_state

# Execute search
if search_query:
    with st.spinner("Searching..."):
        try:
            # Use SQL-based session-grouped search with pagination
            search_result = db_service.search_grouped_by_session(
                query=search_query,
                scope=scope,
                project_id=project_id,
                tool_name=tool_name,
                start_date=start_date,
                end_date=end_date,
                sessions_per_page=3,
                page=st.session_state.search_page,
            )

            results_by_session = search_result["results_by_session"]
            has_more = search_result["has_more"]
            total_unique_sessions = search_result["total_sessions"]

            # Calculate total results on page
            total_results_on_page = sum(len(results) for results in results_by_session.values())

            # Display result count
            st.divider()
            unique_sessions_on_page = len(results_by_session)

            if total_results_on_page > 0:
                # Show page info and more indicator
                page_num = st.session_state.search_page + 1
                if has_more:
                    st.success(
                        f"**Showing {total_results_on_page} results from {unique_sessions_on_page} session(s) on page {page_num}** · Total: {total_unique_sessions} session(s) with matches"
                    )
                else:
                    if st.session_state.search_page == 0:
                        st.success(
                            f"**{total_results_on_page} results** across **{total_unique_sessions} session(s)**"
                        )
                    else:
                        st.success(
                            f"**Showing {total_results_on_page} results from {unique_sessions_on_page} session(s) on page {page_num}** (last page)"
                        )
            else:
                st.info("No results found. Try different search terms or adjust filters.")

            # Display results grouped by session
            if results_by_session:
                for session_id, session_results in results_by_session.items():
                    # Get session info from first result
                    first_result = session_results[0]
                    project_name = first_result.get("project_name", "Unknown")

                    # Format session header
                    st.markdown(f"### Session: `{session_id[:8]}...` | {project_name}")
                    st.caption(f"{len(session_results)} match(es) in this session")

                    # Display each match in the session
                    for result in session_results:
                        with st.container():
                            # Determine result type and display accordingly
                            if scope == "Messages" or result.get("result_type") == "message":
                                role = result.get("role", result.get("detail", "unknown"))
                                timestamp = result.get("timestamp", "")
                                snippet = result.get("snippet", result.get("content", ""))
                                message_index = result.get("message_index", 0)

                                # Role badge
                                role_color = "blue" if role == "user" else "green"
                                st.markdown(f":{role_color}[**{role.title()}**] · {timestamp}")

                                # Snippet with HTML markup
                                st.markdown(snippet, unsafe_allow_html=True)

                                # Action buttons
                                col_view, col_analyze = st.columns([3, 1])
                                with col_view:
                                    # View in conversation link
                                    view_url = f"conversation?session_id={session_id}&message_index={message_index}"
                                    st.markdown(f"[View in Conversation →]({view_url})")
                                with col_analyze:
                                    # Analyze with context button
                                    analyze_url = f"analysis?session_id={session_id}&message_index={message_index}"
                                    st.markdown(f"[🔬 Analyze]({analyze_url})")

                            else:
                                # Tool result
                                result_type = result.get("result_type", "tool")
                                tool_name = result.get("tool_name", result.get("detail", "unknown"))
                                timestamp = result.get("timestamp", "")
                                content = (
                                    result.get("tool_input")
                                    or result.get("tool_result")
                                    or result.get("matched_content", "")
                                )
                                message_index = result.get("message_index", 0)

                                # Tool badge
                                st.markdown(
                                    f":orange[**{tool_name}**] · {result_type.replace('_', ' ').title()} · {timestamp}"
                                )

                                # Content preview (truncate if too long)
                                preview = content[:200] + "..." if len(content) > 200 else content
                                st.code(preview, language="text")

                                # Action buttons
                                col_view, col_analyze = st.columns([3, 1])
                                with col_view:
                                    # View in conversation link
                                    view_url = f"conversation?session_id={session_id}&message_index={message_index}"
                                    st.markdown(f"[View in Conversation →]({view_url})")
                                with col_analyze:
                                    # Analyze with context button
                                    analyze_url = f"analysis?session_id={session_id}&message_index={message_index}"
                                    st.markdown(f"[🔬 Analyze]({analyze_url})")

                            st.divider()

                # Pagination controls
                col1, col2, col3 = st.columns([1, 2, 1])

                with col1:
                    if st.session_state.search_page > 0:
                        if st.button("← Previous"):
                            st.session_state.search_page -= 1
                            st.rerun()

                with col2:
                    st.markdown(
                        f"<center>Page {st.session_state.search_page + 1}</center>",
                        unsafe_allow_html=True,
                    )

                with col3:
                    if has_more and st.button("Next →"):
                        st.session_state.search_page += 1
                        st.rerun()

        except Exception as e:
            st.error(f"Search error: {e}")
            import traceback

            with st.expander("Error details"):
                st.code(traceback.format_exc())
else:
    st.info("👆 Enter a search term to get started")

# MCP Analysis Section
st.divider()
st.markdown("## 🔌 MCP Tool Analysis")

with st.expander("View MCP Tool Usage Statistics", expanded=False):
    try:
        mcp_stats = db_service.get_mcp_tool_stats()

        if mcp_stats["total_uses"] == 0:
            st.info("No MCP tool usage found in your conversations.")
        else:
            # Overview metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total MCP Uses", f"{mcp_stats['total_uses']:,}")
            with col2:
                st.metric("Sessions with MCP", mcp_stats["total_sessions"])

            st.divider()

            # Two-column layout for servers and tools
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### By MCP Server")
                if mcp_stats["by_server"]:
                    for server in mcp_stats["by_server"]:
                        server_name = server["mcp_server"]
                        uses = server["total_uses"]
                        sessions = server["session_count"]

                        # Create clickable link that filters search
                        st.markdown(
                            f"""
                        **{server_name}**
                        - {uses:,} uses across {sessions} session(s)
                        """
                        )
                else:
                    st.info("No MCP servers detected.")

            with col2:
                st.markdown("### Top MCP Tools")
                if mcp_stats["by_tool"]:
                    # Show top 10 tools
                    for i, tool in enumerate(mcp_stats["by_tool"][:10], 1):
                        tool_name = tool["tool_name"]
                        uses = tool["use_count"]
                        sessions = tool["session_count"]

                        # Extract display name (remove mcp__ prefix for readability)
                        display_name = tool_name.replace("mcp__", "").replace("__", " → ")

                        st.markdown(
                            f"""
                        **{i}. {display_name}**
                        {uses:,} uses in {sessions} session(s)
                        """
                        )

                        if i >= 10:
                            break
                else:
                    st.info("No MCP tools detected.")

            # Full tool list in expandable section
            if len(mcp_stats["by_tool"]) > 10:
                st.divider()
                with st.expander(f"Show all {len(mcp_stats['by_tool'])} MCP tools"):
                    for tool in mcp_stats["by_tool"]:
                        tool_name = tool["tool_name"]
                        uses = tool["use_count"]
                        sessions = tool["session_count"]
                        display_name = tool_name.replace("mcp__", "").replace("__", " → ")

                        st.markdown(f"**{display_name}**: {uses:,} uses in {sessions} session(s)")

    except Exception as e:
        st.error(f"Error loading MCP statistics: {e}")
        import traceback

        with st.expander("Error details"):
            st.code(traceback.format_exc())
