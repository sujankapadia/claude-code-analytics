# Homebrew Packaging Plan

## Overview

Package Claude Code Analytics as a Homebrew formula to enable simple installation via `brew install`.

**Documentation Reference**: This plan follows the latest Homebrew guidelines as of December 2024:
- [Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python for Formula Authors](https://docs.brew.sh/Python-for-Formula-Authors)
- [How to Open a PR](https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request)
- [Taps](https://docs.brew.sh/Taps)

## Prerequisites

### Homebrew Formula Requirements

According to Homebrew guidelines, all formulas must have:

1. **Stable Tagged Release**: Must have a version tag (e.g., `v1.0.0`) - Homebrew doesn't accept untagged software
2. **Tarball URL**: Use GitHub release tarball, not raw repository URL
3. **SHA256 Checksum**: Required for security verification
4. **Homepage**: An HTTPS homepage is required (GitHub repo URL is acceptable)
5. **License**: Must use SPDX License List identifier or be public domain
6. **Description**: Clear, concise description of what the tool does
7. **Meaningful Tests**: Tests must verify actual functionality, not just `--version` or `--help`

### Source URL Format

❌ **INCORRECT** - Don't use raw repository URL:
```ruby
url "https://github.com/sujankapadia/claude-code-utils"
```

✅ **CORRECT** - Use GitHub release tarball URL:
```ruby
url "https://github.com/sujankapadia/claude-code-utils/archive/refs/tags/v1.0.0.tar.gz"
sha256 "abc123..."  # Generated from the tarball
```

**Why**: Homebrew requires stable, versioned sources with checksums. GitHub automatically creates tarballs for all tags at the `/archive/refs/tags/VERSION.tar.gz` endpoint.

### Repository Requirements for Taps

- Repository name must be `homebrew-something` (the prefix is mandatory)
- Users can reference it as `username/something` (prefix omitted in commands)
- Repository should contain `Formula/` directory with formula files

### For Homebrew Core Submission (Optional)

If submitting to the main Homebrew repository (not required for personal tap):
- Need 30+ forks, 30+ watchers, OR 75+ stars on GitHub
- Must meet all quality and stability requirements
- PR review process can take weeks

### Claude Code Dependency

**Important Discovery**: Claude Code is available via Homebrew as a **cask** (not a formula):
```bash
brew install --cask claude-code
```

**Key Limitation**: Homebrew formulas **cannot depend on casks**. Only casks can depend on formulas.

**Our Approach**:
1. **Do NOT add Claude Code as a dependency** - it's technically impossible
2. **Use the caveats section** to inform users Claude Code is required
3. **Provide installation instructions** in the caveats
4. **The analytics tool works independently** - it processes exported data, doesn't need Claude Code running

This is the correct Homebrew pattern for optional runtime requirements that aren't formulas.

## Installation Experience

### User Workflow
```bash
# Install via Homebrew
brew install claude-code-analytics

# That's it! The formula handles:
# - Installing Python dependencies
# - Copying scripts to ~/.claude/scripts/
# - Setting up hooks in ~/.claude/settings.json
# - Creating config at ~/.config/claude-code-analytics/.env
# - Creating data directories

# User can immediately run:
claude-code-analytics         # Launch dashboard
claude-code-import            # Import conversations
claude-code-search "query"    # Search from CLI
```

## Homebrew Formula Structure

### Formula Location
- **Tap**: Could create custom tap `sujankapadia/claude-code-analytics`
- **Formula**: `Formula/claude-code-analytics.rb`

### Formula Template

```ruby
class ClaudeCodeAnalytics < Formula
  include Language::Python::Virtualenv

  desc "Analytics platform for Claude Code conversations"
  homepage "https://github.com/sujankapadia/claude-code-utils"
  url "https://github.com/sujankapadia/claude-code-utils/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "..." # Generate with: curl -L <url> | shasum -a 256
  license "MIT"

  depends_on "python@3.11"
  depends_on "jq"

  # Python dependencies
  resource "streamlit" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  resource "pandas" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  # ... other resources for altair, google-generativeai, openai, jinja2, pyyaml, python-dotenv

  def install
    # Create virtualenv and install Python dependencies
    virtualenv_install_with_resources

    # Install scripts
    (prefix/"libexec").install Dir["*"]

    # Create symlinks for CLI commands
    bin.install_symlink prefix/"libexec/run_dashboard.sh" => "claude-code-analytics"
    bin.install_symlink prefix/"libexec/scripts/import_conversations.py" => "claude-code-import"
    bin.install_symlink prefix/"libexec/scripts/search_fts.py" => "claude-code-search"
    bin.install_symlink prefix/"libexec/scripts/analyze_session.py" => "claude-code-analyze"
  end

  def post_install
    # Create required directories
    (var/"claude-conversations").mkpath
    claude_scripts = Pathname.new(Dir.home) / ".claude" / "scripts"
    claude_scripts.mkpath

    # Copy hook scripts to ~/.claude/scripts/
    cp prefix/"libexec/hooks/export-conversation.sh", claude_scripts
    cp prefix/"libexec/scripts/pretty-print-transcript.py", claude_scripts
    chmod 0755, claude_scripts/"export-conversation.sh"
    chmod 0755, claude_scripts/"pretty-print-transcript.py"

    # Create config directory and .env file
    config_dir = Pathname.new(Dir.home) / ".config" / "claude-code-analytics"
    config_dir.mkpath

    unless (config_dir/".env").exist?
      cp prefix/"libexec/.env.example", config_dir/".env"
    end

    # Configure Claude Code settings.json
    setup_claude_hooks
  end

  def setup_claude_hooks
    settings_file = Pathname.new(Dir.home) / ".claude" / "settings.json"
    hook_command = "bash ~/.claude/scripts/export-conversation.sh"

    if settings_file.exist?
      # Backup existing settings
      cp settings_file, "#{settings_file}.backup"

      # Use jq to add hook
      system "jq", "--arg", "cmd", hook_command,
             '.hooks.SessionEnd = [{"matcher": "", "hooks": [{"type": "command", "command": $cmd}]}]',
             settings_file.to_s
    else
      # Create new settings file with hook
      settings_file.write <<~JSON
        {
          "hooks": {
            "SessionEnd": [
              {
                "matcher": "",
                "hooks": [
                  {
                    "type": "command",
                    "command": "#{hook_command}"
                  }
                ]
              }
            ]
          }
        }
      JSON
    end
  end

  def caveats
    <<~EOS
      Claude Code Analytics has been installed!

      ⚠️  REQUIREMENT: This tool analyzes Claude Code conversations.
      If you haven't installed Claude Code yet:

        brew install --cask claude-code

      The analytics tool processes exported conversation data and works
      independently - Claude Code doesn't need to be running.

      To get started:
        1. Launch the dashboard:
           $ claude-code-analytics

        2. The dashboard will open at http://localhost:8501

        3. Click "Run Import" to import your conversations

      Configuration:
        Edit ~/.config/claude-code-analytics/.env to customize settings

      For AI analysis features, add an API key:
        export OPENROUTER_API_KEY="sk-or-your-key"
        # or
        export GOOGLE_API_KEY="your-key"

      CLI Commands:
        claude-code-analytics    # Launch dashboard
        claude-code-import       # Import conversations
        claude-code-search       # Search conversations
        claude-code-analyze      # Analyze sessions

      Documentation:
        https://github.com/sujankapadia/claude-code-utils
    EOS
  end

  test do
    # Basic test to ensure imports work
    system bin/"claude-code-import", "--help"
    system bin/"claude-code-search", "--help"
  end
end
```

## Implementation Steps

### 1. Prepare Repository for Release

- [ ] Create and push a version tag
- [ ] Verify GitHub automatically created the release tarball
- [ ] Generate SHA256 checksum from the tarball

```bash
# Step 1: Create and push version tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Step 2: GitHub automatically creates tarball at:
# https://github.com/sujankapadia/claude-code-utils/archive/refs/tags/v1.0.0.tar.gz

# Step 3: Generate SHA256 checksum
curl -L https://github.com/sujankapadia/claude-code-utils/archive/refs/tags/v1.0.0.tar.gz | shasum -a 256

# Example output:
# abc123def456...  -
# Copy this hash for use in the formula
```

**Important**: Use the `/archive/refs/tags/VERSION.tar.gz` format, not the short `/archive/VERSION.tar.gz` format, as it's more explicit and future-proof.

### 2. Create Homebrew Tap

```bash
# Create tap repository
gh repo create homebrew-claude-code-analytics --public

# Clone and set up
git clone https://github.com/sujankapadia/homebrew-claude-code-analytics
cd homebrew-claude-code-analytics

# Create formula
mkdir Formula
# Add claude-code-analytics.rb formula
```

### 3. Generate Python Resource Stanzas

Use Homebrew's built-in tool to automatically generate resource stanzas:

```bash
# Primary method (recommended by Homebrew)
brew update-python-resources claude-code-analytics

# If that fails, use print-only mode
brew update-python-resources --print-only claude-code-analytics

# Fallback: Use homebrew-pypi-poet if automatic tool fails
pip install homebrew-pypi-poet
poet streamlit pandas altair google-generativeai openai jinja2 pyyaml python-dotenv
```

**Note**: `brew update-python-resources` is the official Homebrew tool and should be tried first. It automatically generates all required `resource` blocks by analyzing the package dependencies.

### 4. Test Formula Locally

Follow Homebrew's official testing workflow:

```bash
# Set environment variable to use local tap
export HOMEBREW_NO_INSTALL_FROM_API=1

# Install from local formula (build from source)
brew install --build-from-source ./Formula/claude-code-analytics.rb

# Run the formula's test suite
brew test claude-code-analytics

# Audit the formula (strict mode + online checks)
brew audit --strict --online claude-code-analytics

# Test CLI commands work
claude-code-analytics --help
claude-code-import --help

# Uninstall and reinstall to test clean installation
brew uninstall claude-code-analytics
brew install --build-from-source ./Formula/claude-code-analytics.rb
```

**Important**: All tests must pass without issues before publishing the formula.

### 5. Publish Tap

```bash
git add Formula/claude-code-analytics.rb
git commit -m "Add claude-code-analytics formula"
git push origin main
```

### 6. User Installation

Users can then install with:

```bash
# Add tap
brew tap sujankapadia/claude-code-analytics

# Install
brew install claude-code-analytics
```

Or one-liner:
```bash
brew install sujankapadia/claude-code-analytics/claude-code-analytics
```

## Alternative: Core Homebrew Submission

To get into the main Homebrew repository (homebrew-core):

1. Must meet [Homebrew requirements](https://docs.brew.sh/Acceptable-Formulae):
   - Notable project (30+ GitHub stars, active development)
   - Stable releases
   - No duplicate functionality

2. Submit PR to homebrew-core:
   ```bash
   brew create https://github.com/sujankapadia/claude-code-utils/archive/v1.0.0.tar.gz
   ```

3. PR Review process (can take weeks)

4. If accepted, users can install with:
   ```bash
   brew install claude-code-analytics
   ```

## CLI Wrapper Scripts

To provide clean CLI commands, create wrapper scripts:

### `bin/claude-code-analytics`
```bash
#!/bin/bash
# Launch Streamlit dashboard
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR" && streamlit run streamlit_app/app.py "$@"
```

### `bin/claude-code-import`
```bash
#!/bin/bash
# Import conversations
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SCRIPT_DIR/scripts/import_conversations.py" "$@"
```

### `bin/claude-code-search`
```bash
#!/bin/bash
# Search conversations
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SCRIPT_DIR/scripts/search_fts.py" "$@"
```

### `bin/claude-code-analyze`
```bash
#!/bin/bash
# Analyze session
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SCRIPT_DIR/scripts/analyze_session.py" "$@"
```

## Dependency Strategy

### Claude Code Requirement

**Problem**: Our tool analyzes Claude Code conversations, but Claude Code is a cask, not a formula.

**Homebrew Limitation**: Formulas cannot depend on casks (only casks can depend on formulas).

**Solution**: Use the `caveats` section to inform users about the Claude Code requirement.

```ruby
def caveats
  <<~EOS
    ⚠️  REQUIREMENT: This tool analyzes Claude Code conversations.
    If you haven't installed Claude Code yet:

      brew install --cask claude-code

    The analytics tool processes exported conversation data and works
    independently - Claude Code doesn't need to be running.
  EOS
end
```

### Why This Works

1. **No Hard Dependency**: The analytics tool works on exported data files
2. **Claude Code Not Required at Runtime**: It only needs the exported `.jsonl` files
3. **User Choice**: Users might already have Claude Code installed via other means
4. **Clear Communication**: The caveats section provides installation instructions
5. **Homebrew Best Practice**: This is the recommended approach for optional runtime requirements

### Alternative Considered (Rejected)

We could create a meta-cask that depends on both:
- `claude-code` (cask)
- `claude-code-analytics` (formula)

**Why Rejected**: Adds complexity, and our tool works independently of Claude Code's runtime.

## Configuration Considerations

### Environment Variable Setup

Homebrew formula should:
1. **Not** modify user's shell profile (against Homebrew guidelines)
2. Document environment variables in caveats
3. Let users add to their own `.bashrc`/`.zshrc`

### Config File Location

The formula respects the standard config location:
- `~/.config/claude-code-analytics/.env` (already implemented)

This works perfectly with Homebrew's philosophy of not polluting user directories.

## Testing Strategy

### Official Homebrew Testing Workflow

Follow Homebrew's recommended three-step testing process:

```bash
# Step 0: Set environment to use local tap
export HOMEBREW_NO_INSTALL_FROM_API=1

# Step 1: Install and test the formula
brew install --build-from-source claude-code-analytics

# Step 2: Run the test suite
brew test claude-code-analytics

# Step 3: Audit the formula (after installation)
brew audit --strict --online claude-code-analytics

# Additional verification: Test CLI commands
claude-code-analytics --help
claude-code-import --help
claude-code-search --help
claude-code-analyze --help
```

**Requirements**: All three steps must pass without issues before committing changes.

### Test Fixture Best Practices

According to Homebrew guidelines, avoid superficial tests like `--version` or `--help`. Instead, implement meaningful tests:

- For CLI apps: Test actual functionality (e.g., import a sample conversation)
- Use `testpath` directory for temporary test files
- Verify core features work, not just that the binary exists

Example test in formula:
```ruby
test do
  # Create a minimal test transcript
  (testpath/"test.jsonl").write('{"message":{"role":"user","content":"test"}}')

  # Test that import can process it (would create DB, import, etc)
  system bin/"claude-code-import", "--help"

  # Better: Actually test import functionality
  ENV["CLAUDE_CONVERSATIONS_DIR"] = testpath
  system bin/"claude-code-import"
  assert_predicate testpath/"conversations.db", :exist?
end
```

### Test on Clean System

Use Homebrew's official Docker image:
```bash
# Start Homebrew container
docker run -it homebrew/brew:latest bash

# Inside container: Install formula
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics

# Verify installation
claude-code-analytics --help
```

## Documentation Updates

After Homebrew packaging:

### README.md - Add Installation Section
```markdown
## Installation

### Homebrew (macOS)
```bash
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics
```

### Git Clone (All platforms)
```bash
git clone https://github.com/sujankapadia/claude-code-utils.git
cd claude-code-utils
./install.sh
```
```

### Update Quick Start
```markdown
## Quick Start

### Using Homebrew
```bash
# Install
brew install claude-code-analytics

# Launch dashboard
claude-code-analytics

# Import conversations
claude-code-import
```

### Using Git Clone
```bash
./run_dashboard.sh
python3 scripts/import_conversations.py
```
```

## Future Enhancements

### Linux Package Managers
- **APT** (Debian/Ubuntu): Create `.deb` package
- **RPM** (Fedora/RHEL): Create `.rpm` package
- **AUR** (Arch Linux): Submit to Arch User Repository

### Python Package (pip/pipx)
```bash
pipx install claude-code-analytics
```

Requires restructuring as proper Python package with:
- `setup.py` or `pyproject.toml`
- Package structure under `src/`
- Entry points for CLI commands

## Benefits of Homebrew Packaging

1. **Simple Installation**: Single command vs multi-step setup
2. **Dependency Management**: Homebrew handles Python, jq, etc.
3. **Automatic Updates**: `brew upgrade claude-code-analytics`
4. **Uninstall**: `brew uninstall claude-code-analytics` (clean removal)
5. **Version Management**: Easy to install specific versions
6. **Discoverability**: Users can find via `brew search`
7. **Trust**: Homebrew's reputation adds credibility

## Timeline Estimate

- **Formula Creation**: 2-4 hours
- **Testing**: 1-2 hours
- **Tap Setup**: 30 minutes
- **Documentation**: 1 hour
- **Total**: ~5-8 hours

## Next Steps

1. Create feature branch: `feature/homebrew-packaging`
2. Create CLI wrapper scripts in `bin/`
3. Write Homebrew formula
4. Test locally
5. Create homebrew tap repository
6. Update documentation
7. Tag release and publish
