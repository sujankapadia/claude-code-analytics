"""Analysis runner page."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.services import DatabaseService, AnalysisService
from streamlit_app.models import AnalysisType

# Initialize services
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

if "analysis_service" not in st.session_state:
    st.session_state.analysis_service = AnalysisService()

db_service = st.session_state.db_service
analysis_service = st.session_state.analysis_service

st.title("🔬 Run Analysis")

st.markdown("""
Perform AI-powered analysis on your conversation sessions using Gemini 2.5 Flash.
""")

# Check for API key
api_key_configured = analysis_service.api_key is not None

if not api_key_configured:
    st.error("⚠️ Google API key not configured!")
    st.markdown("""
    To use the analysis feature, you need to set your Google AI API key:

    1. Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
    2. Set the `GOOGLE_API_KEY` environment variable
    3. Restart the Streamlit app

    ```bash
    export GOOGLE_API_KEY="your-api-key-here"
    streamlit run streamlit_app/app.py
    ```
    """)
    st.stop()

# Session selector
st.subheader("Select Session")

try:
    # Get recent sessions
    sessions = db_service.get_session_summaries(limit=50)

    if not sessions:
        st.warning("No sessions found. Import conversations first.")
        st.stop()

    # Create session options
    session_options = {
        f"{s.project_name} | {s.session_id[:8]}... | {s.start_time}": s.session_id
        for s in sessions
    }

    # Pre-select if coming from browser
    default_index = 0
    if "selected_session_id" in st.session_state:
        selected_id = st.session_state.selected_session_id
        matching_keys = [k for k, v in session_options.items() if v == selected_id]
        if matching_keys:
            default_index = list(session_options.keys()).index(matching_keys[0])

    selected_session_display = st.selectbox(
        "Choose a session:",
        options=list(session_options.keys()),
        index=default_index,
    )

    selected_session_id = session_options[selected_session_display]

    # Display session info
    session = next(s for s in sessions if s.session_id == selected_session_id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages", session.message_count)
    col2.metric("Tool Uses", session.tool_use_count)
    col3.metric("User Msgs", session.user_message_count)
    col4.metric("Assistant Msgs", session.assistant_message_count)

    st.divider()

    # Analysis type selector
    st.subheader("Select Analysis Type")

    available_types = analysis_service.get_available_analysis_types()

    # Create radio buttons for analysis types
    analysis_type_options = {
        f"**{meta.name}**: {meta.description}": key
        for key, meta in available_types.items()
    }

    selected_display = st.radio(
        "Choose analysis type:",
        options=list(analysis_type_options.keys()),
        index=0,
    )

    selected_analysis_type = AnalysisType(analysis_type_options[selected_display])

    st.divider()

    # Run analysis
    st.subheader("Run Analysis")

    col1, col2 = st.columns([1, 3])

    with col1:
        run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    with col2:
        save_to_file = st.checkbox("Save result to file", value=False)

    if run_button:
        with st.spinner("Analyzing conversation... This may take a minute."):
            try:
                # Run analysis
                result = analysis_service.analyze_session(
                    selected_session_id, selected_analysis_type
                )

                st.success("✅ Analysis complete!")

                # Display token usage
                if result.input_tokens or result.output_tokens:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Input Tokens", f"{result.input_tokens or 0:,}")
                    col2.metric("Output Tokens", f"{result.output_tokens or 0:,}")
                    col3.metric("Model", result.model_name or "N/A")

                st.divider()

                # Display result
                st.markdown("### Analysis Result")
                st.markdown(result.result_text)

                # Save to file if requested
                if save_to_file:
                    output_dir = Path.home() / "claude-conversations" / "analyses"
                    output_dir.mkdir(exist_ok=True)

                    filename = f"{selected_session_id}_{selected_analysis_type.value}.md"
                    output_path = output_dir / filename

                    with open(output_path, "w") as f:
                        f.write(f"# {available_types[selected_analysis_type.value].name}\n\n")
                        f.write(f"**Session:** {selected_session_id}\n")
                        f.write(f"**Date:** {result.created_at}\n\n")
                        f.write("---\n\n")
                        f.write(result.result_text)

                    st.success(f"💾 Saved to: `{output_path}`")

                # Download button
                st.download_button(
                    label="📥 Download as Markdown",
                    data=result.result_text,
                    file_name=f"{selected_session_id}_{selected_analysis_type.value}.md",
                    mime="text/markdown",
                )

            except Exception as e:
                st.error(f"❌ Error running analysis: {e}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())

except Exception as e:
    st.error(f"Error loading sessions: {e}")
    import traceback
    with st.expander("Error details"):
        st.code(traceback.format_exc())
