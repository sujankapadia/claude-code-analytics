"""Integration tests for scanner with real content samples."""

import pytest

from claude_code_analytics.scanner import MultiLayerScanner, ScanSeverity

# Sample content with various sensitive patterns
SAMPLE_ANALYSIS = """# Session Analysis - Technical Decisions

## Overview
This session focused on implementing authentication for our application.

## Key Decisions

### Database Configuration
We decided to use PostgreSQL with the following connection:
- URL: postgres://admin:password123@db.internal.com:5432/production
- Backup URL: postgres://readonly:readpass@db.backup.com:5432/production

### API Keys
For external services, we're using:
- OpenAI API Key: sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNO
- AWS Access Key: AKIAIOSFODNN7EXAMPLE
- AWS Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

### Contact Information
Team contacts:
- Lead: john.doe@company.com (555-123-4567)
- Backend: jane.smith@company.com (555-987-6543)

### Development Environment
- Local server: http://localhost:8501
- Dev server: https://dev.internal.company.com
- Internal IP: 192.168.1.100

### Authentication Tokens
Example JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
"""

SAFE_CONTENT = """# Session Analysis - General Overview

## Summary
This session was about discussing high-level architecture patterns and best practices.

## Topics Covered
1. Microservices vs Monolithic architecture
2. Database normalization principles
3. API design patterns (REST, GraphQL)
4. Caching strategies
5. Testing methodologies

## Recommendations
- Follow SOLID principles
- Implement comprehensive testing
- Use dependency injection
- Document all public APIs

## Next Steps
- Schedule follow-up meeting
- Review architecture proposal
- Conduct team training session
"""


@pytest.mark.skipif(
    True,  # Skip by default, enable with: pytest -v --run-gitleaks
    reason="Requires gitleaks installation",
)
class TestGitleaksIntegration:
    """Tests requiring gitleaks binary."""

    def test_gitleaks_detects_secrets(self):
        """Test that gitleaks detects API keys and secrets."""
        scanner = MultiLayerScanner(enable_gitleaks=True, enable_regex=False)

        is_safe, findings = scanner.scan(SAMPLE_ANALYSIS)

        # Should detect secrets
        assert not is_safe

        # Should find AWS keys and other secrets
        secret_findings = [f for f in findings if f.category == "secrets"]
        assert len(secret_findings) > 0

        # Verify secrets are redacted
        for finding in secret_findings:
            assert "REDACTED" in finding.matched_text or "..." in finding.matched_text

    def test_gitleaks_scanner_initialization(self):
        """Test that gitleaks scanner initializes correctly."""
        try:
            scanner = MultiLayerScanner(enable_gitleaks=True, enable_regex=False)
            assert len(scanner.scanners) > 0
        except RuntimeError as e:
            pytest.skip(f"Gitleaks not available: {e}")


class TestRealContentScanning:
    """Test scanning realistic content samples."""

    def test_sample_analysis_with_secrets(self):
        """Test scanning analysis content with multiple secret types."""
        scanner = MultiLayerScanner(
            enable_gitleaks=False,
            enable_regex=True,  # Use regex only for speed
        )

        is_safe, findings = scanner.scan(SAMPLE_ANALYSIS)

        # Should not be safe due to multiple issues
        assert not is_safe

        # Should detect emails (HIGH severity)
        email_findings = [f for f in findings if f.rule_id == "email"]
        assert len(email_findings) >= 2  # john.doe@ and jane.smith@

        # Should detect database URLs (HIGH severity)
        db_findings = [f for f in findings if f.rule_id == "database-url"]
        assert len(db_findings) >= 2  # Two postgres URLs

        # Should detect JWT token (CRITICAL severity)
        jwt_findings = [f for f in findings if f.rule_id == "jwt-token"]
        assert len(jwt_findings) >= 1

        # Verify blocking findings exist
        blocking_findings = [
            f for f in findings if f.severity in (ScanSeverity.CRITICAL, ScanSeverity.HIGH)
        ]
        assert len(blocking_findings) > 0

    def test_safe_content_passes(self):
        """Test that safe content passes scan."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)

        is_safe, findings = scanner.scan(SAFE_CONTENT)

        # Should be safe
        assert is_safe

        # Should have no findings or only non-blocking ones
        blocking_findings = [
            f for f in findings if f.severity in (ScanSeverity.CRITICAL, ScanSeverity.HIGH)
        ]
        assert len(blocking_findings) == 0

    def test_allowlist_for_common_patterns(self):
        """Test that allowlist can ignore common dev patterns."""
        scanner = MultiLayerScanner(
            enable_gitleaks=False,
            enable_regex=True,
            regex_allowed_patterns={
                "localhost-url": ["localhost", "127.0.0.1"],
                "ip-private": ["192.168.1.100"],
                "email": ["company.com"],
            },
        )

        is_safe, findings = scanner.scan(SAMPLE_ANALYSIS)

        # Should still not be safe due to other issues
        assert not is_safe

        # But localhost and company emails should be filtered
        localhost_findings = [f for f in findings if f.rule_id == "localhost-url"]
        ip_findings = [
            f for f in findings if f.rule_id == "ip-private" and "192.168.1.100" in f.matched_text
        ]
        company_email_findings = [
            f for f in findings if f.rule_id == "email" and "company.com" in f.matched_text
        ]

        assert len(localhost_findings) == 0
        assert len(ip_findings) == 0
        assert len(company_email_findings) == 0

    def test_multi_file_scan_mixed_safety(self):
        """Test scanning multiple files with mixed safety levels."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)

        files = {
            "analysis.md": SAMPLE_ANALYSIS,
            "summary.md": SAFE_CONTENT,
            "notes.txt": "Quick note: contact john@example.com",
        }

        all_safe, findings_by_file = scanner.scan_multiple(files)

        # Overall should not be safe
        assert not all_safe

        # analysis.md should have findings
        assert "analysis.md" in findings_by_file

        # summary.md should be safe
        assert "summary.md" not in findings_by_file

        # notes.txt should have email finding
        assert "notes.txt" in findings_by_file

    def test_format_report_realistic(self):
        """Test report formatting with realistic content."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)

        is_safe, findings = scanner.scan(SAMPLE_ANALYSIS)

        report = MultiLayerScanner.format_report(findings)

        # Report should include severity sections
        assert "CRITICAL" in report or "HIGH" in report
        assert "❌ Sensitive data detected" in report

        # Should mention specific rules
        assert "email" in report.lower() or "database-url" in report.lower()


def main():
    """Run manual integration test."""
    print("=== Scanner Integration Test ===\n")

    # Test 1: Safe content
    print("Test 1: Scanning safe content...")
    scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)
    is_safe, findings = scanner.scan(SAFE_CONTENT)
    print(f"Result: {'✅ SAFE' if is_safe else '❌ UNSAFE'}")
    print(f"Findings: {len(findings)}\n")

    # Test 2: Dangerous content
    print("Test 2: Scanning content with secrets...")
    is_safe, findings = scanner.scan(SAMPLE_ANALYSIS)
    print(f"Result: {'✅ SAFE' if is_safe else '❌ UNSAFE'}")
    print(f"Findings: {len(findings)}")
    print("\nReport:")
    print(MultiLayerScanner.format_report(findings))

    # Test 3: With gitleaks (if available)
    print("\n\nTest 3: Testing gitleaks integration...")
    try:
        scanner_with_gitleaks = MultiLayerScanner(enable_gitleaks=True, enable_regex=True)
        is_safe, findings = scanner_with_gitleaks.scan(SAMPLE_ANALYSIS)
        print(f"Result: {'✅ SAFE' if is_safe else '❌ UNSAFE'}")
        print(f"Total findings: {len(findings)}")

        secret_findings = [f for f in findings if f.category == "secrets"]
        print(f"Secrets detected by gitleaks: {len(secret_findings)}")

        if secret_findings:
            print("\nSecret findings:")
            for finding in secret_findings[:3]:  # Show first 3
                print(f"  • {finding.rule_id}: {finding.description}")

    except RuntimeError as e:
        print(f"⚠️  Gitleaks not available: {e}")
        print("Install with: brew install gitleaks")


if __name__ == "__main__":
    main()
