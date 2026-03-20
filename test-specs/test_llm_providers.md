# Test Spec: test_llm_providers

## Purpose
Tests for LLM providers — GeminiProvider, OpenAICompatibleProvider (aliased as OpenRouterProvider), create_provider factory.

## Test fixes

### test_openrouter_provider_generate_api_error
Error message changed from "OpenRouter API error" to generic "API error (status N)". Update assertion to match.

### test_openrouter_provider_generate_no_api_key
Provider no longer validates key upfront. Mock a 401 response and verify the error contains "401".

### test_openrouter_fetch_all_models
fetch_all_models now passes `headers={}` kwarg. Update assert_called_once_with to include it.

### test_create_provider_invalid_openrouter_key_format
Renamed to test_create_provider_any_openrouter_key_format. create_provider no longer validates key format — it accepts any non-empty string and creates a provider. Verify it returns an OpenRouterProvider with the given key.
