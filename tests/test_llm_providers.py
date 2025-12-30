"""Comprehensive tests for LLM providers."""

import os
from unittest.mock import MagicMock, patch

import pytest

from claude_code_analytics.streamlit_app.services.llm_providers import (
    GeminiProvider,
    LLMProvider,
    LLMResponse,
    OpenRouterProvider,
    create_provider,
)


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_llm_response_creation(self):
        """Test creating an LLMResponse instance."""
        response = LLMResponse(
            text="Hello world", input_tokens=10, output_tokens=20, model_name="test-model"
        )
        assert response.text == "Hello world"
        assert response.input_tokens == 10
        assert response.output_tokens == 20
        assert response.model_name == "test-model"

    def test_llm_response_with_defaults(self):
        """Test LLMResponse with optional fields as None."""
        response = LLMResponse(text="Hello")
        assert response.text == "Hello"
        assert response.input_tokens is None
        assert response.output_tokens is None
        assert response.model_name is None


class TestLLMProvider:
    """Test LLMProvider abstract base class."""

    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()  # Should raise TypeError for abstract class


class TestGeminiProvider:
    """Test GeminiProvider."""

    def test_gemini_provider_init(self):
        """Test GeminiProvider initialization."""
        with patch("google.generativeai.configure") as mock_configure:
            provider = GeminiProvider(api_key="test-key", default_model="gemini-pro")
            assert provider.api_key == "test-key"
            assert provider.default_model == "gemini-pro"
            mock_configure.assert_called_once_with(api_key="test-key")

    def test_gemini_provider_init_with_default_model(self):
        """Test GeminiProvider initialization with default model."""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider(api_key="test-key")
            assert provider.default_model == "gemini-2.0-flash-exp"

    @patch("google.generativeai.GenerativeModel")
    def test_gemini_provider_generate(self, mock_model_class):
        """Test GeminiProvider.generate() method."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "Generated text"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        with patch("google.generativeai.configure"):
            provider = GeminiProvider(api_key="test-key")
            result = provider.generate("Test prompt")

        assert isinstance(result, LLMResponse)
        assert result.text == "Generated text"
        assert result.input_tokens == 10
        assert result.output_tokens == 20
        assert result.model_name == "gemini-2.0-flash-exp"

    @patch("google.generativeai.GenerativeModel")
    def test_gemini_provider_generate_with_custom_model(self, mock_model_class):
        """Test GeminiProvider.generate() with custom model."""
        mock_response = MagicMock()
        mock_response.text = "Generated text"
        mock_response.usage_metadata = None

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        with patch("google.generativeai.configure"):
            provider = GeminiProvider(api_key="test-key")
            result = provider.generate("Test prompt", model="gemini-pro")

        assert result.model_name == "gemini-pro"
        assert result.input_tokens is None
        assert result.output_tokens is None

    @patch("google.generativeai.GenerativeModel")
    def test_gemini_provider_generate_with_temperature(self, mock_model_class):
        """Test GeminiProvider.generate() with custom temperature."""
        mock_response = MagicMock()
        mock_response.text = "Generated text"
        mock_response.usage_metadata = None

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        with patch("google.generativeai.configure"):
            provider = GeminiProvider(api_key="test-key")
            provider.generate("Test prompt", temperature=0.5)

        # Verify temperature was passed
        call_kwargs = mock_model.generate_content.call_args[1]
        assert "generation_config" in call_kwargs


class TestOpenRouterProvider:
    """Test OpenRouterProvider."""

    def test_openrouter_provider_init(self):
        """Test OpenRouterProvider initialization."""
        provider = OpenRouterProvider(api_key="sk-or-test", default_model="gpt-4")
        assert provider.api_key == "sk-or-test"
        assert provider.default_model == "gpt-4"
        assert provider.base_url == "https://openrouter.ai/api/v1"

    def test_openrouter_provider_init_with_default_model(self):
        """Test OpenRouterProvider initialization with default model."""
        provider = OpenRouterProvider(api_key="sk-or-test")
        assert provider.default_model == "deepseek/deepseek-v3.2"

    def test_openrouter_quick_select_models(self):
        """Test that QUICK_SELECT_MODELS is defined and has expected structure."""
        assert len(OpenRouterProvider.QUICK_SELECT_MODELS) > 0
        for display_name, model_id in OpenRouterProvider.QUICK_SELECT_MODELS:
            assert isinstance(display_name, str)
            assert isinstance(model_id, str)
            assert len(display_name) > 0
            assert len(model_id) > 0

    @patch("requests.post")
    def test_openrouter_provider_generate(self, mock_post):
        """Test OpenRouterProvider.generate() method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated text"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
        mock_post.return_value = mock_response

        provider = OpenRouterProvider(api_key="sk-or-test")
        result = provider.generate("Test prompt")

        assert isinstance(result, LLMResponse)
        assert result.text == "Generated text"
        assert result.input_tokens == 10
        assert result.output_tokens == 20
        assert result.model_name == "deepseek/deepseek-v3.2"

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://openrouter.ai/api/v1/chat/completions" in call_args[0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk-or-test"

    @patch("requests.post")
    def test_openrouter_provider_generate_with_custom_model(self, mock_post):
        """Test OpenRouterProvider.generate() with custom model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated text"}}],
            "usage": {},
        }
        mock_post.return_value = mock_response

        provider = OpenRouterProvider(api_key="sk-or-test")
        result = provider.generate("Test prompt", model="custom-model")

        assert result.model_name == "custom-model"
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "custom-model"

    @patch("requests.post")
    def test_openrouter_provider_generate_api_error(self, mock_post):
        """Test OpenRouterProvider.generate() handles API errors."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        provider = OpenRouterProvider(api_key="sk-or-test")
        with pytest.raises(ValueError) as exc_info:
            provider.generate("Test prompt")

        assert "OpenRouter API error" in str(exc_info.value)
        assert "401" in str(exc_info.value)

    def test_openrouter_provider_generate_no_api_key(self):
        """Test OpenRouterProvider.generate() raises error when API key is missing."""
        provider = OpenRouterProvider(api_key="")
        with pytest.raises(ValueError) as exc_info:
            provider.generate("Test prompt")

        assert "API key is not set" in str(exc_info.value)

    @patch("requests.post")
    def test_openrouter_provider_generate_with_temperature(self, mock_post):
        """Test OpenRouterProvider.generate() with custom temperature."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated text"}}],
            "usage": {},
        }
        mock_post.return_value = mock_response

        provider = OpenRouterProvider(api_key="sk-or-test")
        provider.generate("Test prompt", temperature=0.7)

        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 0.7

    @patch("requests.get")
    def test_openrouter_fetch_all_models(self, mock_get):
        """Test OpenRouterProvider.fetch_all_models() static method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "model1", "name": "Model 1"},
                {"id": "model2", "name": "Model 2"},
            ]
        }
        mock_get.return_value = mock_response

        models = OpenRouterProvider.fetch_all_models()

        assert len(models) == 2
        assert models[0]["id"] == "model1"
        assert models[1]["id"] == "model2"
        mock_get.assert_called_once_with("https://openrouter.ai/api/v1/models", timeout=30)

    @patch("requests.get")
    def test_openrouter_fetch_all_models_error(self, mock_get):
        """Test OpenRouterProvider.fetch_all_models() handles errors."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception) as exc_info:
            OpenRouterProvider.fetch_all_models()

        assert "Network error" in str(exc_info.value)


class TestCreateProvider:
    """Test create_provider factory function."""

    def test_create_provider_with_openrouter_key(self):
        """Test create_provider returns OpenRouterProvider when OpenRouter key is set."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test-key"}, clear=False):
            provider = create_provider()
            assert isinstance(provider, OpenRouterProvider)
            assert provider.api_key == "sk-or-test-key"

    def test_create_provider_with_gemini_key(self):
        """Test create_provider returns GeminiProvider when only Gemini key is set."""
        with (
            patch.dict(os.environ, {"GOOGLE_API_KEY": "gemini-test-key"}, clear=True),
            patch("google.generativeai.configure"),
        ):
            provider = create_provider()
            assert isinstance(provider, GeminiProvider)
            assert provider.api_key == "gemini-test-key"

    def test_create_provider_precedence(self):
        """Test that OpenRouter takes precedence over Gemini when both are set."""
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "sk-or-test", "GOOGLE_API_KEY": "gemini-test"},
            clear=False,
        ):
            provider = create_provider()
            assert isinstance(provider, OpenRouterProvider)

    def test_create_provider_no_keys(self):
        """Test create_provider raises error when no API keys are configured."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                create_provider()

            assert "No LLM API key configured" in str(exc_info.value)

    def test_create_provider_with_explicit_openrouter_key(self):
        """Test create_provider with explicitly provided OpenRouter key."""
        provider = create_provider(openrouter_api_key="sk-or-explicit")
        assert isinstance(provider, OpenRouterProvider)
        assert provider.api_key == "sk-or-explicit"

    def test_create_provider_with_explicit_gemini_key(self):
        """Test create_provider with explicitly provided Gemini key."""
        with patch("google.generativeai.configure"):
            provider = create_provider(gemini_api_key="gemini-explicit")
            assert isinstance(provider, GeminiProvider)
            assert provider.api_key == "gemini-explicit"

    def test_create_provider_with_default_model(self):
        """Test create_provider with custom default model."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
            provider = create_provider(default_model="custom-model")
            assert provider.default_model == "custom-model"

    def test_create_provider_invalid_openrouter_key_format(self):
        """Test create_provider raises error for invalid OpenRouter key format."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                create_provider(openrouter_api_key="invalid-key")

            assert "Invalid OpenRouter API key format" in str(exc_info.value)
            assert "sk-or-" in str(exc_info.value)

    def test_create_provider_valid_openrouter_key_format(self):
        """Test create_provider accepts valid OpenRouter key format."""
        provider = create_provider(openrouter_api_key="sk-or-v1-valid-key")
        assert isinstance(provider, OpenRouterProvider)
        assert provider.api_key == "sk-or-v1-valid-key"


class TestIntegration:
    """Integration tests for provider interactions."""

    @patch("requests.post")
    def test_full_openrouter_workflow(self, mock_post):
        """Test complete workflow with OpenRouterProvider."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Analysis result"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        mock_post.return_value = mock_response

        # Create provider and generate
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
            provider = create_provider()
            result = provider.generate("Analyze this conversation")

        assert result.text == "Analysis result"
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    @patch("google.generativeai.GenerativeModel")
    def test_full_gemini_workflow(self, mock_model_class):
        """Test complete workflow with GeminiProvider."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "Gemini analysis"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 80
        mock_response.usage_metadata.candidates_token_count = 40

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Create provider and generate
        with (
            patch.dict(os.environ, {"GOOGLE_API_KEY": "gemini-test"}, clear=True),
            patch("google.generativeai.configure"),
        ):
            provider = create_provider()
            result = provider.generate("Analyze this conversation")

        assert result.text == "Gemini analysis"
        assert result.input_tokens == 80
        assert result.output_tokens == 40
