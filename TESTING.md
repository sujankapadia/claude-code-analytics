# Testing

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=claude_code_analytics

# Run specific test file
pytest tests/test_database_service.py
```

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

- **Black** — Code formatting (100 char line length)
- **Ruff** — Linting with auto-fix
- **Bandit** — Security scanning
- **Standard checks** — Trailing whitespace, YAML/JSON validation, large files, merge conflicts

```bash
# Run all hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## Frontend

```bash
cd frontend

# Type check
npx tsc --noEmit

# Build (catches errors)
npm run build
```

## Manual Testing

Use Playwright MCP to test frontend changes in the browser before committing.
