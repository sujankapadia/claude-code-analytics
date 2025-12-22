# Release Checklist

## Pre-Release (Before Tagging)

### Documentation
- [ ] Update CHANGELOG.md with all changes since last release
- [ ] Update README.md if needed (new features, changed commands)
- [ ] Review and update SECURITY.md (add/update security contact email)
- [ ] Check all documentation links are valid
- [ ] Verify code examples in docs work

### Code Quality
- [ ] All tests pass locally: `python3 -m pytest` (if tests exist)
- [ ] Manual testing of key workflows:
  - [ ] Export conversation works (run Claude Code session and exit)
  - [ ] Import works: `python3 scripts/import_conversations.py`
  - [ ] Dashboard launches: `./run_dashboard.sh`
  - [ ] Search works (try a query)
  - [ ] AI analysis works (if API keys configured)
- [ ] No debug/console.log statements left in code
- [ ] All TODOs addressed or documented as future work

### Dependencies
- [ ] All Python dependencies listed in formula resources
- [ ] No security vulnerabilities in dependencies: `pip-audit` (if available)
- [ ] Dependencies are latest stable versions (or pinned for compatibility)

## Creating the Release

### 1. Version Bumping
- [ ] Update version in CHANGELOG.md (change `[Unreleased]` to `[1.0.0] - YYYY-MM-DD`)
- [ ] Update formula URL to use new version tag (will update after creating tag)
- [ ] Commit version changes: `git commit -m "Bump version to 1.0.0"`

### 2. Create Git Tag
```bash
# Create annotated tag
git tag -a v1.0.0 -m "Release version 1.0.0

## Highlights
- Initial Homebrew release
- Streamlit dashboard for conversation analytics
- Full-text search with FTS5
- AI-powered analysis with 300+ models
- Automatic export via SessionEnd hooks

## Installation
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics
"

# Push tag to GitHub
git push origin v1.0.0
```

### 3. Generate Release Tarball SHA256
```bash
# Wait a few seconds for GitHub to generate the tarball
sleep 5

# Download and generate checksum
curl -L https://github.com/sujankapadia/claude-code-utils/archive/refs/tags/v1.0.0.tar.gz | shasum -a 256

# Save the hash - you'll need it for the formula
```

### 4. Update Homebrew Formula
- [ ] Update `Formula/claude-code-analytics.rb`:
  - [ ] Set correct `url` with version tag
  - [ ] Set `sha256` from step 3
- [ ] Generate Python resources (see below)
- [ ] Commit formula: `git commit -m "Update formula for v1.0.0"`

### 5. Generate Python Resources

**Option 1: Automatic (Recommended)**
```bash
# This auto-generates resource stanzas
brew update-python-resources Formula/claude-code-analytics.rb
```

**Option 2: Manual (If automatic fails)**
```bash
# Install poet
pip install homebrew-pypi-poet

# Generate resources
poet streamlit pandas altair google-generativeai openai jinja2 pyyaml python-dotenv

# Copy output into formula
```

- [ ] Python resources generated and added to formula
- [ ] All resources have SHA256 checksums
- [ ] Commit updated formula

## Testing the Formula

### 1. Local Testing
```bash
# Set environment for local testing
export HOMEBREW_NO_INSTALL_FROM_API=1

# Test installation from local formula
brew install --build-from-source ./Formula/claude-code-analytics.rb
```

### 2. Run Formula Tests
```bash
# Run the test suite
brew test claude-code-analytics
```

- [ ] All 6 tests pass:
  - [ ] Test 1: Database created
  - [ ] Test 2: Database schema correct
  - [ ] Test 3: Data imported (2 messages)
  - [ ] Test 4: FTS tables created
  - [ ] Test 5: Search works
  - [ ] Test 6: CLI help works

### 3. Manual Verification
```bash
# Test CLI commands
claude-code-analytics --help
claude-code-import --help
claude-code-search --help
claude-code-analyze --help

# Try actual import (if you have data)
claude-code-import

# Launch dashboard
claude-code-analytics
# Should open browser to http://localhost:8501
```

- [ ] All CLI commands work
- [ ] Dashboard launches successfully
- [ ] Can import actual conversations
- [ ] Can search conversations
- [ ] Analytics page shows data

### 4. Audit Formula
```bash
# Run strict audit
brew audit --strict --online claude-code-analytics
```

- [ ] No audit errors
- [ ] No audit warnings (or all acceptable)
- [ ] Fix any issues found

### 5. Clean Install Test
```bash
# Uninstall
brew uninstall claude-code-analytics

# Clean reinstall
brew install --build-from-source ./Formula/claude-code-analytics.rb

# Verify it works
claude-code-analytics --help
```

- [ ] Clean install works
- [ ] Post-install hooks ran successfully
- [ ] Config file created at `~/.config/claude-code-analytics/.env`
- [ ] Hook scripts installed to `~/.claude/scripts/`

### 6. Docker Clean Environment Test
```bash
# Start Homebrew Docker container
docker run -it homebrew/brew:latest bash

# Inside container:
brew tap sujankapadia/claude-code-analytics https://github.com/sujankapadia/homebrew-claude-code-analytics
brew install claude-code-analytics

# Test it works
claude-code-import --help
```

- [ ] Installs successfully in clean environment
- [ ] All dependencies resolved
- [ ] No environment-specific issues

## Publishing

### 1. Create GitHub Release
- [ ] Go to https://github.com/sujankapadia/claude-code-utils/releases/new
- [ ] Select tag: `v1.0.0`
- [ ] Release title: `v1.0.0 - Initial Homebrew Release`
- [ ] Copy release notes from CHANGELOG.md
- [ ] Add installation instructions
- [ ] Attach any binaries (if applicable)
- [ ] Publish release

### 2. Create Homebrew Tap Repository
```bash
# Create tap repository
gh repo create homebrew-claude-code-analytics --public --description "Homebrew tap for Claude Code Analytics"

# Clone it
git clone https://github.com/sujankapadia/homebrew-claude-code-analytics
cd homebrew-claude-code-analytics

# Create Formula directory
mkdir Formula

# Copy formula
cp ../claude-code-utils/Formula/claude-code-analytics.rb Formula/

# Create README
cat > README.md << 'EOF'
# Homebrew Tap for Claude Code Analytics

## Installation

```bash
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics
```

## Documentation

See the [main repository](https://github.com/sujankapadia/claude-code-utils) for documentation.
EOF

# Commit and push
git add Formula/claude-code-analytics.rb README.md
git commit -m "Add claude-code-analytics formula v1.0.0"
git push origin main
```

- [ ] Tap repository created
- [ ] Formula published to tap
- [ ] README added to tap

### 3. Test Tap Installation
```bash
# On a different machine or clean environment
brew tap sujankapadia/claude-code-analytics
brew install claude-code-analytics

# Verify
claude-code-analytics --help
```

- [ ] Tap installs successfully
- [ ] Formula works from tap

### 4. Update Main Repository
- [ ] Update README.md with Homebrew installation instructions
- [ ] Add badge: `![Homebrew](https://img.shields.io/badge/homebrew-available-blue)`
- [ ] Link to tap repository
- [ ] Commit and push

## Post-Release

### Documentation
- [ ] Update README.md with installation instructions
- [ ] Tweet/post about release (optional)
- [ ] Update any external documentation/wiki

### Monitoring
- [ ] Watch GitHub issues for installation problems
- [ ] Monitor tap repository for PRs/issues
- [ ] Check Homebrew analytics (if available): `brew info --analytics claude-code-analytics`

### Future Planning
- [ ] Create milestone for next version
- [ ] Add [Unreleased] section back to CHANGELOG.md
- [ ] Document any known issues or future improvements

## Rollback Procedure (If Needed)

If critical issues are found after release:

1. **Yank the release:**
   ```bash
   gh release delete v1.0.0
   git tag -d v1.0.0
   git push origin :refs/tags/v1.0.0
   ```

2. **Revert formula:**
   ```bash
   cd homebrew-claude-code-analytics
   git revert HEAD
   git push origin main
   ```

3. **Fix issues and create patch release:**
   - Fix the issue
   - Follow this checklist for v1.0.1

## Version-Specific Checklists

### For Patch Releases (1.0.x)
- [ ] Only bug fixes, no new features
- [ ] Update CHANGELOG with fixes
- [ ] Increment revision in formula if dependencies updated
- [ ] Fast-track testing (focus on fixed bugs)

### For Minor Releases (1.x.0)
- [ ] New features are backward compatible
- [ ] Update CHANGELOG with new features
- [ ] Update README with new features
- [ ] Full testing suite

### For Major Releases (x.0.0)
- [ ] Breaking changes documented
- [ ] Migration guide created
- [ ] Deprecation warnings added in previous version
- [ ] Extended testing period
- [ ] Communication plan for users

## Contacts

- **Maintainer:** [Your name]
- **Email:** [Your email]
- **GitHub:** [@sujankapadia](https://github.com/sujankapadia)

## Notes

- Keep this checklist updated as process evolves
- Add automation where possible (GitHub Actions, etc.)
- Document any deviations from this checklist in release notes
