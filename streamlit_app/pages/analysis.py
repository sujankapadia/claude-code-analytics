"""Analysis runner page."""

import streamlit as st
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config
from streamlit_app.services import DatabaseService, AnalysisService, OpenRouterProvider
from streamlit_app.models import AnalysisType


def get_git_commit_id() -> str:
    """Get current git commit ID."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"
    except Exception:
        return "unknown"


def format_analysis_with_metadata(
    result_text: str,
    analysis_type: str,
    analysis_name: str,
    session_id: str,
    project_name: str,
    model_name: str,
    provider_name: str,
    input_tokens: int,
    output_tokens: int,
) -> str:
    """Format analysis result with traceability metadata."""
    git_commit = get_git_commit_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata = f"""# {analysis_name}

## Traceability Information

- **Project:** {project_name}
- **Session ID:** `{session_id}`
- **Analysis Type:** `{analysis_type}`
- **Generated:** {timestamp}
- **LLM Provider:** {provider_name}
- **Model:** `{model_name}`
- **Input Tokens:** {input_tokens:,}
- **Output Tokens:** {output_tokens:,}
- **Tool Version:** `{git_commit[:8]}`
- **Full Commit:** `{git_commit}`

---

"""
    return metadata + result_text

# Initialize services
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

if "analysis_service" not in st.session_state:
    st.session_state.analysis_service = AnalysisService()

db_service = st.session_state.db_service
analysis_service = st.session_state.analysis_service

st.title("🔬 Run Analysis")

st.markdown("""
Perform AI-powered analysis on your conversation sessions using state-of-the-art LLMs.
""")

# Check for API key
api_key_configured = analysis_service.api_key is not None

if not api_key_configured:
    st.error("⚠️ LLM API key not configured!")
    st.markdown("""
    To use the analysis feature, you need to set an API key:

    **Option 1: OpenRouter (Recommended)** - Access 300+ models
    1. Get an API key from [OpenRouter](https://openrouter.ai/keys)
    2. Set the `OPENROUTER_API_KEY` environment variable
    3. Restart the Streamlit app

    ```bash
    export OPENROUTER_API_KEY="sk-or-your-key-here"
    streamlit run streamlit_app/app.py
    ```

    **Option 2: Google Gemini (Direct)**
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

    # Show custom prompt text area if CUSTOM is selected
    custom_prompt = None
    if selected_analysis_type == AnalysisType.CUSTOM:
        st.markdown("### Enter Your Analysis Prompt")
        st.markdown("_The conversation transcript will be automatically appended to your prompt._")
        custom_prompt = st.text_area(
            "Prompt:",
            height=200,
            placeholder="Example: Analyze this conversation and identify the main topics discussed, key insights shared, and any action items mentioned.",
            help="Enter your analysis instructions. The transcript will be automatically added after your prompt."
        )

    st.divider()

    # Model selector (only show if using OpenRouter)
    selected_model = None
    if isinstance(analysis_service.provider, OpenRouterProvider):
        st.subheader("Model Selection")

        # Radio button to choose between quick select and browse all
        model_selection_mode = st.radio(
            "Choose model selection method:",
            ["Quick Select (13 curated models)", "Browse All Models (300+)"],
            index=0,
            help="Quick Select shows recommended models. Browse All lets you choose from the full catalog."
        )

        if model_selection_mode == "Quick Select (13 curated models)":
            # Quick select dropdown
            model_options = {label: model_id for label, model_id in OpenRouterProvider.QUICK_SELECT_MODELS}

            selected_model_label = st.selectbox(
                "Choose model:",
                options=list(model_options.keys()),
                index=4,  # Default to DeepSeek V3.2
                help="Curated list of newest premium models from 2025."
            )

            selected_model = model_options[selected_model_label]

        else:
            # Browse all models mode
            import pandas as pd

            # Use session state to cache the models
            if "all_openrouter_models" not in st.session_state:
                st.session_state.all_openrouter_models = None

            # Auto-load models when switching to this mode
            if st.session_state.all_openrouter_models is None:
                with st.spinner("Fetching models from OpenRouter..."):
                    try:
                        all_models = OpenRouterProvider.fetch_all_models()

                        # Filter for text generation models
                        text_models = [
                            m for m in all_models
                            if 'text' in m['architecture']['output_modalities']
                            and m['pricing']['prompt'] != '0'
                        ]

                        # Sort by newest first
                        text_models.sort(key=lambda m: m['created'], reverse=True)

                        # Store in session state (limit to 100 for performance)
                        st.session_state.all_openrouter_models = text_models[:100]

                    except Exception as e:
                        st.error(f"❌ Failed to fetch models: {e}")
                        st.session_state.all_openrouter_models = []

            # Display models if loaded
            if st.session_state.all_openrouter_models:
                text_models = st.session_state.all_openrouter_models
                st.success(f"✅ Loaded {len(text_models)} models")

                # Create dataframe
                df_data = []
                for m in text_models:
                    prompt_price = float(m['pricing']['prompt']) * 1_000_000
                    completion_price = float(m['pricing']['completion']) * 1_000_000
                    df_data.append({
                        'Model ID': m['id'],
                        'Name': m['name'],
                        'Input $/1M': f"${prompt_price:.2f}",
                        'Output $/1M': f"${completion_price:.2f}",
                        'Context': f"{m['context_length']:,}",
                    })

                df = pd.DataFrame(df_data)

                st.markdown("**Select a model (click the checkbox):**")

                # Use dataframe with selection mode
                event = st.dataframe(
                    df,
                    use_container_width=True,
                    height=400,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                )

                # Check if a row was selected
                if event.selection and event.selection.rows:
                    selected_row_idx = event.selection.rows[0]
                    selected_model = text_models[selected_row_idx]['id']
                    selected_model_name = text_models[selected_row_idx]['name']

                    st.success(f"✅ Selected: **{selected_model_name}**")
                    st.code(selected_model, language="text")
                else:
                    st.warning("⚠️ Please select a model from the table above by clicking its checkbox.")
                    # Don't allow analysis to run without selection
                    selected_model = None

        st.divider()

    # Run analysis
    st.subheader("Run Analysis")

    col1, col2 = st.columns([1, 3])

    with col1:
        run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    with col2:
        save_to_file = st.checkbox("Save result to file", value=False)

    if run_button:
        # Validate custom prompt if CUSTOM type is selected
        if selected_analysis_type == AnalysisType.CUSTOM:
            if not custom_prompt or not custom_prompt.strip():
                st.error("❌ Please enter a custom prompt for analysis.")
                st.stop()

        with st.spinner("Analyzing conversation... This may take a minute."):
            try:
                # Run analysis
                result = analysis_service.analyze_session(
                    selected_session_id,
                    selected_analysis_type,
                    custom_prompt=custom_prompt,
                    model=selected_model,
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

                # Prepare formatted output with metadata
                provider_name = type(analysis_service.provider).__name__.replace("Provider", "")
                formatted_result = format_analysis_with_metadata(
                    result_text=result.result_text,
                    analysis_type=selected_analysis_type.value,
                    analysis_name=available_types[selected_analysis_type.value].name,
                    session_id=selected_session_id,
                    project_name=session.project_name,
                    model_name=result.model_name or "unknown",
                    provider_name=provider_name,
                    input_tokens=result.input_tokens or 0,
                    output_tokens=result.output_tokens or 0,
                )

                # Generate unique filename with timestamp
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Sanitize project name for filename (remove special chars)
                safe_project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in session.project_name)
                filename = f"{safe_project_name}_{selected_analysis_type.value}_{timestamp_str}.md"

                # Save to file if requested
                if save_to_file:
                    output_dir = config.ANALYSIS_OUTPUT_DIR
                    output_dir.mkdir(parents=True, exist_ok=True)

                    output_path = output_dir / filename

                    with open(output_path, "w") as f:
                        f.write(formatted_result)

                    st.success(f"💾 Saved to: `{output_path}`")

                # Download button
                st.download_button(
                    label="📥 Download as Markdown",
                    data=formatted_result,
                    file_name=filename,
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
