# Logging Conventions

All production scripts in this directory use Python's `logging` module for consistent, configurable output.

## Standard Setup

All scripts should include this at the top:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)
```

## Usage Guidelines

### Log Levels

- **`logger.info()`**: Normal operational messages (progress, success, statistics)
- **`logger.warning()`**: Non-fatal issues (e.g., user interruption, skipped items)
- **`logger.error()`**: Errors that prevent operation (e.g., missing files, database errors)
- **`logger.debug()`**: Detailed diagnostic information (use sparingly)

### Examples

```python
# Good - use logging
logger.info("Database schema created successfully")
logger.error(f"Database not found: {db_path}")
logger.warning("Interrupted by user")

# Bad - don't use print()
print("Database schema created successfully")
print(f"❌ Error: {error_message}")
```

## Benefits

1. **Configurable Verbosity**: Users can control log level via environment or code
2. **Programmatic Use**: Scripts can be imported and used without unwanted output
3. **Structured Output**: Consistent format across all scripts
4. **Redirection**: Easy to redirect logs to files or other handlers

## Controlling Verbosity

Users can set the log level in their code:

```python
import logging
logging.getLogger().setLevel(logging.WARNING)  # Show only warnings and errors

from claude_code_analytics.scripts.import_conversations import main
main()  # Runs quietly
```

Or via environment variable:

```bash
export PYTHONLOGLEVEL=WARNING
python3 scripts/import_conversations.py
```

## Test and Demo Scripts

Interactive test scripts (`test_*.py`) and demo scripts (`demo_*.py`) may use `print()`
for user-facing output, as they are not intended for programmatic use.
