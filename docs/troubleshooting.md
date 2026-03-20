# Troubleshooting

[Back to README](../README.md)

## Conversations not exporting

Check the debug log:
```bash
cat ~/.claude/export-debug.log
```

Common issues:
- Hook not configured in `~/.claude/settings.json`
- Scripts not executable (`chmod +x`)
- Incorrect paths in settings

## Permission errors

Ensure directories are writable:
```bash
chmod 755 ~/claude-conversations
chmod 755 ~/.claude/scripts
```

## Import errors

If database import fails:
- Verify JSONL files exist in `~/claude-conversations/`
- Check file permissions
- Ensure Python 3.10+ is installed (`python3 --version`)
- Run with verbose output: `claude-code-import -v`

## App not launching

- Ensure the frontend is built: `cd frontend && npm install && npm run build`
- Check port 8000 is available: `lsof -ti:8000`
- Try alternate port: `claude-code-api --port 8001`
