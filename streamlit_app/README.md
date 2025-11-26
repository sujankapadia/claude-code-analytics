# Claude Code Analytics Dashboard

A Streamlit web application for analyzing and visualizing Claude Code conversation transcripts.

## Features

### 📚 Browse Sessions
- View all your projects and conversation sessions
- See metadata like message counts, timestamps, and tool usage
- Filter and search through your conversations

### 💬 View Conversations
- Read full conversation transcripts
- Filter by role (user/assistant)
- View token usage statistics
- Inspect tool uses and results

### 🔬 Run Analysis
- Perform AI-powered analysis on conversations using Gemini 2.5 Flash
- Available analysis types:
  - **Technical Decisions**: Extract decisions, alternatives, and reasoning
  - **Error Patterns**: Identify errors, root causes, and resolutions
- Export analysis results as markdown
- ~87% cheaper than using Claude for analysis

### 📊 Analytics Dashboard
- Token usage statistics and trends
- Tool usage patterns and error rates
- Project and session metrics
- Daily activity charts
- Interactive visualizations

## Architecture

The application follows clean architecture principles with clear separation of concerns:

```
streamlit_app/
├── app.py                  # Main entry point with navigation
├── models/                 # Pydantic data models
│   ├── database_models.py  # Models matching DB schema
│   └── analysis_models.py  # Models for analysis functionality
├── services/              # Business logic layer
│   ├── database_service.py # Database operations
│   └── analysis_service.py # Analysis operations
└── pages/                 # UI pages
    ├── home.py           # Home page
    ├── browser.py        # Session browser
    ├── conversation.py   # Conversation viewer
    ├── analysis.py       # Analysis runner
    └── analytics.py      # Analytics dashboard
```

### Design Principles

1. **Separation of Concerns**: UI (pages) is separated from business logic (services) and data models
2. **Service Layer**: All database operations and analysis logic are encapsulated in service classes
3. **Pydantic Models**: Type-safe data models with validation
4. **Session State**: Used for caching service instances and maintaining navigation state
5. **Modern Streamlit**: Uses `st.Page` and `st.navigation` for better control

## Prerequisites

1. **Database**: You need to have created and populated the SQLite database first:
   ```bash
   # Create database
   python3 scripts/create_database.py

   # Import conversations
   python3 scripts/import_conversations.py
   ```

2. **Google AI API Key**: For running analysis, you need a Google AI API key:
   - Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Set the environment variable:
     ```bash
     export GOOGLE_API_KEY="your-api-key-here"
     ```

## Installation

1. Install dependencies:
   ```bash
   pip install -r streamlit_app/requirements.txt
   ```

2. Set up your Google AI API key (optional, only needed for analysis):
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```

## Running the App

From the project root:

```bash
streamlit run streamlit_app/app.py
```

Or use the provided script:

```bash
./run_dashboard.sh
```

The app will open in your default browser at `http://localhost:8501`.

## Usage

1. **Home**: View quick statistics about your conversations
2. **Browse Sessions**:
   - Select a project to view its sessions
   - Click on a session to see detailed statistics
   - Use the buttons to view the conversation or run analysis
3. **View Conversation**:
   - Read the full conversation transcript
   - Filter by role or search within messages
   - View tool uses and token statistics
4. **Run Analysis**:
   - Select a session and analysis type
   - Run AI-powered analysis using Gemini
   - Download or save results as markdown
5. **Analytics Dashboard**:
   - View aggregated statistics across all your conversations
   - Explore tool usage patterns
   - Analyze daily activity trends

## Development

The application is built with:
- **Streamlit**: Web framework
- **Pydantic**: Data validation and modeling
- **Pandas**: Data manipulation
- **Altair**: Interactive visualizations
- **SQLite**: Database (via Python stdlib)
- **Google Generative AI**: LLM analysis

## Configuration

The app uses sensible defaults:
- Database path: `~/claude-conversations/conversations.db`
- Analysis output: `~/claude-conversations/analyses/`
- Prompts: `./prompts/` (relative to project root)

## Future Enhancements

Potential improvements:
- PII/sensitive data analysis type
- Search interface with FTS5
- MCP server analytics
- Export capabilities (CSV, JSON)
- Custom analysis prompts
- Analysis result caching
