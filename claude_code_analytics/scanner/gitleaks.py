"""Gitleaks-based secrets detection scanner."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .base import ScanFinding, ScanSeverity


class GitleaksScanner:
    """Wrapper for gitleaks binary to detect secrets."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize gitleaks scanner.

        Args:
            config_path: Optional path to .gitleaks.toml config file
        """
        self.config_path = config_path
        self.gitleaks_path = self._verify_installation()

    def _verify_installation(self) -> str:
        """
        Check if gitleaks is installed and return its absolute path.

        Returns:
            Absolute path to gitleaks executable

        Raises:
            RuntimeError: If gitleaks is not found or fails to run
        """
        # Find gitleaks in PATH
        gitleaks_path = shutil.which("gitleaks")
        if not gitleaks_path:
            raise RuntimeError("Gitleaks not found. Install with: brew install gitleaks")

        # Verify it works
        try:
            subprocess.run([gitleaks_path, "version"], capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Gitleaks found but failed to run: {e}") from e

        return gitleaks_path

    def scan(self, content: str, filename: str = "content.txt") -> list[ScanFinding]:
        """
        Scan content for secrets using gitleaks.

        Args:
            content: Text content to scan
            filename: Filename context (affects pattern matching)

        Returns:
            List of findings
        """
        findings = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write content to temp file
            file_path = Path(tmpdir) / filename
            file_path.write_text(content, encoding="utf-8")

            # Build gitleaks command
            cmd = [
                self.gitleaks_path,
                "detect",
                "--source",
                tmpdir,
                "--report-format",
                "json",
                "--report-path",
                f"{tmpdir}/report.json",
                "--no-git",
                "--exit-code",
                "0",  # Don't exit with error on findings
            ]

            if self.config_path:
                cmd.extend(["--config", self.config_path])

            # Run gitleaks
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode > 1:
                raise RuntimeError(f"Gitleaks error: {result.stderr}")

            # Parse report
            report_path = Path(tmpdir) / "report.json"
            if report_path.exists():
                report_content = report_path.read_text(encoding="utf-8")
                if report_content.strip():
                    gitleaks_findings = json.loads(report_content)
                    findings = self._convert_findings(gitleaks_findings, filename)

        return findings

    def _convert_findings(self, gitleaks_findings: list[dict], filename: str) -> list[ScanFinding]:
        """Convert gitleaks JSON findings to ScanFinding objects."""
        findings = []

        for gf in gitleaks_findings:
            # Redact the actual secret value
            secret = gf.get("Secret", "")
            redacted = f"{secret[:8]}...{secret[-4:]}" if len(secret) > 20 else "***REDACTED***"

            findings.append(
                ScanFinding(
                    category="secrets",
                    severity=ScanSeverity.CRITICAL,
                    rule_id=gf.get("RuleID", "unknown"),
                    description=gf.get("Description", "Secret detected"),
                    matched_text=redacted,
                    line_number=gf.get("StartLine"),
                    file_name=filename,
                    confidence=1.0,
                )
            )

        return findings
