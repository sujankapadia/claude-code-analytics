# Homebrew Packaging Plan

## Overview

Package Claude Code Analytics as a Homebrew formula to enable simple installation via `brew install`.

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
  url "https://github.com/sujankapadia/claude-code-utils/archive/v1.0.0.tar.gz"
  sha256 "..." # Will be generated from release tarball
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

- [ ] Tag a release version (e.g., `v1.0.0`)
- [ ] Create GitHub release with tarball
- [ ] Generate SHA256 checksum for tarball

```bash
# Create release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Generate checksum
curl -L https://github.com/sujankapadia/claude-code-utils/archive/v1.0.0.tar.gz | shasum -a 256
```

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

Use `homebrew-pypi-poet` to generate resource stanzas for Python dependencies:

```bash
pip install homebrew-pypi-poet

# Generate resources
poet streamlit pandas altair google-generativeai openai jinja2 pyyaml python-dotenv
```

This outputs the `resource` blocks needed in the formula.

### 4. Test Formula Locally

```bash
# Install from local formula
brew install --build-from-source ./Formula/claude-code-analytics.rb

# Test it works
claude-code-analytics --help
claude-code-import --help

# Uninstall and test again
brew uninstall claude-code-analytics
brew install claude-code-analytics
```

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

### Local Testing
```bash
# Test formula syntax
brew audit --strict ./Formula/claude-code-analytics.rb

# Test installation
brew install --build-from-source ./Formula/claude-code-analytics.rb

# Test all CLI commands
claude-code-analytics --help
claude-code-import --help
claude-code-search --help
claude-code-analyze --help
```

### Test on Clean System
Use Docker to test on clean macOS environment:
```bash
# Start macOS container
docker run -it homebrew/brew:latest

# Install formula
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics
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
