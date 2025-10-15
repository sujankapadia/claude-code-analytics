# claude-code-utils

A collection of utilities and hooks for [Claude Code](https://claude.com/claude-code) that automatically exports and archives your conversation transcripts.

## Overview

The main feature of this toolkit is automatic conversation archiving using Claude Code's SessionEnd hooks. When a Claude Code session ends, your conversation is automatically:
- Exported from the internal JSONL transcript format
- Converted to a human-readable text format
- Organized by project in `~/claude-conversations/`
- Saved in both raw JSONL and formatted text versions

This makes it easy to review past conversations, track your development process, and maintain a searchable archive of your work with Claude.

## Features

- **Automatic export on session end** - No manual intervention required
- **Project-based organization** - Conversations are organized by the project directory where they occurred
- **Dual format storage** - Both raw JSONL (for programmatic access) and pretty-printed text (for human reading)
- **Rich formatting** - The text format includes:
  - Clear visual separation between user and Claude messages
  - Tool commands (e.g., `$ git push`)
  - Tool results with actual output
  - Timestamps
  - Proper handling of multiline content
- **Session resumption handling** - Correctly identifies the latest transcript even when resuming old sessions
- **Debug logging** - Troubleshoot issues with `~/.claude/export-debug.log`

## Installation

### Quick Install (Recommended)

Clone the repository and run the installation script:

```bash
git clone https://github.com/yourusername/claude-code-utils.git
cd claude-code-utils
./install.sh
```

The install script will:
- Create necessary directories (`~/.claude/scripts/`, `~/claude-conversations/`)
- Copy scripts to `~/.claude/scripts/`
- Set executable permissions
- Update `~/.claude/settings.json` with the SessionEnd hook (backs up existing settings)

**Note:** The script uses `jq` for JSON manipulation if available. If not installed, it will provide manual configuration instructions. Install with: `brew install jq` (macOS) or `apt-get install jq` (Linux).

### Manual Installation

If you prefer to install manually:

#### 1. Create the scripts directory

```bash
mkdir -p ~/.claude/scripts
```

#### 2. Copy the scripts

Copy both `export-conversation.sh` and `pretty-print-transcript.py` to `~/.claude/scripts/`:

```bash
cp hooks/export-conversation.sh ~/.claude/scripts/
cp scripts/pretty-print-transcript.py ~/.claude/scripts/
```

#### 3. Make scripts executable

```bash
chmod +x ~/.claude/scripts/export-conversation.sh
chmod +x ~/.claude/scripts/pretty-print-transcript.py
```

#### 4. Configure the SessionEnd hook

Add the following to your `~/.claude/settings.json`:

```json
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
```

If you already have other hooks configured, just add the `SessionEnd` entry to your existing `hooks` object.

#### 5. Create the conversations directory (optional)

The script will create this automatically, but you can create it manually if you prefer:

```bash
mkdir -p ~/claude-conversations
```

## Usage

### Automatic Export

Once configured, conversations are automatically exported when you exit Claude Code. You don't need to do anything!

Your conversations will be saved to:
```
~/claude-conversations/
  └── project-name/
      ├── session-20250113-143022.jsonl
      ├── session-20250113-143022.txt
      ├── session-20250113-151430.jsonl
      └── session-20250113-151430.txt
```

### Manual Export

You can also manually convert existing JSONL transcripts to readable text:

```bash
~/.claude/scripts/pretty-print-transcript.py /path/to/transcript.jsonl output.txt
```

Or use stdin/stdout:

```bash
cat transcript.jsonl | ~/.claude/scripts/pretty-print-transcript.py > output.txt
```

## File Structure

### `export-conversation.sh`

The main hook script that:
- Receives the current working directory and transcript path from Claude Code
- Finds the most recent transcript file (handling session resumption)
- Creates the project-specific directory structure
- Copies the JSONL file
- Calls the pretty-print script to create the readable version
- Logs debug information

### `pretty-print-transcript.py`

Python script that converts JSONL transcripts to readable text:
- Parses the Claude Code JSONL format
- Formats messages with clear visual separation
- Displays tool usage (commands and results)
- Handles both string and structured object tool results
- Adds timestamps and proper text wrapping

### Output Format Example

```
═══════════════════════════════════════════════════════════════
USER (2025-01-13 14:30:22)
───────────────────────────────────────────────────────────────
Can you help me fix the bug in the authentication module?

═══════════════════════════════════════════════════════════════
CLAUDE (2025-01-13 14:30:24)
───────────────────────────────────────────────────────────────
I'll help you fix the authentication bug. Let me first examine the
authentication module to understand the issue.

[Tool: Read]
$ Read file_path=/path/to/auth.js

[Tool Result]
1  function authenticate(user, password) {
2    if (user && password) {
3      return true;
4    }
5  }
```

## Troubleshooting

### Debug Log

If exports aren't working, check the debug log:

```bash
cat ~/.claude/export-debug.log
```

The log includes:
- Hook execution timestamps
- Paths being processed
- File operations
- Any errors encountered

### Common Issues

**Conversations not exporting**
- Verify the hook is configured in `~/.claude/settings.json`
- Check that scripts are executable (`chmod +x`)
- Review `~/.claude/export-debug.log` for errors

**Permission errors**
- Ensure `~/claude-conversations/` is writable
- Verify script files have execute permissions

**Missing Python or bash**
- The scripts require Python 3 and bash
- On macOS/Linux these are typically pre-installed
- Run `python3 --version` and `bash --version` to verify

## Future Ideas

- **SQLite export** - Store conversations in a queryable database
- **Vector embeddings** - Add semantic search across all conversations
- **Web UI** - Browse and search conversations in a browser
- **Conversation statistics** - Track token usage, session length, topics
- **Export formats** - Support Markdown, HTML, PDF output
- **Cloud sync** - Optional backup to cloud storage
- **Privacy filters** - Automatic redaction of sensitive information

## Contributing

Contributions are welcome! Feel free to:
- Report bugs or issues
- Suggest new features
- Submit pull requests
- Share your own utilities and hooks

## License

MIT License - feel free to use and modify as needed.

## Related Resources

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Claude Code Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks)
