# Contributing

[Back to README](../README.md)

Contributions are welcome! Feel free to:
- Report bugs or request features via GitHub Issues
- Submit pull requests
- Share your custom analysis prompts
- Suggest new analytics visualizations

## Running in Development Mode

For frontend development with hot-reload:

```bash
# Terminal 1: Start the API server with auto-reload
claude-code-api --reload

# Terminal 2: Start the React dev server (proxies /api to port 8000)
cd frontend && npm run dev
```

The dev server runs at `http://localhost:5173` with hot module replacement.

## Setting Up Development Environment

If you're contributing to Claude Code Analytics or modifying the code, we use pre-commit hooks to ensure code quality.

### 1. Install pre-commit

```bash
pip install pre-commit
```

### 2. Install the git hooks

```bash
pre-commit install
```

### 3. (Optional) Run against all files

```bash
pre-commit run --all-files
```

The hooks will now run automatically before each commit.

## Code Quality Tools

The pre-commit configuration includes:

- **Black** - Automatic code formatting (100 character line length)
- **Ruff** - Fast Python linter with auto-fix capabilities
  - Checks: pycodestyle, pyflakes, isort, flake8-bugbear, pyupgrade, and more
  - Automatically modernizes type hints (e.g., `typing.Dict` -> `dict`)
  - Improves exception handling patterns
- **Bandit** - Security linting to detect potential vulnerabilities
- **Mypy** - Static type checking for type safety
- **Standard checks** - Trailing whitespace, end-of-file, YAML/JSON validation, large files, merge conflicts, private keys

## Manual Code Quality Checks

If you need to run checks manually without committing:

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files

# Skip hooks for a specific commit (not recommended)
git commit --no-verify
```

## Configuration

All tool configurations are in `pyproject.toml`:

- **Black**: 100 character line length
- **Ruff**: Comprehensive rule set with modern Python practices
- **Bandit**: Excludes test files, configured for security-critical patterns
- **Mypy**: Python 3.10 target with reasonable strictness

## Logging Standards

Production scripts use Python's `logging` module for consistent output. See `claude_code_analytics/scripts/LOGGING.md` for conventions:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Use logger methods instead of print()
logger.info("Processing completed")
logger.error("Database not found")
logger.warning("Interrupted by user")
```
