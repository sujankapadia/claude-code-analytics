# Python Multi-Layer Scanner Implementation

## Overview

This document describes a Python-based multi-layer scanner for detecting secrets, PII, and sensitive patterns in LLM-generated content before publication. The scanner combines three layers:

1. **Gitleaks** - Industry-standard secrets detection
2. **Presidio** - Microsoft's PII detection framework (optional but recommended)
3. **Custom Regex** - Domain-specific patterns

## Prerequisites

### Required: Gitleaks Binary
```bash
# macOS
brew install gitleaks

# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.4/gitleaks_8.18.4_linux_x64.tar.gz
tar -xzf gitleaks_8.18.4_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

### Python Dependencies

**Minimal (gitleaks + regex only):**
```bash
pip install --break-system-packages
# No additional packages needed
```

**With Presidio (recommended for comprehensive PII detection):**
```bash
pip install --break-system-packages presidio-analyzer presidio-anonymizer spacy
python -m spacy download en_core_web_lg
```

## Core Scanner Implementation

### Data Structures

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple


class ScanSeverity(Enum):
    """Severity levels for findings."""
    CRITICAL = "critical"  # Secrets, credentials, SSNs
    HIGH = "high"          # PII like emails, phones
    MEDIUM = "medium"      # Internal IPs, localhost URLs
    LOW = "low"            # Informational patterns


@dataclass
class ScanFinding:
    """Represents a single security finding."""
    category: str          # "secrets", "pii", or "custom"
    severity: ScanSeverity
    rule_id: str          # Identifier for the rule
    description: str       # Human-readable description
    matched_text: str      # The matched content (may be redacted)
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
```

### Layer 1: Gitleaks Integration

```python
import subprocess
import json
import tempfile
from pathlib import Path


class GitleaksScanner:
    """Wrapper for gitleaks binary."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize gitleaks scanner.
        
        Args:
            config_path: Optional path to .gitleaks.toml config file
        """
        self.config_path = config_path
        self._verify_installation()
    
    def _verify_installation(self) -> None:
        """Check if gitleaks is installed."""
        try:
            subprocess.run(
                ["gitleaks", "version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "Gitleaks not found. Install with: brew install gitleaks"
            )
    
    def scan(
        self,
        content: str,
        filename: str = "content.txt"
    ) -> List[ScanFinding]:
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
            file_path.write_text(content, encoding='utf-8')
            
            # Build gitleaks command
            cmd = [
                "gitleaks",
                "detect",
                "--source", tmpdir,
                "--report-format", "json",
                "--report-path", f"{tmpdir}/report.json",
                "--no-git",
                "--exit-code", "0"  # Don't exit with error on findings
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
                report_content = report_path.read_text(encoding='utf-8')
                if report_content.strip():
                    gitleaks_findings = json.loads(report_content)
                    findings = self._convert_findings(gitleaks_findings, filename)
        
        return findings
    
    def _convert_findings(
        self,
        gitleaks_findings: List[Dict],
        filename: str
    ) -> List[ScanFinding]:
        """Convert gitleaks JSON findings to ScanFinding objects."""
        findings = []
        
        for gf in gitleaks_findings:
            # Redact the actual secret value
            secret = gf.get('Secret', '')
            if len(secret) > 20:
                redacted = f"{secret[:8]}...{secret[-4:]}"
            else:
                redacted = "***REDACTED***"
            
            findings.append(ScanFinding(
                category="secrets",
                severity=ScanSeverity.CRITICAL,
                rule_id=gf.get('RuleID', 'unknown'),
                description=gf.get('Description', 'Secret detected'),
                matched_text=redacted,
                line_number=gf.get('StartLine'),
                file_name=filename,
                confidence=1.0
            ))
        
        return findings
```

### Layer 2: Presidio PII Detection

```python
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


class PresidioScanner:
    """PII detection using Microsoft Presidio."""
    
    # Map Presidio entity types to our severity levels
    ENTITY_SEVERITY = {
        'CREDIT_CARD': ScanSeverity.CRITICAL,
        'CRYPTO': ScanSeverity.CRITICAL,
        'US_SSN': ScanSeverity.CRITICAL,
        'US_BANK_NUMBER': ScanSeverity.CRITICAL,
        'EMAIL_ADDRESS': ScanSeverity.HIGH,
        'PHONE_NUMBER': ScanSeverity.HIGH,
        'PERSON': ScanSeverity.HIGH,
        'US_DRIVER_LICENSE': ScanSeverity.HIGH,
        'IP_ADDRESS': ScanSeverity.MEDIUM,
        'LOCATION': ScanSeverity.MEDIUM,
        'DATE_TIME': ScanSeverity.LOW,
        'URL': ScanSeverity.LOW,
    }
    
    def __init__(
        self,
        confidence_threshold: float = 0.5,
        allowed_entities: Optional[Set[str]] = None
    ):
        """
        Initialize Presidio scanner.
        
        Args:
            confidence_threshold: Minimum confidence score (0.0-1.0)
            allowed_entities: Entity types to ignore (e.g., {'DATE_TIME'})
        """
        if not PRESIDIO_AVAILABLE:
            raise ImportError(
                "Presidio not available. Install with: "
                "pip install presidio-analyzer presidio-anonymizer spacy && "
                "python -m spacy download en_core_web_lg"
            )
        
        self.confidence_threshold = confidence_threshold
        self.allowed_entities = allowed_entities or set()
        
        # Initialize Presidio analyzer
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    
    def scan(
        self,
        content: str,
        filename: str = "content.txt"
    ) -> List[ScanFinding]:
        """
        Scan content for PII using Presidio.
        
        Args:
            content: Text to scan
            filename: Filename for context
        
        Returns:
            List of PII findings
        """
        findings = []
        
        # Analyze with Presidio
        results = self.analyzer.analyze(
            text=content,
            language='en',
            entities=list(self.ENTITY_SEVERITY.keys())
        )
        
        lines = content.split('\n')
        
        for result in results:
            # Skip if below confidence threshold
            if result.score < self.confidence_threshold:
                continue
            
            # Skip allowed entities
            if result.entity_type in self.allowed_entities:
                continue
            
            # Find line number
            char_count = 0
            line_number = 1
            for i, line in enumerate(lines, 1):
                char_count += len(line) + 1  # +1 for newline
                if char_count > result.start:
                    line_number = i
                    break
            
            # Extract matched text
            matched_text = content[result.start:result.end]
            
            # Redact sensitive values
            if result.entity_type in {'CREDIT_CARD', 'US_SSN', 'CRYPTO'}:
                matched_text = "***REDACTED***"
            
            findings.append(ScanFinding(
                category="pii",
                severity=self.ENTITY_SEVERITY.get(
                    result.entity_type,
                    ScanSeverity.MEDIUM
                ),
                rule_id=result.entity_type.lower(),
                description=f"{result.entity_type.replace('_', ' ').title()} detected",
                matched_text=matched_text,
                line_number=line_number,
                file_name=filename,
                confidence=result.score
            ))
        
        return findings
```

### Layer 3: Regex Pattern Scanner

```python
import re


class RegexPatternScanner:
    """Custom regex-based pattern detection."""
    
    # Built-in patterns for common sensitive data
    BUILTIN_PATTERNS = [
        {
            'id': 'email',
            'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'description': 'Email address',
            'severity': ScanSeverity.HIGH,
            'redact': False,
        },
        {
            'id': 'phone-us',
            'pattern': r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'description': 'US phone number',
            'severity': ScanSeverity.HIGH,
            'redact': False,
        },
        {
            'id': 'phone-us-parentheses',
            'pattern': r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b',
            'description': 'US phone number with parentheses',
            'severity': ScanSeverity.HIGH,
            'redact': False,
        },
        {
            'id': 'ssn',
            'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
            'description': 'Social Security Number',
            'severity': ScanSeverity.CRITICAL,
            'redact': True,
        },
        {
            'id': 'credit-card',
            'pattern': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'description': 'Credit card number pattern',
            'severity': ScanSeverity.CRITICAL,
            'redact': True,
        },
        {
            'id': 'ip-private',
            'pattern': r'\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|127\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
            'description': 'Private IP address',
            'severity': ScanSeverity.MEDIUM,
            'redact': False,
        },
        {
            'id': 'database-url',
            'pattern': r'(postgres|mysql|mongodb|redis|mariadb)://[^\s]+',
            'description': 'Database connection string',
            'severity': ScanSeverity.HIGH,
            'redact': True,
        },
        {
            'id': 'localhost-url',
            'pattern': r'https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?',
            'description': 'Localhost URL',
            'severity': ScanSeverity.MEDIUM,
            'redact': False,
        },
        {
            'id': 'jwt-token',
            'pattern': r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
            'description': 'JWT token',
            'severity': ScanSeverity.CRITICAL,
            'redact': True,
        },
        {
            'id': 'bearer-token',
            'pattern': r'Bearer\s+[A-Za-z0-9\-._~+/]+=*',
            'description': 'Bearer token',
            'severity': ScanSeverity.CRITICAL,
            'redact': True,
        },
    ]
    
    def __init__(
        self,
        custom_patterns: Optional[List[Dict]] = None,
        allowed_patterns: Optional[Dict[str, List[str]]] = None,
        use_builtin: bool = True
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
            {
                **pattern,
                'regex': re.compile(pattern['pattern'], re.IGNORECASE)
            }
            for pattern in self.patterns
        ]
    
    def scan(
        self,
        content: str,
        filename: str = "content.txt"
    ) -> List[ScanFinding]:
        """
        Scan content using regex patterns.
        
        Args:
            content: Text to scan
            filename: Filename for context
        
        Returns:
            List of findings
        """
        findings = []
        lines = content.split('\n')
        
        for pattern_def in self.compiled_patterns:
            pattern_id = pattern_def['id']
            regex = pattern_def['regex']
            description = pattern_def['description']
            severity = pattern_def['severity']
            redact = pattern_def['redact']
            
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
                    
                    findings.append(ScanFinding(
                        category="custom",
                        severity=severity,
                        rule_id=pattern_id,
                        description=description,
                        matched_text=display_text,
                        line_number=line_num,
                        file_name=filename,
                        confidence=1.0
                    ))
        
        return findings
    
    def _is_allowed(self, pattern_id: str, matched_text: str) -> bool:
        """Check if a match should be ignored based on allowlist."""
        if pattern_id not in self.allowed_patterns:
            return False
        
        allowed = self.allowed_patterns[pattern_id]
        return any(allow in matched_text.lower() for allow in allowed)
```

### Unified Scanner

```python
class MultiLayerScanner:
    """
    Unified scanner combining gitleaks, Presidio, and regex patterns.
    """
    
    def __init__(
        self,
        enable_gitleaks: bool = True,
        enable_presidio: bool = True,
        enable_regex: bool = True,
        gitleaks_config: Optional[str] = None,
        presidio_confidence: float = 0.5,
        presidio_allowed_entities: Optional[Set[str]] = None,
        custom_patterns: Optional[List[Dict]] = None,
        regex_allowed_patterns: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize multi-layer scanner.
        
        Args:
            enable_gitleaks: Use gitleaks for secrets detection
            enable_presidio: Use Presidio for PII detection
            enable_regex: Use regex patterns
            gitleaks_config: Path to .gitleaks.toml
            presidio_confidence: Minimum confidence for Presidio (0.0-1.0)
            presidio_allowed_entities: Presidio entity types to ignore
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
        
        if enable_presidio:
            if PRESIDIO_AVAILABLE:
                try:
                    self.scanners.append(
                        PresidioScanner(
                            confidence_threshold=presidio_confidence,
                            allowed_entities=presidio_allowed_entities
                        )
                    )
                except Exception as e:
                    print(f"Warning: Presidio disabled - {e}")
            else:
                print("Warning: Presidio not available, skipping PII detection")
        
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
```

## Usage Examples

### Example 1: Basic Usage (All Layers)

```python
# Initialize scanner with all layers
scanner = MultiLayerScanner(
    enable_gitleaks=True,
    enable_presidio=True,
    enable_regex=True
)

# Scan content
content = """
# Analysis
User email: john.doe@company.com
AWS Key: AKIAIOSFODNN7EXAMPLE
Database: postgres://admin:password@db.internal.com/prod
Internal IP: 192.168.1.100
"""

is_safe, findings = scanner.scan(content, filename="analysis.md")

# Print report
print(MultiLayerScanner.format_report(findings))

# Check if safe to publish
if not is_safe:
    print("\n⚠️  Cannot publish - blocking issues found")
    exit(1)
else:
    print("\n✅ Safe to publish")
```

### Example 2: Gitleaks + Regex Only (No Presidio)

```python
# Lighter scanner without Presidio dependency
scanner = MultiLayerScanner(
    enable_gitleaks=True,
    enable_presidio=False,
    enable_regex=True,
    regex_allowed_patterns={
        'email': ['example.com', 'test.com']  # Ignore example emails
    }
)

is_safe, findings = scanner.scan(content)
```

### Example 3: Custom Patterns

```python
# Add company-specific patterns
custom_patterns = [
    {
        'id': 'company-domain',
        'pattern': r'chariot-solutions\.com',
        'description': 'Company domain reference',
        'severity': ScanSeverity.MEDIUM,
        'redact': False
    },
    {
        'id': 'project-id',
        'pattern': r'PROJ-\d{6}',
        'description': 'Internal project ID',
        'severity': ScanSeverity.LOW,
        'redact': False
    },
    {
        'id': 'api-endpoint',
        'pattern': r'https://api\.internal\.company\.com/[^\s]+',
        'description': 'Internal API endpoint',
        'severity': ScanSeverity.HIGH,
        'redact': True
    }
]

scanner = MultiLayerScanner(
    enable_gitleaks=True,
    enable_presidio=False,
    enable_regex=True,
    custom_patterns=custom_patterns
)

is_safe, findings = scanner.scan(content)
```

### Example 4: Scan Multiple Files

```python
# Scan analysis and session together
files = {
    "analysis.md": "# Session Analysis\n...",
    "session.txt": "Full conversation transcript...",
    "summary.md": "Executive summary..."
}

scanner = MultiLayerScanner()
all_safe, findings_by_file = scanner.scan_multiple(files)

if not all_safe:
    for filename, findings in findings_by_file.items():
        print(f"\n{filename}:")
        print(MultiLayerScanner.format_report(findings))
    exit(1)
```

### Example 5: With Custom Gitleaks Config

```python
# Use custom .gitleaks.toml configuration
scanner = MultiLayerScanner(
    enable_gitleaks=True,
    gitleaks_config=".gitleaks.toml",
    enable_presidio=True,
    presidio_confidence=0.7,  # Higher confidence threshold
    presidio_allowed_entities={'DATE_TIME', 'URL'}  # Ignore dates/URLs
)

is_safe, findings = scanner.scan(content)
```

### Example 6: Configuration-Driven Scanner

```python
# Load configuration from dict or YAML
config = {
    'gitleaks': {
        'enabled': True,
        'config_path': '.gitleaks.toml'
    },
    'presidio': {
        'enabled': True,
        'confidence': 0.6,
        'allowed_entities': ['DATE_TIME', 'LOCATION']
    },
    'regex': {
        'enabled': True,
        'allowed_patterns': {
            'email': ['example.com', 'test.com'],
            'ip-private': ['192.168.1.1']
        },
        'custom_patterns': [
            {
                'id': 'internal-ticket',
                'pattern': r'TICKET-\d+',
                'description': 'Internal ticket reference',
                'severity': ScanSeverity.LOW,
                'redact': False
            }
        ]
    }
}

scanner = MultiLayerScanner(
    enable_gitleaks=config['gitleaks']['enabled'],
    gitleaks_config=config['gitleaks'].get('config_path'),
    enable_presidio=config['presidio']['enabled'],
    presidio_confidence=config['presidio']['confidence'],
    presidio_allowed_entities=set(config['presidio']['allowed_entities']),
    enable_regex=config['regex']['enabled'],
    custom_patterns=config['regex'].get('custom_patterns'),
    regex_allowed_patterns=config['regex'].get('allowed_patterns')
)
```

## Integration Pattern for claude-code-utils

### Recommended File Structure

```
claude_code_utils/
├── scanner/
│   ├── __init__.py
│   ├── base.py           # ScanFinding, ScanSeverity classes
│   ├── gitleaks.py       # GitleaksScanner
│   ├── presidio.py       # PresidioScanner
│   ├── regex.py          # RegexPatternScanner
│   └── multi_layer.py    # MultiLayerScanner
└── gist/
    └── publisher.py      # GistPublisher with scanning
```

### Gist Publisher Integration

```python
# In gist/publisher.py
from ..scanner import MultiLayerScanner, ScanSeverity

class GistPublisher:
    def __init__(self, github_token: str, scanner_config: Optional[Dict] = None):
        self.github_token = github_token
        
        # Initialize scanner
        if scanner_config:
            self.scanner = MultiLayerScanner(**scanner_config)
        else:
            # Default configuration
            self.scanner = MultiLayerScanner(
                enable_gitleaks=True,
                enable_presidio=False,  # Optional dependency
                enable_regex=True
            )
    
    def publish(
        self,
        analysis: str,
        session: str,
        description: str = "Claude Code Analysis",
        skip_scan: bool = False
    ) -> str:
        """
        Publish to gist after security scan.
        
        Returns:
            Gist URL
        
        Raises:
            SecurityError: If sensitive data detected
        """
        if not skip_scan:
            files = {
                "analysis.md": analysis,
                "session.txt": session
            }
            
            all_safe, findings = self.scanner.scan_multiple(files)
            
            if not all_safe:
                error_msg = ["Cannot publish - sensitive data detected:\n"]
                for filename, file_findings in findings.items():
                    error_msg.append(f"\n{filename}:")
                    error_msg.append(
                        MultiLayerScanner.format_report(file_findings)
                    )
                raise SecurityError("\n".join(error_msg))
        
        # Proceed with publication
        return self._create_gist(analysis, session, description)
    
    def _create_gist(self, analysis: str, session: str, description: str):
        # Implementation details
        pass


class SecurityError(Exception):
    """Raised when security scan fails."""
    pass
```

## Performance Considerations

### Scanning Speed

- **Gitleaks**: ~100-500ms for typical files
- **Presidio**: ~1-3 seconds (NLP processing)
- **Regex**: <100ms

**Recommendation**: For real-time use (pre-commit hooks), consider gitleaks + regex only. Use Presidio for batch processing or when publishing.

### Memory Usage

- **Gitleaks**: Minimal (subprocess)
- **Presidio**: ~500MB (spaCy model)
- **Regex**: Minimal

### Optimization Tips

1. **Lazy Load Presidio**: Only initialize when needed
2. **Compile Patterns Once**: Reuse scanner instances
3. **Async Scanning**: Process multiple files in parallel
4. **Cache Results**: For unchanged content

```python
# Lazy loading example
class LazyPresidioScanner:
    def __init__(self):
        self._scanner = None
    
    @property
    def scanner(self):
        if self._scanner is None:
            if PRESIDIO_AVAILABLE:
                self._scanner = PresidioScanner()
        return self._scanner
```

## Testing

### Unit Test Example

```python
import pytest
from scanner import MultiLayerScanner, ScanSeverity

def test_email_detection():
    scanner = MultiLayerScanner(
        enable_gitleaks=False,
        enable_presidio=False,
        enable_regex=True
    )
    
    content = "Contact me at john@example.com"
    is_safe, findings = scanner.scan(content)
    
    assert not is_safe
    assert len(findings) == 1
    assert findings[0].rule_id == 'email'
    assert findings[0].severity == ScanSeverity.HIGH


def test_allowed_emails():
    scanner = MultiLayerScanner(
        enable_gitleaks=False,
        enable_presidio=False,
        enable_regex=True,
        regex_allowed_patterns={
            'email': ['example.com']
        }
    )
    
    content = "Contact me at john@example.com"
    is_safe, findings = scanner.scan(content)
    
    assert is_safe
    assert len(findings) == 0


def test_secrets_detection():
    scanner = MultiLayerScanner(
        enable_gitleaks=True,
        enable_presidio=False,
        enable_regex=False
    )
    
    content = 'api_key = "sk-1234567890abcdef"'
    is_safe, findings = scanner.scan(content)
    
    assert not is_safe
    assert any(f.category == 'secrets' for f in findings)
```

## Error Handling

```python
# Graceful degradation
try:
    scanner = MultiLayerScanner(
        enable_gitleaks=True,
        enable_presidio=True,
        enable_regex=True
    )
except RuntimeError as e:
    # Gitleaks not available
    print(f"Warning: {e}")
    scanner = MultiLayerScanner(
        enable_gitleaks=False,
        enable_presidio=False,
        enable_regex=True
    )

# Check what's enabled
if not scanner.scanners:
    raise RuntimeError("No scanners available - cannot perform security checks")
```

## Configuration File Format

### YAML Example (.claude-scanner.yaml)

```yaml
scanning:
  gitleaks:
    enabled: true
    config_path: .gitleaks.toml  # optional
  
  presidio:
    enabled: false  # optional, requires additional deps
    confidence_threshold: 0.6
    allowed_entities:
      - DATE_TIME
      - URL
  
  regex:
    enabled: true
    allowed_patterns:
      email:
        - example.com
        - test.com
      ip-private:
        - 192.168.1.1
        - 127.0.0.1
    
    custom_patterns:
      - id: company-domain
        pattern: 'mycompany\.com'
        description: Company domain reference
        severity: medium
        redact: false
      
      - id: internal-endpoint
        pattern: 'https://internal\.api\.company\.com'
        description: Internal API endpoint
        severity: high
        redact: true
```

### Loading Configuration

```python
import yaml

def load_scanner_from_config(config_path: str) -> MultiLayerScanner:
    """Load scanner configuration from YAML file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    scan_config = config.get('scanning', {})
    
    # Parse gitleaks config
    gitleaks_cfg = scan_config.get('gitleaks', {})
    
    # Parse presidio config
    presidio_cfg = scan_config.get('presidio', {})
    allowed_entities = presidio_cfg.get('allowed_entities', [])
    
    # Parse regex config
    regex_cfg = scan_config.get('regex', {})
    custom_patterns = []
    for p in regex_cfg.get('custom_patterns', []):
        custom_patterns.append({
            'id': p['id'],
            'pattern': p['pattern'],
            'description': p['description'],
            'severity': ScanSeverity[p['severity'].upper()],
            'redact': p.get('redact', False)
        })
    
    return MultiLayerScanner(
        enable_gitleaks=gitleaks_cfg.get('enabled', True),
        gitleaks_config=gitleaks_cfg.get('config_path'),
        enable_presidio=presidio_cfg.get('enabled', False),
        presidio_confidence=presidio_cfg.get('confidence_threshold', 0.5),
        presidio_allowed_entities=set(allowed_entities),
        enable_regex=regex_cfg.get('enabled', True),
        custom_patterns=custom_patterns,
        regex_allowed_patterns=regex_cfg.get('allowed_patterns')
    )
```
