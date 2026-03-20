# Test Spec: test_analysis_router.py

## Purpose
Tests for security features in the analysis router: SSRF validation on user-supplied base URLs and localhost restriction on the publish endpoint.

## Test Cases

### TestValidateBaseUrl
- `test_accepts_ollama_localhost` — Accepts `http://localhost:11434/v1` (allowed local provider port)
- `test_accepts_lm_studio_localhost` — Accepts `http://localhost:1234/v1` (allowed local provider port)
- `test_accepts_vllm_localhost` — Accepts `http://localhost:8001/v1` (allowed local provider port)
- `test_accepts_openrouter` — Accepts `https://openrouter.ai/api/v1` (public HTTPS URL)
- `test_rejects_file_scheme` — Rejects `file:///etc/passwd` (only http/https allowed)
- `test_rejects_ftp_scheme` — Rejects `ftp://example.com/data` (only http/https allowed)
- `test_rejects_cloud_metadata_ip` — Rejects `http://169.254.169.254/latest/meta-data` (link-local cloud metadata)
- `test_rejects_no_hostname` — Rejects `http:///path/only` (missing hostname)
- `test_rejects_private_ip_10` — Rejects `http://10.0.0.1/v1` (private 10.x range)
- `test_rejects_private_ip_192_168` — Rejects `http://192.168.1.1/v1` (private 192.168.x range)
- `test_rejects_localhost_on_disallowed_port` — Rejects localhost on port 9999 (not in allowed set)
- `test_rejects_localhost_default_port` — Rejects `http://localhost/` (port 80 not in allowed set)

### TestPublishLocalhostRestriction
- `test_publish_rejects_non_localhost` — Returns 403 when request comes from a non-loopback IP (203.0.113.1)
- `test_publish_allows_localhost` — Does NOT return 403 from 127.0.0.1 (gets 400 for missing GITHUB_TOKEN instead)
- `test_publish_allows_ipv6_localhost` — Does NOT return 403 from ::1 (gets 400 for missing GITHUB_TOKEN instead)

## Notes
- `validate_base_url` is tested as a pure unit by importing it directly
- Publish endpoint tests inject fake client IPs by wrapping the ASGI app to modify the scope
- Publish localhost tests patch `config.GITHUB_TOKEN = None` to verify the request passes the 403 gate and hits the next check (400)

## Changes
- 2026-03-20: Initial spec
- 2026-03-20: Fix mock path for GITHUB_TOKEN in publish localhost and IPv6 tests
