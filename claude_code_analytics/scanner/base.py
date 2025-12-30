"""Base classes and types for security scanning."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ScanSeverity(Enum):
    """Severity levels for security findings."""

    CRITICAL = "critical"  # Secrets, credentials, SSNs
    HIGH = "high"  # PII like emails, phones
    MEDIUM = "medium"  # Internal IPs, localhost URLs
    LOW = "low"  # Informational patterns


@dataclass
class ScanFinding:
    """Represents a single security finding."""

    category: str  # "secrets", "pii", or "custom"
    severity: ScanSeverity
    rule_id: str  # Identifier for the rule
    description: str  # Human-readable description
    matched_text: str  # The matched content (may be redacted)
    line_number: Optional[int] = None
    file_name: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0 (used by Presidio)

    def __str__(self):
        location = f"{self.file_name}:{self.line_number}" if self.line_number else "unknown"
        return (
            f"[{self.severity.value.upper()}] {self.category}/{self.rule_id}\n"
            f"  Location: {location}\n"
            f"  Description: {self.description}\n"
            f"  Match: {self.matched_text}\n"
            f"  Confidence: {self.confidence:.2f}"
        )
