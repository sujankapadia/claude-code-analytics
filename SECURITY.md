# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub issue.

Instead, please report it by emailing: [Your security contact email - TO BE ADDED]

**Please include the following information:**
- Type of issue (e.g., SQL injection, XSS, authentication bypass, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### What to Expect

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will send a more detailed response within 7 days indicating the next steps
- We will keep you informed of the progress towards a fix and announcement
- We may ask for additional information or guidance

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
- All Python dependencies are pinned with SHA256 checksums in Homebrew formula
- Regular dependency updates for security patches
- Use `brew upgrade claude-code-analytics` to get latest secure versions

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

Security updates are released as:
- **Patch versions** (1.0.1, 1.0.2) for security fixes
- **Revision bumps** in Homebrew formula for dependency updates

Users should update regularly:
```bash
brew upgrade claude-code-analytics
```

## Contact

For security-related questions (non-vulnerability):
- Open a GitHub Discussion
- Tag with `security` label

For vulnerability reports:
- Email: [TO BE ADDED]
- PGP key: [TO BE ADDED - optional]

## Acknowledgments

We appreciate the security research community and will acknowledge reporters of valid security issues in our release notes and security advisories.

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [SQLite Security](https://www.sqlite.org/security.html)

---

**Last updated:** December 2024
