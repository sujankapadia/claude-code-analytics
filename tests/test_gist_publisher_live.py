"""Live integration test for GistPublisher with GitHub API.

WARNING: This test creates REAL gists on your GitHub account!
         Make sure you have a GITHUB_TOKEN set in your environment.

Run with: python tests/test_gist_publisher_live.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_code_analytics import config
from claude_code_analytics.streamlit_app.services import GistPublisher

# Test content samples
SAFE_ANALYSIS = """# Analysis: Testing Best Practices

## Overview
This session covered unit testing strategies and best practices.

## Key Insights

### 1. Test Pyramid
- Many unit tests (fast, isolated)
- Fewer integration tests (slower, more realistic)
- Minimal end-to-end tests (slowest, most comprehensive)

### 2. AAA Pattern
Structure tests using Arrange, Act, Assert pattern for clarity.

### 3. Test Naming
Use descriptive names that explain what and why:
- `test_user_login_with_valid_credentials_succeeds()`
- `test_payment_processing_with_insufficient_funds_fails()`

## Recommendations
1. Aim for 80%+ code coverage
2. Mock external dependencies
3. Test edge cases and error conditions
4. Keep tests fast and independent

## Next Steps
- Implement pytest fixtures for common test data
- Set up continuous integration
- Add property-based testing with Hypothesis
"""

DANGEROUS_ANALYSIS = """# Analysis: Authentication Implementation

## Configuration
Database: postgres://admin:SuperSecret123@prod.db.com:5432/app

API Keys:
- OpenAI: sk-proj-abcdef1234567890
- AWS: AKIAIOSFODNN7EXAMPLE

## Team Contacts
- Lead: john.doe@company.com (555-123-4567)
- DevOps: jane@company.com (555-987-6543)

## Implementation Notes
JWT Secret: myverysecretkey123456
Session Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature
"""


def test_publisher_initialization():
    """Test 1: Publisher initialization."""
    print("\n" + "=" * 60)
    print("Test 1: GistPublisher Initialization")
    print("=" * 60)

    if not config.GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not set in environment")
        print("   Set it in ~/.config/claude-code-analytics/.env")
        return False

    try:
        publisher = GistPublisher(github_token=config.GITHUB_TOKEN)
        print("✅ Publisher initialized successfully")
        print(f"   Scanner layers: {len(publisher.scanner.scanners)}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False


def test_safe_content_scan():
    """Test 2: Safe content should pass scan."""
    print("\n" + "=" * 60)
    print("Test 2: Safe Content Scanning")
    print("=" * 60)

    publisher = GistPublisher(github_token=config.GITHUB_TOKEN)

    # Scan without publishing
    scanner = publisher.scanner
    is_safe, findings = scanner.scan(SAFE_ANALYSIS, "analysis.md")

    if is_safe:
        print("✅ Safe content correctly identified")
        print(f"   Findings: {len(findings)} (all non-blocking)")
        return True
    else:
        print("❌ Safe content incorrectly flagged as unsafe")
        print(f"   Findings: {len(findings)}")
        for finding in findings:
            print(f"   - {finding.severity.value}: {finding.description}")
        return False


def test_dangerous_content_blocked():
    """Test 3: Dangerous content should be blocked."""
    print("\n" + "=" * 60)
    print("Test 3: Dangerous Content Blocking")
    print("=" * 60)

    publisher = GistPublisher(github_token=config.GITHUB_TOKEN)

    # Try to publish dangerous content (should be blocked)
    success, message, findings = publisher.publish(
        analysis_content=DANGEROUS_ANALYSIS,
        description="Test Gist - Should Be Blocked",
        is_public=False,
    )

    if not success and findings:
        print("✅ Dangerous content correctly blocked")
        print(f"   Total findings: {len(findings)}")
        print(f"\n{message}")
        return True
    else:
        print("❌ Dangerous content was NOT blocked!")
        print(f"   Success: {success}")
        print(f"   Findings: {len(findings)}")
        return False


def test_publish_to_github():
    """Test 4: Actually publish a test gist."""
    print("\n" + "=" * 60)
    print("Test 4: Publish Real Gist to GitHub")
    print("=" * 60)

    if not config.GITHUB_TOKEN:
        print("⚠️  Skipping - GITHUB_TOKEN not set")
        return None

    publisher = GistPublisher(github_token=config.GITHUB_TOKEN)

    # Publish safe content
    success, result, findings = publisher.publish(
        analysis_content=SAFE_ANALYSIS,
        description="Claude Code Analytics - Integration Test",
        is_public=False,  # Secret gist
        analysis_filename="test_analysis.md",
    )

    if success:
        print("✅ Gist published successfully!")
        print(f"   URL: {result}")
        print(f"   Findings: {len(findings)}")
        print("\n   ⚠️  Remember to delete this test gist from GitHub!")
        print(f"   Delete at: {result}")
        return result
    else:
        print("❌ Failed to publish gist")
        print(f"   Error: {result}")
        return None


def test_publish_with_session():
    """Test 5: Publish with session content."""
    print("\n" + "=" * 60)
    print("Test 5: Publish with Session Content")
    print("=" * 60)

    if not config.GITHUB_TOKEN:
        print("⚠️  Skipping - GITHUB_TOKEN not set")
        return None

    publisher = GistPublisher(github_token=config.GITHUB_TOKEN)

    session_transcript = """
Session Transcript - Testing Discussion

User: Let's discuss testing strategies
Assistant: Sure! I'd recommend following the test pyramid...
User: What about mocking?
Assistant: Mocking is essential for isolating units...
"""

    success, result, findings = publisher.publish(
        analysis_content=SAFE_ANALYSIS,
        session_content=session_transcript,
        description="Claude Code Analytics - Test with Session",
        is_public=False,
        analysis_filename="analysis.md",
        session_filename="transcript.txt",
    )

    if success:
        print("✅ Gist with session published successfully!")
        print(f"   URL: {result}")
        print("   Files: analysis.md, transcript.txt, README.md")
        print("\n   ⚠️  Remember to delete this test gist from GitHub!")
        return result
    else:
        print("❌ Failed to publish gist with session")
        print(f"   Error: {result}")
        return None


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GitHub Gist Publisher - Live Integration Tests")
    print("=" * 60)
    print("\n⚠️  WARNING: This will create REAL gists on GitHub!")
    print("   Make sure GITHUB_TOKEN is set in your config.\n")

    results = []
    gist_urls = []

    # Test 1: Initialization
    results.append(("Initialization", test_publisher_initialization()))

    if not results[0][1]:
        print("\n❌ Cannot proceed without valid GITHUB_TOKEN")
        return

    # Test 2: Safe content
    results.append(("Safe Content Scan", test_safe_content_scan()))

    # Test 3: Dangerous content blocking
    results.append(("Dangerous Content Block", test_dangerous_content_blocked()))

    # Test 4: Actual publish
    url = test_publish_to_github()
    results.append(("Publish to GitHub", url is not None))
    if url:
        gist_urls.append(url)

    # Test 5: Publish with session
    url = test_publish_with_session()
    results.append(("Publish with Session", url is not None))
    if url:
        gist_urls.append(url)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result is True)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"{status} - {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if gist_urls:
        print("\n" + "=" * 60)
        print("Created Gists (remember to delete!):")
        print("=" * 60)
        for url in gist_urls:
            print(f"  • {url}")
        print("\nTo delete, visit each URL and click 'Delete gist' button.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
