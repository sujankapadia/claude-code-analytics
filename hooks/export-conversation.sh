#!/bin/bash
# ~/.claude/scripts/export-conversation.sh
# Exports Claude Code conversation on SessionEnd hook
# Creates both JSONL backup and pretty-printed text version

# Load configuration from standard location
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/claude-code-analytics"
ENV_FILE="$CONFIG_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    # Load env vars, handling comments and blank lines
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
fi

# Setup debug logging (use env var or default)
DEBUG_LOG="${CLAUDE_EXPORT_DEBUG_LOG:-$HOME/.claude/export-debug.log}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$DEBUG_LOG"
}

log "========== SessionEnd Hook Triggered =========="

# Read JSON input from stdin
INPUT=$(cat)
log "Raw input received (first 500 chars): ${INPUT:0:500}"

# Extract the transcript path and session info
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
PROJECT_DIR_PATH=$(dirname "$TRANSCRIPT_PATH")

log "Parsed values:"
log "  transcript_path: $TRANSCRIPT_PATH"
log "  session_id: $SESSION_ID"
log "  project_dir: $PROJECT_DIR_PATH"

# Give the file system a moment to flush writes
log "Waiting 1 second for file system flush..."
sleep 1

# Check what files exist in the project directory
log "Files in project directory:"
ls -lt "$PROJECT_DIR_PATH"/*.jsonl 2>/dev/null | head -5 >> "$DEBUG_LOG"

# Find the most recent JSONL file in the project directory
# This handles cases where transcript_path might point to an older file
LATEST_TRANSCRIPT=$(ls -t "$PROJECT_DIR_PATH"/*.jsonl 2>/dev/null | head -1)

if [ -n "$LATEST_TRANSCRIPT" ]; then
    log "Latest transcript found: $LATEST_TRANSCRIPT"
    if [ "$LATEST_TRANSCRIPT" != "$TRANSCRIPT_PATH" ]; then
        log "WARNING: Latest transcript differs from transcript_path!"
        log "  Using latest instead of: $TRANSCRIPT_PATH"
    fi
    TRANSCRIPT_PATH="$LATEST_TRANSCRIPT"
else
    log "WARNING: No transcript files found in $PROJECT_DIR_PATH"
fi

# Verify transcript exists and check its size
if [ ! -f "$TRANSCRIPT_PATH" ]; then
    log "ERROR: Transcript not found at $TRANSCRIPT_PATH"
    exit 1
fi

FILE_SIZE=$(wc -l < "$TRANSCRIPT_PATH")
log "Transcript file size: $FILE_SIZE lines"

# Create backup directory structure (use env var or default)
BACKUP_ROOT="${CLAUDE_CONVERSATIONS_DIR:-$HOME/claude-conversations}"
# Expand ~ if present
BACKUP_ROOT="${BACKUP_ROOT/#\~/$HOME}"
SESSION_NAME=$(basename "$(dirname "$TRANSCRIPT_PATH")")
PROJECT_DIR="$BACKUP_ROOT/$SESSION_NAME"

log "Creating backup directory: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"

# Generate timestamp for filename
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BASE_FILENAME="session-${TIMESTAMP}"

# Copy raw JSONL transcript
JSONL_FILE="$PROJECT_DIR/${BASE_FILENAME}.jsonl"
log "Copying transcript to: $JSONL_FILE"
cp "$TRANSCRIPT_PATH" "$JSONL_FILE"

if [ $? -eq 0 ]; then
    EXPORTED_SIZE=$(wc -l < "$JSONL_FILE")
    log "Successfully copied. Exported file size: $EXPORTED_SIZE lines"
else
    log "ERROR: Failed to copy transcript file"
    exit 1
fi

# Create pretty-printed version
PRETTY_FILE="$PROJECT_DIR/${BASE_FILENAME}.txt"
log "Creating pretty-printed version: $PRETTY_FILE"

# Path to the pretty printer script (adjust if you put it elsewhere)
PRETTY_PRINTER="$HOME/.claude/scripts/pretty-print-transcript.py"

if [ -f "$PRETTY_PRINTER" ]; then
    log "Pretty printer found, executing..."
    python3 "$PRETTY_PRINTER" "$JSONL_FILE" > "$PRETTY_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log "✅ SUCCESS: Conversation exported"
        log "   Location: $PROJECT_DIR/"
        log "   Files: ${BASE_FILENAME}.jsonl and ${BASE_FILENAME}.txt"
        echo "✅ Conversation exported to $PROJECT_DIR/:"
        echo "   JSONL: ${BASE_FILENAME}.jsonl"
        echo "   Text:  ${BASE_FILENAME}.txt"
    else
        log "⚠️  JSONL exported but pretty printing failed"
        log "   Pretty printer exit code: $?"
        echo "⚠️  JSONL exported but pretty printing failed:"
        echo "   Location: $PROJECT_DIR/"
        echo "   Check $PRETTY_PRINTER exists and is executable"
    fi
else
    log "⚠️  Pretty printer not found at: $PRETTY_PRINTER"
    log "   JSONL exported successfully"
    echo "⚠️  JSONL exported (pretty printer not found):"
    echo "   Location: $PROJECT_DIR/"
    echo "   Install pretty printer at: $PRETTY_PRINTER"
fi

log "========== SessionEnd Hook Completed =========="
log ""
