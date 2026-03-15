# Test Spec: test_analysis_service

## Purpose
Tests for AnalysisService — LLM-powered session analysis orchestration.

## Changes (current refactor)
Refactor: update all references from `claude_code_analytics.streamlit_app.*` to new package layout:
- Import paths: `streamlit_app.models` -> `models`, `streamlit_app.services` -> `services`
- Mock patch targets: `claude_code_analytics.streamlit_app.services.analysis_service.__file__` -> `claude_code_analytics.services.analysis_service.__file__`
- Path construction in fixtures: `/ "streamlit_app"` -> `/ "services"`

No behavior changes — pure import path refactor.

## Changes (prompts path fix)
Fix mock `__file__` paths after prompts directory resolution changed from
`parent.parent.parent / "prompts"` to `parent.parent / "prompts"`.
Remove extra `/ "services"` from mock file paths so `parent.parent` resolves
to the temp `claude_code_analytics/` directory where `prompts/` lives.
Also update fixture comment to reflect current directory structure.
