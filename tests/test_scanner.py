"""Unit tests for scanner module."""

from claude_code_analytics.scanner import (
    MultiLayerScanner,
    RegexPatternScanner,
    ScanFinding,
    ScanSeverity,
)


class TestRegexPatternScanner:
    """Tests for RegexPatternScanner."""

    def test_email_detection(self):
        """Test email address detection."""
        RegexPatternScanner()
        content = "Contact me at john.doe@example.com for details."

        is_safe, findings = MultiLayerScanner(enable_gitleaks=False, enable_regex=True).scan(
            content
        )

        assert not is_safe  # Email is HIGH severity
        assert len([f for f in findings if f.rule_id == "email"]) == 1
        assert findings[0].severity == ScanSeverity.HIGH
        assert "john.doe@example.com" in findings[0].matched_text

    def test_email_allowlist(self):
        """Test email allowlist functionality."""
        scanner = MultiLayerScanner(
            enable_gitleaks=False,
            enable_regex=True,
            regex_allowed_patterns={"email": ["example.com", "test.com"]},
        )

        content = "Contact: john@example.com, jane@real.com"
        is_safe, findings = scanner.scan(content)

        # Only jane@real.com should be detected
        email_findings = [f for f in findings if f.rule_id == "email"]
        assert len(email_findings) == 1
        assert "jane@real.com" in email_findings[0].matched_text

    def test_phone_number_detection(self):
        """Test US phone number detection."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)

        content = "Call me at 555-123-4567 or (555) 987-6543"
        is_safe, findings = scanner.scan(content)

        phone_findings = [f for f in findings if f.rule_id in ("phone-us", "phone-us-parentheses")]
        assert len(phone_findings) == 2

    def test_ssn_detection_and_redaction(self):
        """Test SSN detection and redaction."""
        scanner = RegexPatternScanner()
        content = "My SSN is 123-45-6789"

        findings = scanner.scan(content)

        ssn_findings = [f for f in findings if f.rule_id == "ssn"]
        assert len(ssn_findings) == 1
        assert ssn_findings[0].severity == ScanSeverity.CRITICAL
        assert ssn_findings[0].matched_text == "***REDACTED***"

    def test_credit_card_detection(self):
        """Test credit card number detection."""
        scanner = RegexPatternScanner()
        content = "Card: 4532-1234-5678-9010"

        findings = scanner.scan(content)

        cc_findings = [f for f in findings if f.rule_id == "credit-card"]
        assert len(cc_findings) == 1
        assert cc_findings[0].severity == ScanSeverity.CRITICAL

    def test_private_ip_detection(self):
        """Test private IP address detection."""
        scanner = RegexPatternScanner()
        content = "Server at 192.168.1.100 and 10.0.0.1"

        findings = scanner.scan(content)

        ip_findings = [f for f in findings if f.rule_id == "ip-private"]
        assert len(ip_findings) == 2
        assert ip_findings[0].severity == ScanSeverity.MEDIUM

    def test_database_url_detection(self):
        """Test database connection string detection."""
        scanner = RegexPatternScanner()
        content = "DB: postgres://user:pass@localhost/db"

        findings = scanner.scan(content)

        db_findings = [f for f in findings if f.rule_id == "database-url"]
        assert len(db_findings) == 1
        assert db_findings[0].severity == ScanSeverity.HIGH

    def test_localhost_url_detection(self):
        """Test localhost URL detection."""
        scanner = RegexPatternScanner()
        content = "Running at http://localhost:8501"

        findings = scanner.scan(content)

        localhost_findings = [f for f in findings if f.rule_id == "localhost-url"]
        assert len(localhost_findings) == 1
        assert localhost_findings[0].severity == ScanSeverity.MEDIUM

    def test_jwt_token_detection(self):
        """Test JWT token detection."""
        scanner = RegexPatternScanner()
        content = "Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"

        findings = scanner.scan(content)

        jwt_findings = [f for f in findings if f.rule_id == "jwt-token"]
        assert len(jwt_findings) == 1
        assert jwt_findings[0].severity == ScanSeverity.CRITICAL

    def test_bearer_token_detection(self):
        """Test Bearer token detection."""
        scanner = RegexPatternScanner()
        content = "Authorization: Bearer sk-1234567890abcdef"

        findings = scanner.scan(content)

        bearer_findings = [f for f in findings if f.rule_id == "bearer-token"]
        assert len(bearer_findings) == 1
        assert bearer_findings[0].severity == ScanSeverity.CRITICAL

    def test_custom_patterns(self):
        """Test custom pattern addition."""
        custom_patterns = [
            {
                "id": "test-pattern",
                "pattern": r"SECRET-\d+",
                "description": "Test secret pattern",
                "severity": ScanSeverity.HIGH,
                "redact": False,
            }
        ]

        scanner = RegexPatternScanner(custom_patterns=custom_patterns)
        content = "ID is SECRET-12345"

        findings = scanner.scan(content)

        custom_findings = [f for f in findings if f.rule_id == "test-pattern"]
        assert len(custom_findings) == 1
        assert "SECRET-12345" in custom_findings[0].matched_text

    def test_line_numbers(self):
        """Test that line numbers are correctly recorded."""
        scanner = RegexPatternScanner()
        content = "Line 1\nLine 2\nEmail: test@example.com\nLine 4"

        findings = scanner.scan(content)

        email_findings = [f for f in findings if f.rule_id == "email"]
        assert len(email_findings) == 1
        assert email_findings[0].line_number == 3


class TestMultiLayerScanner:
    """Tests for MultiLayerScanner."""

    def test_safe_content(self):
        """Test content with no sensitive data."""
        scanner = MultiLayerScanner(
            enable_gitleaks=False,  # Skip gitleaks for speed
            enable_regex=True,
            regex_allowed_patterns={"localhost-url": ["localhost", "127.0.0.1"]},
        )

        content = "This is safe content with no secrets at http://localhost:8501"
        is_safe, findings = scanner.scan(content)

        # Localhost URL is allowed, so should be safe
        assert is_safe
        assert len(findings) == 0

    def test_blocking_severity(self):
        """Test that CRITICAL and HIGH findings block publication."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)

        # HIGH severity (email)
        content = "Email: john@example.com"
        is_safe, findings = scanner.scan(content)
        assert not is_safe

        # CRITICAL severity (SSN)
        content = "SSN: 123-45-6789"
        is_safe, findings = scanner.scan(content)
        assert not is_safe

    def test_non_blocking_severity(self):
        """Test that MEDIUM and LOW findings don't block."""
        scanner = MultiLayerScanner(
            enable_gitleaks=False,
            enable_regex=True,
            regex_allowed_patterns={
                "email": ["example.com"],  # Allow emails
                "phone-us": [],
                "phone-us-parentheses": [],
            },
        )

        # MEDIUM severity (private IP)
        content = "Server: 192.168.1.100"
        is_safe, findings = scanner.scan(content)

        assert is_safe  # Should not block
        assert len(findings) > 0  # But should still report
        assert all(f.severity in (ScanSeverity.MEDIUM, ScanSeverity.LOW) for f in findings)

    def test_scan_multiple_files(self):
        """Test scanning multiple files."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=True)

        files = {
            "file1.txt": "Safe content",
            "file2.txt": "Email: test@example.com",
            "file3.txt": "IP: 192.168.1.1",
        }

        all_safe, findings_by_file = scanner.scan_multiple(files)

        assert not all_safe  # file2 has email (HIGH)
        assert "file1.txt" not in findings_by_file  # No findings
        assert "file2.txt" in findings_by_file
        assert "file3.txt" in findings_by_file

    def test_format_report_empty(self):
        """Test report formatting with no findings."""
        report = MultiLayerScanner.format_report([])
        assert "✅ No sensitive data detected" in report

    def test_format_report_with_findings(self):
        """Test report formatting with findings."""
        findings = [
            ScanFinding(
                category="secrets",
                severity=ScanSeverity.CRITICAL,
                rule_id="test-secret",
                description="Test secret",
                matched_text="***REDACTED***",
                line_number=1,
                file_name="test.txt",
            ),
            ScanFinding(
                category="custom",
                severity=ScanSeverity.MEDIUM,
                rule_id="ip-private",
                description="Private IP",
                matched_text="192.168.1.1",
                line_number=5,
                file_name="test.txt",
            ),
        ]

        report = MultiLayerScanner.format_report(findings)

        assert "❌ Sensitive data detected" in report
        assert "CRITICAL (1)" in report
        assert "MEDIUM (1)" in report
        assert "test-secret" in report
        assert "ip-private" in report

    def test_no_scanners_enabled(self):
        """Test scanner with all layers disabled."""
        scanner = MultiLayerScanner(enable_gitleaks=False, enable_regex=False)

        content = "API Key: sk-1234567890"
        is_safe, findings = scanner.scan(content)

        # No scanners, so no findings
        assert is_safe
        assert len(findings) == 0
