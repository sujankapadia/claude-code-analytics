"""Multi-layer scanner orchestrator combining multiple scanning methods."""

from typing import List, Optional, Dict, Tuple, Set

from .base import ScanFinding, ScanSeverity
from .gitleaks import GitleaksScanner
from .regex_scanner import RegexPatternScanner


class MultiLayerScanner:
    """
    Unified scanner combining gitleaks and regex patterns.

    Presidio support can be added in the future as an optional layer.
    """

    def __init__(
        self,
        enable_gitleaks: bool = True,
        enable_regex: bool = True,
        gitleaks_config: Optional[str] = None,
        custom_patterns: Optional[List[Dict]] = None,
        regex_allowed_patterns: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize multi-layer scanner.

        Args:
            enable_gitleaks: Use gitleaks for secrets detection
            enable_regex: Use regex patterns
            gitleaks_config: Path to .gitleaks.toml
            custom_patterns: Additional regex patterns
            regex_allowed_patterns: Allowlist for regex patterns
        """
        self.scanners = []

        # Initialize enabled scanners
        if enable_gitleaks:
            try:
                self.scanners.append(
                    GitleaksScanner(config_path=gitleaks_config)
                )
            except RuntimeError as e:
                print(f"Warning: Gitleaks disabled - {e}")

        if enable_regex:
            self.scanners.append(
                RegexPatternScanner(
                    custom_patterns=custom_patterns,
                    allowed_patterns=regex_allowed_patterns
                )
            )

    def scan(
        self,
        content: str,
        filename: str = "content.txt"
    ) -> Tuple[bool, List[ScanFinding]]:
        """
        Scan content through all enabled layers.

        Args:
            content: Text to scan
            filename: Filename for context

        Returns:
            Tuple of (is_safe, findings)
            - is_safe: True if no CRITICAL or HIGH severity findings
            - findings: All findings from all scanners
        """
        all_findings = []

        # Run all scanners
        for scanner in self.scanners:
            findings = scanner.scan(content, filename)
            all_findings.extend(findings)

        # Determine if content is safe to publish
        # Block on CRITICAL and HIGH severity
        blocking_findings = [
            f for f in all_findings
            if f.severity in (ScanSeverity.CRITICAL, ScanSeverity.HIGH)
        ]

        is_safe = len(blocking_findings) == 0

        return is_safe, all_findings

    def scan_multiple(
        self,
        contents: Dict[str, str]
    ) -> Tuple[bool, Dict[str, List[ScanFinding]]]:
        """
        Scan multiple files.

        Args:
            contents: Dict mapping filename to content

        Returns:
            Tuple of (all_safe, findings_by_file)
        """
        all_findings = {}
        all_safe = True

        for filename, content in contents.items():
            is_safe, findings = self.scan(content, filename)

            if not is_safe:
                all_safe = False

            if findings:
                all_findings[filename] = findings

        return all_safe, all_findings

    @staticmethod
    def format_report(findings: List[ScanFinding]) -> str:
        """Format findings into human-readable report."""
        if not findings:
            return "✅ No sensitive data detected"

        # Group by severity
        by_severity = {
            ScanSeverity.CRITICAL: [],
            ScanSeverity.HIGH: [],
            ScanSeverity.MEDIUM: [],
            ScanSeverity.LOW: []
        }

        for finding in findings:
            by_severity[finding.severity].append(finding)

        lines = ["❌ Sensitive data detected:\n"]

        for severity in [ScanSeverity.CRITICAL, ScanSeverity.HIGH,
                        ScanSeverity.MEDIUM, ScanSeverity.LOW]:
            items = by_severity[severity]
            if items:
                lines.append(f"\n{severity.value.upper()} ({len(items)}):")
                for finding in items:
                    lines.append(
                        f"  • {finding.category}/{finding.rule_id}: "
                        f"{finding.description}"
                    )
                    if finding.line_number:
                        lines.append(
                            f"    Line {finding.line_number}: "
                            f"{finding.matched_text}"
                        )
                    else:
                        lines.append(f"    Match: {finding.matched_text}")
                    if finding.confidence < 1.0:
                        lines.append(
                            f"    Confidence: {finding.confidence:.0%}"
                        )

        return "\n".join(lines)
