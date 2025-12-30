"""Import Data page for Claude Code Analytics."""

import sqlite3
import sys
import time
from pathlib import Path

import streamlit as st

# Add parent directory to path for imports
from claude_code_analytics import config
from claude_code_analytics.streamlit_app.services import DatabaseService

# Import the import logic from scripts
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

import import_conversations
from create_database import create_database
from create_fts_index import create_fts_index

# Initialize service
db_service = DatabaseService()

# Page config
st.title("📥 Import Data")

st.markdown(
    """
Import conversation transcripts from your Claude Code projects into the database for analysis.

The import process:
- Automatically detects new conversations and messages
- Updates existing sessions with new messages (incremental import)
- Never duplicates data
- Preserves all existing analytics
"""
)

st.divider()


def check_for_new_data() -> tuple[bool, int, int]:
    """
    Lightweight check for new data available to import.
    Compares database max message index against file line count.

    Returns:
        Tuple of (has_new_data, new_sessions_count, updated_sessions_count)
    """
    db_path = config.DATABASE_PATH
    source_path = config.CLAUDE_CODE_PROJECTS_DIR

    if not source_path.exists():
        return (False, 0, 0)

    # If database doesn't exist, any JSONL files are "new"
    if not db_path.exists():
        # Quick count of JSONL files
        jsonl_count = sum(1 for _ in source_path.rglob("*.jsonl"))
        return (jsonl_count > 0, jsonl_count, 0)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    new_sessions = 0
    updated_sessions = 0

    try:
        # Get all project directories
        project_dirs = [d for d in source_path.iterdir() if d.is_dir()]

        for project_dir in project_dirs:
            # Find all JSONL files
            jsonl_files = list(project_dir.glob("*.jsonl"))

            for jsonl_file in jsonl_files:
                session_id = jsonl_file.stem

                # First, count actual messages in file (user/assistant roles only)
                file_message_count = 0
                try:
                    with open(jsonl_file) as f:
                        for line in f:
                            if '"message"' in line and (
                                '"role":"user"' in line or '"role":"assistant"' in line
                            ):
                                file_message_count += 1
                except:
                    continue

                # Skip files with no importable messages
                if file_message_count == 0:
                    continue

                # Check if session exists and get max message index
                cursor.execute(
                    """
                    SELECT MAX(message_index)
                    FROM messages
                    WHERE session_id = ?
                """,
                    (session_id,),
                )

                result = cursor.fetchone()
                max_message_index = result[0] if result and result[0] is not None else None

                if max_message_index is None:
                    # Session doesn't exist in database and has messages
                    new_sessions += 1
                else:
                    # Session exists - check if file has more messages
                    db_message_count = max_message_index + 1

                    # If file has more messages than database, it's been updated
                    if file_message_count > db_message_count:
                        updated_sessions += 1

    finally:
        conn.close()

    has_new_data = (new_sessions + updated_sessions) > 0
    return (has_new_data, new_sessions, updated_sessions)


def run_import() -> tuple[int, int, int, int]:
    """
    Run the import process and return statistics.

    Returns:
        Tuple of (projects, sessions, messages, tool_uses) imported
    """
    db_path = config.DATABASE_PATH
    source_path = config.CLAUDE_CODE_PROJECTS_DIR

    # Auto-create database if it doesn't exist
    if not db_path.exists():
        st.info(f"📊 Creating new database at: {db_path}")
        try:
            create_database(str(db_path))
            st.success("✅ Database created successfully")
        except Exception as e:
            st.error(f"❌ Failed to create database: {e}")
            return (0, 0, 0, 0)

    if not source_path.exists():
        st.error(f"❌ Source directory not found: {source_path}")
        return (0, 0, 0, 0)

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # Find all project directories
        project_dirs = [d for d in source_path.iterdir() if d.is_dir()]

        if not project_dirs:
            st.warning("⚠️ No project directories found")
            return (0, 0, 0, 0)

        # Import each project
        total_projects = 0
        total_sessions = 0
        total_messages = 0
        total_tool_uses = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, project_dir in enumerate(project_dirs):
            project_name = import_conversations.decode_project_name(project_dir.name)
            status_text.text(f"Importing: {project_name}")

            try:
                sessions, messages, tool_uses = import_conversations.import_project(
                    project_dir, conn
                )

                if sessions > 0:
                    total_projects += 1
                    total_sessions += sessions
                    total_messages += messages
                    total_tool_uses += tool_uses

            except Exception as e:
                st.warning(f"⚠️ Error importing {project_name}: {e}")
                continue

            # Update progress
            progress_bar.progress((idx + 1) / len(project_dirs))

        # Commit changes
        conn.commit()
        conn.close()

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

        # Rebuild FTS index if any data was imported
        if total_messages > 0:
            status_text.text("🔍 Rebuilding search index...")
            try:
                create_fts_index(str(db_path))
                status_text.empty()
            except Exception as e:
                st.warning(f"⚠️ Failed to rebuild search index: {e}")

        return (total_projects, total_sessions, total_messages, total_tool_uses)

    except Exception as e:
        st.error(f"❌ Fatal error during import: {e}")
        conn.rollback()
        return (0, 0, 0, 0)
    finally:
        if conn:
            conn.close()


# Check for new data
with st.spinner("Checking for new data..."):
    start_time = time.time()
    has_new_data, new_sessions, updated_sessions = check_for_new_data()
    elapsed_time = time.time() - start_time

# Display status notification
if has_new_data:
    total_affected = new_sessions + updated_sessions
    st.info(
        f"✨ **New data detected:** {total_affected} session(s) ready to import ({new_sessions} new, {updated_sessions} updated)"
    )
else:
    st.success("✅ **Database is up to date** - No new data to import")

# Display check performance
st.caption(f"⏱️ Detection check completed in {elapsed_time:.2f}s")

st.divider()

# Import button
if st.button("🚀 Run Import", type="primary", disabled=not has_new_data):
    with st.spinner("Importing conversations..."):
        projects, sessions, messages, tool_uses = run_import()

    # Display results
    st.divider()
    st.subheader("📊 Import Results")

    if sessions > 0:
        st.success("✅ **Import completed successfully!**")

        st.markdown("**Imported in this run:**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Projects", projects)
        col2.metric("Sessions", sessions)
        col3.metric("Messages", f"{messages:,}")
        col4.metric("Tool Uses", f"{tool_uses:,}")

        st.info("💡 Refresh the page or navigate away to update the detection status")
    else:
        st.info("ℹ️ No new data was imported")

# Show current database stats
st.divider()
st.subheader("📈 Current Database Statistics")

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
    st.info("Make sure you've created the database first.")
