# Security Policy

## Supported Versions

This project is currently in active development and has not had an official release. All users should run the latest version from the `main` branch:

```bash
git pull
./install.sh
```

Security fixes are applied directly to the main branch and are immediately available to all users.

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub issue.

Instead, please report it privately by:

1. **Opening a GitHub Security Advisory** (preferred method):
   - Go to the [Security tab](https://github.com/sujankapadia/claude-code-utils/security/advisories) of this repository
   - Click "Report a vulnerability"
   - Fill in the details privately

2. **Opening a private issue**:
   - Create a new issue with the `security` label
   - Mark it as private if possible
   - We will respond and move discussion to a secure channel

**Please include the following information:**
- Type of issue (e.g., SQL injection, command injection, path traversal, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will send a more detailed response within 7 days indicating the next steps
- We will keep you informed of the progress towards a fix
- We may ask for additional information or guidance
- We will credit you in the fix commit (unless anonymity requested)

## Security Best Practices

### For Users

**Protecting API Keys:**
- Store API keys in `~/.config/claude-code-analytics/.env` (never commit to git)
- Use environment variables for temporary overrides
- Never share your `.env` file
- Rotate API keys regularly

**Data Privacy:**
- All conversation data stays local (no cloud sync)
- Database stored at `~/claude-conversations/conversations.db`
- No telemetry or analytics collection
- No data sent to third parties (except when using AI analysis features)

**Access Control:**
- Database file has user-only permissions by default
- Config file should be readable only by you: `chmod 600 ~/.config/claude-code-analytics/.env`
- Exported conversations in `~/claude-conversations/` contain your code and conversations

### For Developers

**Dependency Management:**
- All Python dependencies are specified in `pyproject.toml`
- Regular dependency updates for security patches
- Use `git pull && ./install.sh` to get latest secure versions
- The installation script uses pip to install the package and all dependencies

**Database Security:**
- SQLite database is local-only, not exposed to network
- No SQL injection risks (uses parameterized queries)
- FTS5 search is safe from injection attacks

**Configuration:**
- No sensitive defaults
- All paths respect user permissions
- XDG-compliant config location

## Known Security Considerations

### API Keys in AI Analysis

When using AI analysis features:
- API keys are sent to OpenRouter or Google Gemini APIs
- Your conversation data is sent to the selected LLM provider
- Review provider privacy policies:
  - [OpenRouter Privacy](https://openrouter.ai/privacy)
  - [Google AI Privacy](https://support.google.com/gemini/answer/13594961)

**Recommendation:** Only analyze conversations that don't contain sensitive information, or use local models.

### Conversation Data

Exported conversations may contain:
- Your code and project details
- File paths (which may reveal system structure)
- Error messages and stack traces
- API responses and data

**Recommendation:** Review exported data before sharing. Use `.gitignore` to exclude conversation directories from version control.

### Hook Execution

The SessionEnd hook executes automatically:
- Runs bash script from `~/.claude/scripts/export-conversation.sh`
- Has access to your conversation transcript
- Writes to `~/claude-conversations/`

**Recommendation:** Review hook script before installation. Only install hooks from trusted sources.

## Disclosure Policy

When we learn of a security issue, we will:

1. **Confirm the issue** and determine its impact
2. **Prepare fixes** for all supported versions
3. **Release new versions** with fixes
4. **Publish security advisory** on GitHub
5. **Credit the reporter** (unless anonymity requested)

### Timeline

- **Day 0:** Issue reported
- **Day 1-2:** Acknowledgment sent
- **Day 7:** Detailed response with timeline
- **Day 30 (target):** Fix released (may vary based on complexity)
- **Day 31+:** Public disclosure after fix is available

## Security Updates

Since this project is unreleased and in active development:
- Security fixes are applied directly to the `main` branch
- No version tags or formal releases yet
- All users run the latest commit

Users should update regularly:
```bash
git pull
./install.sh
```

When the project reaches a stable release (1.0.0), security updates will be released as patch versions (1.0.1, 1.0.2) with tagged releases on GitHub.

## Contact

For security-related questions (non-vulnerability):
- Open a GitHub Discussion
- Tag with `security` label

For vulnerability reports:
- Use GitHub Security Advisories (see "Reporting a Vulnerability" section above)

## Acknowledgments

We appreciate the security research community and will acknowledge reporters of valid security issues in our release notes and security advisories.

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [SQLite Security](https://www.sqlite.org/security.html)

---

**Last updated:** December 2025
