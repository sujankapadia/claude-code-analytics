"""Regex-based pattern scanner for sensitive data detection."""

import re
from typing import Optional

from .base import ScanFinding, ScanSeverity


class RegexPatternScanner:
    """Custom regex-based pattern detection."""

    # Built-in patterns for common sensitive data
    BUILTIN_PATTERNS = [
        {
            "id": "email",
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "description": "Email address",
            "severity": ScanSeverity.HIGH,
            "redact": False,
        },
        {
            "id": "phone-us",
            "pattern": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "description": "US phone number",
            "severity": ScanSeverity.HIGH,
            "redact": False,
        },
        {
            "id": "phone-us-parentheses",
            "pattern": r"\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b",
            "description": "US phone number with parentheses",
            "severity": ScanSeverity.HIGH,
            "redact": False,
        },
        {
            "id": "ssn",
            "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
            "description": "Social Security Number",
            "severity": ScanSeverity.CRITICAL,
            "redact": True,
        },
        {
            "id": "credit-card",
            "pattern": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            "description": "Credit card number pattern",
            "severity": ScanSeverity.CRITICAL,
            "redact": True,
        },
        {
            "id": "ip-private",
            "pattern": r"\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|127\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
            "description": "Private IP address",
            "severity": ScanSeverity.MEDIUM,
            "redact": False,
        },
        {
            "id": "database-url",
            "pattern": r"(postgres|mysql|mongodb|redis|mariadb)://[^\s]+",
            "description": "Database connection string",
            "severity": ScanSeverity.HIGH,
            "redact": True,
        },
        {
            "id": "localhost-url",
            "pattern": r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
            "description": "Localhost URL",
            "severity": ScanSeverity.MEDIUM,
            "redact": False,
        },
        {
            "id": "jwt-token",
            "pattern": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
            "description": "JWT token",
            "severity": ScanSeverity.CRITICAL,
            "redact": True,
        },
        {
            "id": "bearer-token",
            "pattern": r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
            "description": "Bearer token",
            "severity": ScanSeverity.CRITICAL,
            "redact": True,
        },
    ]

    def __init__(
        self,
        custom_patterns: Optional[list[dict]] = None,
        allowed_patterns: Optional[dict[str, list[str]]] = None,
        use_builtin: bool = True,
    ):
        """
        Initialize regex scanner.

        Args:
            custom_patterns: Additional patterns to scan for
                Format: [{'id': str, 'pattern': str, 'description': str,
                         'severity': ScanSeverity, 'redact': bool}]
            allowed_patterns: Patterns to ignore per rule
                Format: {'email': ['example.com', 'test.com']}
            use_builtin: Whether to use built-in patterns
        """
        self.patterns = []

        if use_builtin:
            self.patterns.extend(self.BUILTIN_PATTERNS)

        if custom_patterns:
            self.patterns.extend(custom_patterns)

        self.allowed_patterns = allowed_patterns or {}

        # Compile all patterns for performance
        self.compiled_patterns = [
            {**pattern, "regex": re.compile(pattern["pattern"], re.IGNORECASE)}
            for pattern in self.patterns
        ]

    def scan(self, content: str, filename: str = "content.txt") -> list[ScanFinding]:
        """
        Scan content using regex patterns.

        Args:
            content: Text to scan
            filename: Filename for context

        Returns:
            List of findings
        """
        findings = []
        lines = content.split("\n")

        for pattern_def in self.compiled_patterns:
            pattern_id = pattern_def["id"]
            regex = pattern_def["regex"]
            description = pattern_def["description"]
            severity = pattern_def["severity"]
            redact = pattern_def["redact"]

            # Check each line
            for line_num, line in enumerate(lines, 1):
                for match in regex.finditer(line):
                    matched_text = match.group()

                    # Check if match is in allowed list
                    if self._is_allowed(pattern_id, matched_text):
                        continue

                    # Redact sensitive values if configured
                    display_text = matched_text
                    if redact:
                        if len(matched_text) > 20:
                            display_text = f"{matched_text[:8]}...{matched_text[-4:]}"
                        else:
                            display_text = "***REDACTED***"

                    findings.append(
                        ScanFinding(
                            category="custom",
                            severity=severity,
                            rule_id=pattern_id,
                            description=description,
                            matched_text=display_text,
                            line_number=line_num,
                            file_name=filename,
                            confidence=1.0,
                        )
                    )

        return findings

    def _is_allowed(self, pattern_id: str, matched_text: str) -> bool:
        """Check if a match should be ignored based on allowlist."""
        if pattern_id not in self.allowed_patterns:
            return False

        allowed = self.allowed_patterns[pattern_id]
        return any(allow in matched_text.lower() for allow in allowed)
