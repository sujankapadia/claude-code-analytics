# OpenRouter Integration - Testing Checklist

This document tracks testing status for the OpenRouter integration feature.

## Setup

- [x] `.env` file with `OPENROUTER_API_KEY`
- [x] API key validation (correct format check)
- [x] Expired key detection and error messaging

## Streamlit UI Testing

### Analysis Page - Model Selection
- [x] Model selector dropdown appears (OpenRouter only)
- [x] 13 curated models displayed correctly
- [x] Default selection (DeepSeek V3.2) works
- [ ] Try different budget tier models
- [ ] Try different balanced tier models
- [ ] Try different premium tier models
- [x] Run analysis with default model succeeds

### Analysis Page - Browse All Models
- [ ] "Browse All Models" expander opens
- [ ] "Load All Models" button works
- [ ] 300+ models fetched from API
- [ ] Table displays correctly with pricing/context
- [ ] Models sorted by newest first

### Analysis Page - Different Analysis Types
- [x] Decisions analysis works
- [ ] Errors analysis works
- [ ] Agent Usage analysis works
- [ ] Custom analysis with prompt works

### Analysis Results Display
- [x] Analysis completes successfully
- [x] Result text displays correctly
- [ ] Token usage shows correctly
- [ ] Model name displayed in results
- [ ] Can download/copy results

## CLI Testing

### Basic Usage
- [ ] `python3 scripts/analyze_session.py <session-id> --type=decisions` works
- [ ] Default model (DeepSeek V3.2) is used
- [ ] Provider name shown in output
- [ ] Token usage displayed

### Model Selection
- [ ] `--model=anthropic/claude-sonnet-4.5` works
- [ ] `--model=openai/gpt-5.2-chat` works
- [ ] `--model=qwen/qwen3-vl-8b-instruct` works (cheapest)
- [ ] Invalid model shows helpful error

### Analysis Types
- [ ] `--type=decisions` works
- [ ] `--type=errors` works
- [ ] `--type=agent_usage` works
- [ ] `--type=custom --prompt="..."` works

### Output Options
- [ ] `--output=analysis.md` saves to file
- [ ] Stdout output works (no --output flag)

## Provider Fallback Testing

### Google Gemini Fallback
- [ ] Unset OPENROUTER_API_KEY
- [ ] Set GOOGLE_API_KEY
- [ ] Streamlit UI: No model selector shown
- [ ] Streamlit UI: Analysis works with Gemini
- [ ] CLI: Works with Gemini provider
- [ ] CLI: Shows "Gemini" as provider name

### Error Handling
- [ ] No API key configured shows helpful error
- [ ] Invalid OpenRouter key format detected
- [ ] 401 error shows helpful message
- [ ] Network errors handled gracefully
- [ ] Timeout errors handled (for very long prompts)

## Edge Cases

### Large Conversations
- [ ] Very long transcript (>100K tokens) works
- [ ] Timeout handling works correctly
- [ ] Memory usage is reasonable

### Model-Specific Features
- [ ] Models with 1M context (Gemini 3 Flash, Claude Sonnet 4.5) work
- [ ] Multimodal models work (or gracefully fail if not applicable)
- [ ] Different temperature settings work

### API Rate Limits
- [ ] Rate limit errors handled gracefully
- [ ] Retry logic (if implemented)

## Documentation Testing

- [x] README updated with OpenRouter info
- [ ] Example commands in README work
- [ ] API key setup instructions clear
- [ ] Model pricing information accurate

## Performance Testing

- [ ] Model fetching (<3 seconds)
- [ ] Analysis completion time reasonable
- [ ] Streamlit UI responsive during analysis
- [ ] No memory leaks with repeated analyses

## Known Issues

_Document any issues found during testing here_

---

## Testing Notes

### Completed
- ✅ Streamlit UI with default model (DeepSeek V3.2)
- ✅ API key validation and expired key detection
- ✅ Decisions analysis type works

### In Progress
- ⏳ CLI testing
- ⏳ Testing different models across price tiers
- ⏳ Testing all analysis types

### Blocked
- None currently

---

**Last Updated:** 2025-12-18
**Tester:** @skapadia
