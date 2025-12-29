"""GitHub Gist publishing service with security scanning."""

import requests
from typing import Optional, Dict, Tuple, List
from datetime import datetime

from claude_code_analytics.scanner import MultiLayerScanner, ScanFinding


class SecurityError(Exception):
    """Raised when security scan detects blocking issues."""
    pass


class GistPublisher:
    """
    Service for publishing analysis results and sessions to GitHub Gists.

    Automatically scans content for secrets and PII before publishing.
    """

    GITHUB_API_URL = "https://api.github.com/gists"

    def __init__(
        self,
        github_token: str,
        scanner: Optional[MultiLayerScanner] = None
    ):
        """
        Initialize Gist publisher.

        Args:
            github_token: GitHub Personal Access Token with 'gist' scope
            scanner: MultiLayerScanner instance (creates default if not provided)
        """
        if not github_token:
            raise ValueError("GitHub token is required for publishing gists")

        self.github_token = github_token

        # Initialize scanner if not provided
        if scanner is None:
            self.scanner = MultiLayerScanner(
                enable_gitleaks=True,
                enable_regex=True
            )
        else:
            self.scanner = scanner

    def publish(
        self,
        analysis_content: str,
        session_content: Optional[str] = None,
        description: str = "Claude Code Analysis",
        is_public: bool = False,
        analysis_filename: str = "analysis.md",
        session_filename: str = "session.txt",
        skip_scan: bool = False
    ) -> Tuple[bool, str, List[ScanFinding]]:
        """
        Publish analysis and optional session to GitHub Gist.

        Args:
            analysis_content: The analysis markdown content
            session_content: Optional session transcript
            description: Gist description
            is_public: Whether to create public gist (default: secret)
            analysis_filename: Filename for analysis in gist
            session_filename: Filename for session in gist
            skip_scan: Skip security scan (NOT RECOMMENDED)

        Returns:
            Tuple of (success, result_message, all_findings)
            - success: True if published, False if blocked or failed
            - result_message: Gist URL on success, error message on failure
            - all_findings: List of all security findings (empty if skipped)

        Raises:
            SecurityError: If CRITICAL/HIGH severity issues found (unless skip_scan=True)
        """
        all_findings = []

        # Scan content for sensitive data
        if not skip_scan:
            files_to_scan = {
                analysis_filename: analysis_content
            }

            if session_content:
                files_to_scan[session_filename] = session_content

            all_safe, findings_by_file = self.scanner.scan_multiple(files_to_scan)

            # Collect all findings
            for file_findings in findings_by_file.values():
                all_findings.extend(file_findings)

            # Block if not safe
            if not all_safe:
                error_msg = ["❌ Cannot publish - sensitive data detected:\n"]
                for filename, file_findings in findings_by_file.items():
                    error_msg.append(f"\n📄 {filename}:")
                    error_msg.append(
                        MultiLayerScanner.format_report(file_findings)
                    )
                error_text = "\n".join(error_msg)
                return False, error_text, all_findings

        # Prepare gist files
        gist_files = {
            analysis_filename: {"content": analysis_content}
        }

        if session_content:
            gist_files[session_filename] = {"content": session_content}

        # Add auto-generated README with metadata
        readme_content = self._generate_readme(
            description=description,
            has_session=session_content is not None,
            analysis_filename=analysis_filename,
            session_filename=session_filename
        )
        gist_files["README.md"] = {"content": readme_content}

        # Create gist via GitHub API
        try:
            gist_url = self._create_gist(
                files=gist_files,
                description=description,
                is_public=is_public
            )
            return True, gist_url, all_findings

        except requests.exceptions.RequestException as e:
            error_msg = f"❌ Failed to publish gist: {str(e)}"
            return False, error_msg, all_findings

    def _create_gist(
        self,
        files: Dict[str, Dict[str, str]],
        description: str,
        is_public: bool
    ) -> str:
        """
        Create a gist via GitHub API.

        Args:
            files: Dict of filename -> {"content": content}
            description: Gist description
            is_public: Whether gist is public

        Returns:
            URL of created gist

        Raises:
            requests.exceptions.RequestException: On API failure
        """
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        data = {
            "description": description,
            "public": is_public,
            "files": files
        }

        response = requests.post(
            self.GITHUB_API_URL,
            headers=headers,
            json=data,
            timeout=30
        )

        # Handle errors
        if response.status_code == 401:
            raise requests.exceptions.RequestException(
                "Invalid GitHub token. Check your GITHUB_TOKEN in config."
            )
        elif response.status_code == 422:
            raise requests.exceptions.RequestException(
                "Invalid gist data. Check file contents and names."
            )
        elif response.status_code != 201:
            raise requests.exceptions.RequestException(
                f"GitHub API error: {response.status_code} - {response.text}"
            )

        # Extract gist URL from response
        gist_data = response.json()
        return gist_data["html_url"]

    def _generate_readme(
        self,
        description: str,
        has_session: bool,
        analysis_filename: str,
        session_filename: str
    ) -> str:
        """Generate README content for gist."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        readme = f"""# {description}

**Generated:** {timestamp}
**Tool:** [Claude Code Analytics](https://github.com/sujankapadia/claude-code-utils)

## Contents

- **{analysis_filename}** - AI-powered analysis results
"""

        if has_session:
            readme += f"- **{session_filename}** - Session transcript with context\n"

        readme += """
## About

This gist was automatically generated using Claude Code Analytics, a tool for capturing,
analyzing, and sharing AI development conversations from Claude Code.

All content was scanned for secrets, API keys, and PII before publication.

---

🤖 *Published via [Claude Code Analytics](https://github.com/sujankapadia/claude-code-utils)*
"""

        return readme
