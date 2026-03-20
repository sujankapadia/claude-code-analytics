# Manual Installation

[Back to README](../README.md)

If you need to install manually or want to understand what the installer does, follow these steps.

## 1. Create directories

```bash
mkdir -p ~/.claude/scripts
mkdir -p ~/claude-conversations
```

## 2. Copy scripts

```bash
cp hooks/export-conversation.sh ~/.claude/scripts/
cp scripts/pretty-print-transcript.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/export-conversation.sh
chmod +x ~/.claude/scripts/pretty-print-transcript.py
```

## 3. Configure hook

Add to `~/.claude/settings.json`:

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

If you have existing hooks, merge the `SessionEnd` entry into your existing `hooks` object.

## 4. Install Python package and build frontend

```bash
# From the repository directory
pip install -e .

# Build the React frontend
cd frontend && npm install && npm run build && cd ..
```
