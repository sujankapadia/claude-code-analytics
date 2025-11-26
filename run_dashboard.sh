#!/bin/bash
# Launch Claude Code Analytics Dashboard

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit is not installed."
    echo "Install it with: pip install -r streamlit_app/requirements.txt"
    exit 1
fi

# Check if database exists
DB_PATH="$HOME/claude-conversations/conversations.db"
if [ ! -f "$DB_PATH" ]; then
    echo "⚠️  Database not found at $DB_PATH"
    echo "Run these scripts first:"
    echo "  1. python3 scripts/create_database.py"
    echo "  2. python3 scripts/import_conversations.py"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for API key
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY environment variable not set."
    echo "Analysis features will be disabled."
    echo "Get your key from: https://aistudio.google.com/app/apikey"
    echo ""
fi

# Launch Streamlit
echo "🚀 Launching Claude Code Analytics Dashboard..."
echo ""

streamlit run streamlit_app/app.py
