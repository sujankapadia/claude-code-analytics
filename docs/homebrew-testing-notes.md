# Homebrew Formula Testing Notes

## Testing Attempt Summary

**Date:** December 22, 2024
**Branch:** feature/homebrew-packaging
**Status:** Partially successful - identified blocking issues

## What We Learned

### ✅ Successful Components

1. **Formula Syntax**: Formula structure is valid and passes basic Homebrew checks
2. **Tap Creation**: Successfully created local tap at `/opt/homebrew/Library/Taps/sujankapadia/homebrew-claude-code-analytics`
3. **Tarball Download**: Homebrew can download from GitHub branch URL
4. **SHA256 Generation**: Homebrew automatically calculated checksum:
   ```
   sha256 "8088b0dd4f16ef2f187418324097a92da7d848deba1c3639b1ae45f914ef1f59"
   ```
   (This is for the current `feature/homebrew-packaging` branch)
5. **Dependency Resolution**: Python 3.11, jq, and system dependencies install correctly
6. **CLI Wrapper Scripts**: Wrapper script approach is sound

### ❌ Blocking Issues Discovered

#### 1. Not a Python Package

**Error:**
```
ERROR: Directory '/private/tmp/claude-code-analytics-20251222-99087-4o22e6/claude-code-utils-feature-homebrew-packaging' is not installable.
Neither 'setup.py' nor 'pyproject.toml' found.
```

**Root Cause:**
- Our project isn't structured as an installable Python package
- `virtualenv_install_with_resources` expects either `setup.py` or `pyproject.toml`
- We're currently a collection of scripts, not a proper package

**Impact:** Cannot create proper Python virtualenv with isolated dependencies

#### 2. Missing Python Resources

**Issue:**
- Formula has placeholder comments for Python dependencies
- `brew update-python-resources` needs a proper Python package to analyze
- Without resources, can't install dependencies in virtualenv

**Required Resources:**
- streamlit
- pandas
- altair
- google-generativeai
- openai
- jinja2
- pyyaml
- python-dotenv

## Remaining Tasks for v1.0.0

### Critical (Blocking Release)

#### 1. Create Python Package Structure

**Option A: Modern approach (pyproject.toml)**
```toml
[project]
name = "claude-code-analytics"
version = "1.0.0"
description = "Analytics platform for Claude Code conversations"
readme = "README.md"
license = {text = "MIT"}

dependencies = [
    "streamlit>=1.28.0",
    "pandas>=2.0.0",
    "altair>=5.0.0",
    "google-generativeai>=0.3.0",
    "openai>=1.0.0",
    "jinja2>=3.0.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
claude-code-analytics = "claude_code_analytics.cli:dashboard"
claude-code-import = "claude_code_analytics.cli:import_cmd"
claude-code-search = "claude_code_analytics.cli:search_cmd"
claude-code-analyze = "claude_code_analytics.cli:analyze_cmd"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**Required File Restructuring:**
```
claude-code-analytics/
├── src/
│   └── claude_code_analytics/
│       ├── __init__.py
│       ├── cli.py           # Entry points
│       ├── config.py
│       ├── streamlit_app/
│       └── scripts/
├── hooks/
├── pyproject.toml
├── README.md
└── LICENSE
```

**OR Option B: Minimal approach (setup.py)**
```python
from setuptools import setup, find_packages

setup(
    name="claude-code-analytics",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "altair>=5.0.0",
        "google-generativeai>=0.3.0",
        "openai>=1.0.0",
        "jinja2>=3.0.0",
        "pyyaml>=6.0.0",
        "python-dotenv>=1.0.0",
    ],
)
```

**Decision Required:** Which approach to take?
- pyproject.toml is modern and recommended
- setup.py is simpler but legacy
- Both work with Homebrew

#### 2. Generate Python Resources

Once we have a package structure:

```bash
# Auto-generate resource stanzas
brew update-python-resources Formula/claude-code-analytics.rb

# This will add all resource blocks with proper URLs and SHA256 checksums
```

#### 3. Update Formula Install Method

Change from:
```ruby
def install
  libexec.install Dir["*"]
  # Manual wrapper scripts
end
```

To proper virtualenv approach:
```ruby
def install
  virtualenv_install_with_resources
  # Homebrew handles CLI entry points from pyproject.toml
end
```

#### 4. Update for Real Release

- Change URL from branch to tag: `v1.0.0.tar.gz`
- Generate new SHA256 for tag (not branch)
- Remove "dev" version suffix
- Remove testing comments

### Testing (After Above Fixes)

1. **Local Install Test:**
   ```bash
   export HOMEBREW_NO_INSTALL_FROM_API=1
   brew install --build-from-source claude-code-analytics
   ```

2. **Verify CLI Commands:**
   ```bash
   claude-code-analytics --help
   claude-code-import --help
   claude-code-search --help
   claude-code-analyze --help
   ```

3. **Run Formula Tests:**
   ```bash
   brew test claude-code-analytics
   ```

4. **Audit:**
   ```bash
   brew audit --strict --online claude-code-analytics
   ```

5. **Clean Install Test:**
   ```bash
   brew uninstall claude-code-analytics
   brew install --build-from-source claude-code-analytics
   ```

## Alternative Workaround (Not Recommended)

We *could* make the formula work without being a Python package by:
- Not using `virtualenv_install_with_resources`
- Just copying files to libexec
- Using system Python and assuming packages are installed

**Why this is bad:**
- No dependency isolation
- Breaks on systems without packages installed
- Not proper Homebrew style
- Won't work for other users

**Verdict:** Not acceptable for release

## Next Steps

1. **Decide on package structure**: pyproject.toml (recommended) or setup.py
2. **Restructure repository**: Move to src/ layout if using pyproject.toml
3. **Add package files**: pyproject.toml or setup.py
4. **Create CLI entry points**: In cli.py module
5. **Test packaging works**: `pip install -e .` locally
6. **Generate Homebrew resources**: `brew update-python-resources`
7. **Test complete formula**: Full install → test → audit cycle

## Estimated Effort

- **Package restructuring**: 2-4 hours
- **CLI entry points**: 1-2 hours
- **Testing**: 1-2 hours
- **Documentation updates**: 1 hour
- **Total**: 5-9 hours

## Current Formula State

The formula in this branch:
- ✅ Has correct structure for Homebrew
- ✅ Has proper metadata (desc, homepage, license)
- ✅ Has comprehensive tests (6 test cases)
- ✅ Has good caveats message
- ✅ Has post-install hooks setup
- ⚠️ Uses temporary branch URL (need tag)
- ⚠️ Has SHA256 for branch (need tag SHA256)
- ❌ Missing Python resources
- ❌ Won't install without package structure

**Status:** 80% complete - needs Python packaging to finish

## Files Modified in This Testing Session

- `Formula/claude-code-analytics.rb` - Created and iterated
- `/opt/homebrew/Library/Taps/sujankapadia/homebrew-claude-code-analytics/` - Local tap
- Updated with SHA256: `8088b0dd4f16ef2f187418324097a92da7d848deba1c3639b1ae45f914ef1f59`

## Lessons Learned

1. **Homebrew expects proper packages**: Can't just point at a script collection
2. **`virtualenv_install_with_resources` is non-negotiable**: It's the proper way for Python formulas
3. **Testing early reveals issues**: Good that we tested before creating v1.0.0 tag
4. **Python packaging is a prerequisite**: Can't skip this step
5. **Homebrew provides good error messages**: Made it clear what was missing

## Recommendation

**Do NOT tag v1.0.0 yet.** First complete:
1. Python package structure
2. Python resources generation
3. Complete local testing
4. Then tag and release

This ensures a smooth release experience for users.
