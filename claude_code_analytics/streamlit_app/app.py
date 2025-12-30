"""
Claude Code Analytics Dashboard

A Streamlit application for analyzing Claude Code conversation transcripts.
"""

import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Claude Code Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling to match landing page
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap" rel="stylesheet">

    <style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap');

    /* Root variables matching landing page */
    :root {
        --bg-primary: #0a0e1a;
        --bg-secondary: #131824;
        --bg-tertiary: #1a2234;
        --accent-primary: #00d9ff;
        --accent-secondary: #7c3aed;
        --accent-tertiary: #f59e0b;
        --text-primary: #e2e8f0;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --border-color: rgba(148, 163, 184, 0.1);
        --glow-primary: rgba(0, 217, 255, 0.3);
        --glow-secondary: rgba(124, 58, 237, 0.2);
    }

    /* Main app styling */
    .stApp {
        font-family: 'Sora', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg-primary);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--text-secondary);
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--text-primary);
    }

    /* Code blocks with terminal styling */
    code {
        font-family: 'JetBrains Mono', monospace;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 0.2rem 0.4rem;
        color: var(--accent-primary);
    }

    pre {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1rem;
    }

    pre code {
        background: transparent;
        border: none;
        padding: 0;
    }

    /* Buttons with gradient */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
        color: var(--bg-primary);
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-family: 'Sora', sans-serif;
        transition: all 0.3s ease;
        box-shadow: 0 0 20px var(--glow-primary);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 30px var(--glow-primary);
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        font-family: 'Sora', sans-serif;
    }

    .stDownloadButton > button:hover {
        border-color: var(--accent-primary);
        background: var(--bg-secondary);
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        background: var(--bg-secondary);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        font-family: 'Sora', sans-serif;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--accent-primary);
        box-shadow: 0 0 0 1px var(--accent-primary);
    }

    /* Metrics / Stats cards */
    [data-testid="stMetricValue"] {
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary);
        font-family: 'Sora', sans-serif;
    }

    /* Cards and containers */
    [data-testid="stExpander"] {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
    }

    [data-testid="stExpander"]:hover {
        border-color: var(--accent-primary);
        box-shadow: 0 4px 12px rgba(0, 217, 255, 0.1);
    }

    /* Dataframes and tables */
    .stDataFrame {
        font-family: 'JetBrains Mono', monospace;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'Sora', sans-serif;
        font-weight: 600;
        color: var(--text-secondary);
        border-radius: 8px 8px 0 0;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent-primary);
        border-bottom: 2px solid var(--accent-primary);
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        border-radius: 12px;
        border: 1px solid var(--border-color);
        font-family: 'Sora', sans-serif;
    }

    /* Success messages */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1);
        border-color: rgba(16, 185, 129, 0.3);
    }

    /* Info messages */
    .stInfo {
        background: rgba(0, 217, 255, 0.1);
        border-color: rgba(0, 217, 255, 0.3);
    }

    /* Warning messages */
    .stWarning {
        background: rgba(245, 158, 11, 0.1);
        border-color: rgba(245, 158, 11, 0.3);
    }

    /* Error messages */
    .stError {
        background: rgba(239, 68, 68, 0.1);
        border-color: rgba(239, 68, 68, 0.3);
    }

    /* Plotly charts background */
    .js-plotly-plot {
        background: var(--bg-secondary);
        border-radius: 12px;
        padding: 1rem;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: var(--accent-primary);
    }

    /* Links */
    a {
        color: var(--accent-primary);
        text-decoration: none;
    }

    a:hover {
        color: var(--accent-secondary);
        text-decoration: underline;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--accent-primary);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-secondary);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Define pages
about_page = st.Page(
    "pages/about.py",
    title="About",
    icon="ℹ️",
)

browser_page = st.Page(
    "pages/browser.py",
    title="Browse Sessions",
    icon="📚",
    default=True,
)

analysis_page = st.Page(
    "pages/analysis.py",
    title="Run Analysis",
    icon="🔬",
)

analytics_page = st.Page(
    "pages/analytics.py",
    title="Analytics Dashboard",
    icon="📊",
)

conversation_page = st.Page(
    "pages/conversation.py",
    title="View Conversation",
    icon="💬",
)

import_data_page = st.Page(
    "pages/import_data.py",
    title="Import Data",
    icon="📥",
)

search_page = st.Page(
    "pages/search.py",
    title="Search",
    icon="🔍",
)

# Build navigation
pg = st.navigation(
    {
        "Browse": [browser_page, conversation_page, search_page],
        "Analysis": [analysis_page, analytics_page],
        "Data": [import_data_page],
        "Info": [about_page],
    }
)

# Run the selected page
pg.run()
