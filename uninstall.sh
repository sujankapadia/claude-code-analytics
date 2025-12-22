#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🗑️  Uninstalling claude-code-analytics..."
echo ""

# Target directories
CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/claude-code-analytics"
CONVERSATIONS_DIR="$HOME/claude-conversations"

# Flags for what to remove
REMOVE_PACKAGE=true
REMOVE_HOOKS=false
REMOVE_CONFIG=false
REMOVE_DATA=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --remove-hooks)
            REMOVE_HOOKS=true
            shift
            ;;
        --remove-config)
            REMOVE_CONFIG=true
            shift
            ;;
        --remove-data)
            REMOVE_DATA=true
            shift
            ;;
        --complete)
            REMOVE_HOOKS=true
            REMOVE_CONFIG=true
            shift
            ;;
        --purge)
            REMOVE_HOOKS=true
            REMOVE_CONFIG=true
            REMOVE_DATA=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./uninstall.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --remove-hooks   Remove hook scripts from ~/.claude/scripts/"
            echo "  --remove-config  Remove configuration from ~/.config/claude-code-analytics/"
            echo "  --remove-data    Remove all conversation data from ~/claude-conversations/"
            echo "  --complete       Remove package, hooks, and config (keeps data)"
            echo "  --purge          Remove everything including data (⚠️  destructive!)"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Default: Only uninstalls the Python package (keeps hooks, config, and data)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show what will be removed
echo "The following will be removed:"
echo ""
if [ "$REMOVE_PACKAGE" = true ]; then
    echo "  ✓ Python package (claude-code-analytics)"
    echo "  ✓ CLI commands (claude-code-analytics, claude-code-import, etc.)"
fi
if [ "$REMOVE_HOOKS" = true ]; then
    echo "  ✓ Hook scripts from ~/.claude/scripts/"
    echo "  ✓ SessionEnd hook from ~/.claude/settings.json"
fi
if [ "$REMOVE_CONFIG" = true ]; then
    echo "  ✓ Configuration from ~/.config/claude-code-analytics/"
fi
if [ "$REMOVE_DATA" = true ]; then
    echo -e "  ${RED}✓ ALL conversation data from ~/claude-conversations/ (⚠️  IRREVERSIBLE!)${NC}"
fi
echo ""

# Confirm if removing data
if [ "$REMOVE_DATA" = true ]; then
    echo -e "${RED}⚠️  WARNING: You are about to delete all conversation data!${NC}"
    echo -e "${RED}   This includes the database and all exported conversations.${NC}"
    echo -e "${RED}   This action CANNOT be undone!${NC}"
    echo ""
    read -p "Are you absolutely sure? Type 'DELETE' to confirm: " CONFIRM
    if [ "$CONFIRM" != "DELETE" ]; then
        echo "Uninstall cancelled."
        exit 0
    fi
fi

# Uninstall Python package
if [ "$REMOVE_PACKAGE" = true ]; then
    echo "📦 Uninstalling Python package..."
    if command -v pip3 &> /dev/null; then
        if pip3 show claude-code-analytics &> /dev/null; then
            pip3 uninstall -y claude-code-analytics
            echo -e "${GREEN}✓ Uninstalled Python package${NC}"
        else
            echo -e "${YELLOW}  Package not installed via pip${NC}"
        fi
    fi

    # Check Homebrew
    if command -v brew &> /dev/null; then
        if brew list claude-code-analytics &> /dev/null 2>&1; then
            brew uninstall claude-code-analytics
            echo -e "${GREEN}✓ Uninstalled Homebrew package${NC}"
        fi
    fi
fi

# Remove hooks
if [ "$REMOVE_HOOKS" = true ]; then
    echo "🪝 Removing hooks..."

    # Remove scripts
    if [ -f "$SCRIPTS_DIR/export-conversation.sh" ]; then
        rm "$SCRIPTS_DIR/export-conversation.sh"
        echo -e "${GREEN}✓ Removed export-conversation.sh${NC}"
    fi

    if [ -f "$SCRIPTS_DIR/pretty-print-transcript.py" ]; then
        rm "$SCRIPTS_DIR/pretty-print-transcript.py"
        echo -e "${GREEN}✓ Removed pretty-print-transcript.py${NC}"
    fi

    # Remove hook from settings.json
    if [ -f "$SETTINGS_FILE" ]; then
        if command -v jq &> /dev/null; then
            # Backup settings
            cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup-uninstall"

            # Remove SessionEnd hook
            jq 'del(.hooks.SessionEnd[] | select(.hooks[]?.command | contains("export-conversation.sh")))' \
                "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"
            mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"

            echo -e "${GREEN}✓ Removed SessionEnd hook from settings.json${NC}"
            echo -e "${GREEN}  Backup saved to settings.json.backup-uninstall${NC}"
        else
            echo -e "${YELLOW}  jq not found - please manually remove hook from $SETTINGS_FILE${NC}"
        fi
    fi
fi

# Remove config
if [ "$REMOVE_CONFIG" = true ]; then
    echo "⚙️  Removing configuration..."
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}✓ Removed configuration directory${NC}"
    fi
fi

# Remove data
if [ "$REMOVE_DATA" = true ]; then
    echo "🗄️  Removing conversation data..."
    if [ -d "$CONVERSATIONS_DIR" ]; then
        # Extra safety check
        if [[ "$CONVERSATIONS_DIR" == *"claude-conversations"* ]]; then
            rm -rf "$CONVERSATIONS_DIR"
            echo -e "${GREEN}✓ Removed all conversation data${NC}"
        else
            echo -e "${RED}✗ Safety check failed - unexpected directory path${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}✅ Uninstall complete!${NC}"
echo ""

# Show what remains
REMAINING=false
if [ "$REMOVE_HOOKS" = false ] && [ -f "$SCRIPTS_DIR/export-conversation.sh" ]; then
    REMAINING=true
fi
if [ "$REMOVE_CONFIG" = false ] && [ -d "$CONFIG_DIR" ]; then
    REMAINING=true
fi
if [ "$REMOVE_DATA" = false ] && [ -d "$CONVERSATIONS_DIR" ]; then
    REMAINING=true
fi

if [ "$REMAINING" = true ]; then
    echo "The following were preserved:"
    if [ "$REMOVE_HOOKS" = false ] && [ -f "$SCRIPTS_DIR/export-conversation.sh" ]; then
        echo "  • Hook scripts in ~/.claude/scripts/"
    fi
    if [ "$REMOVE_CONFIG" = false ] && [ -d "$CONFIG_DIR" ]; then
        echo "  • Configuration in ~/.config/claude-code-analytics/"
    fi
    if [ "$REMOVE_DATA" = false ] && [ -d "$CONVERSATIONS_DIR" ]; then
        echo "  • Conversation data in ~/claude-conversations/"
    fi
    echo ""
    echo "To remove these, run:"
    echo "  ./uninstall.sh --complete    # Remove everything except data"
    echo "  ./uninstall.sh --purge       # Remove everything including data"
fi
