#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Installing claude-code-utils..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Target directories
CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
CONVERSATIONS_DIR="$HOME/claude-conversations"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/claude-code-analytics"
CONFIG_FILE="$CONFIG_DIR/.env"

# Check for required commands
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is required but not installed.${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed. Will use manual JSON editing.${NC}"
    echo -e "${YELLOW}For better JSON handling, install jq: brew install jq${NC}"
    USE_JQ=false
else
    USE_JQ=true
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$CONVERSATIONS_DIR"
mkdir -p "$CONFIG_DIR"

# Copy scripts
echo "📋 Copying scripts..."
cp "$SCRIPT_DIR/hooks/export-conversation.sh" "$SCRIPTS_DIR/"
cp "$SCRIPT_DIR/scripts/pretty-print-transcript.py" "$SCRIPTS_DIR/"

# Make scripts executable
echo "🔧 Setting permissions..."
chmod +x "$SCRIPTS_DIR/export-conversation.sh"
chmod +x "$SCRIPTS_DIR/pretty-print-transcript.py"

# Set up configuration file
echo "⚙️  Setting up configuration..."
if [ ! -f "$CONFIG_FILE" ]; then
    cp "$SCRIPT_DIR/.env.example" "$CONFIG_FILE"
    echo -e "${GREEN}✓ Created configuration file at $CONFIG_FILE${NC}"
    echo -e "${YELLOW}  Edit this file to customize settings (optional)${NC}"
else
    echo -e "${GREEN}✓ Configuration file already exists at $CONFIG_FILE${NC}"
fi

# Configure settings.json
echo "⚙️  Configuring settings.json..."

HOOK_COMMAND="bash ~/.claude/scripts/export-conversation.sh"

if [ -f "$SETTINGS_FILE" ]; then
    # Backup existing settings
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
    echo -e "${GREEN}✓ Backed up existing settings to $SETTINGS_FILE.backup${NC}"

    if [ "$USE_JQ" = true ]; then
        # Use jq to merge the hook with proper structure
        tmp_file=$(mktemp)
        jq --arg cmd "$HOOK_COMMAND" '.hooks.SessionEnd = [{"matcher": "", "hooks": [{"type": "command", "command": $cmd}]}]' "$SETTINGS_FILE" > "$tmp_file"
        mv "$tmp_file" "$SETTINGS_FILE"
        echo -e "${GREEN}✓ Updated SessionEnd hook in settings.json${NC}"
    else
        # Manual JSON editing
        echo -e "${YELLOW}Please manually add the following to your $SETTINGS_FILE:${NC}"
        echo ""
        echo -e "${YELLOW}  \"hooks\": {${NC}"
        echo -e "${YELLOW}    \"SessionEnd\": [${NC}"
        echo -e "${YELLOW}      {${NC}"
        echo -e "${YELLOW}        \"matcher\": \"\",${NC}"
        echo -e "${YELLOW}        \"hooks\": [${NC}"
        echo -e "${YELLOW}          {${NC}"
        echo -e "${YELLOW}            \"type\": \"command\",${NC}"
        echo -e "${YELLOW}            \"command\": \"$HOOK_COMMAND\"${NC}"
        echo -e "${YELLOW}          }${NC}"
        echo -e "${YELLOW}        ]${NC}"
        echo -e "${YELLOW}      }${NC}"
        echo -e "${YELLOW}    ]${NC}"
        echo -e "${YELLOW}  }${NC}"
        echo ""
    fi
else
    # Create new settings file
    cat > "$SETTINGS_FILE" <<'EOF'
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/scripts/export-conversation.sh"
          }
        ]
      }
    ]
  }
}
EOF
    echo -e "${GREEN}✓ Created new settings.json with SessionEnd hook${NC}"
fi

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "Your Claude Code conversations will now be automatically exported to:"
echo "  $CONVERSATIONS_DIR"
echo ""
echo "Files installed:"
echo "  $SCRIPTS_DIR/export-conversation.sh"
echo "  $SCRIPTS_DIR/pretty-print-transcript.py"
echo ""
echo "Configuration:"
echo "  $CONFIG_FILE"
echo ""
echo "Debug logs available at:"
echo "  $CLAUDE_DIR/export-debug.log"
echo ""

if [ "$USE_JQ" = false ]; then
    echo -e "${YELLOW}⚠️  Please manually update your settings.json (see above)${NC}"
    echo ""
fi

echo "Next steps:"
echo ""
echo "Required for basic features (export, browse, search):"
echo "  1. Create database: python3 scripts/create_database.py"
echo "  2. Import conversations: python3 scripts/import_conversations.py"
echo "  3. Launch dashboard: ./run_dashboard.sh"
echo ""
echo "Required for AI analysis features:"
echo "  4. Edit configuration: $CONFIG_FILE"
echo "     Set OPENROUTER_API_KEY or GOOGLE_API_KEY"
echo "     (Get keys from https://openrouter.ai/keys or https://aistudio.google.com/app/apikey)"
echo ""
echo "Optional customization:"
echo "  - Edit $CONFIG_FILE to customize:"
echo "    - Data directories"
echo "    - Pagination settings"
echo "    - Search results per page"
echo "    - Display settings"
echo ""
echo "To test the export hook, start a new Claude Code session and exit it."
echo "You should see a new conversation file in $CONVERSATIONS_DIR"
