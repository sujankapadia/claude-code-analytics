"""LLM provider abstraction layer for multiple backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import os

import google.generativeai as genai
import requests


@dataclass
class LLMResponse:
    """Standardized response from LLM providers."""

    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model_name: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            model: Model identifier (provider-specific)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini direct API provider."""

    def __init__(self, api_key: str, default_model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            default_model: Default model to use
        """
        self.api_key = api_key
        self.default_model = default_model
        genai.configure(api_key=api_key)

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        """Generate text using Gemini API."""
        model_name = model or self.default_model
        gemini_model = genai.GenerativeModel(model_name)

        # Generate with low temperature for deterministic output
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=kwargs.get('temperature', 0.1)
            )
        )

        # Extract token usage
        usage_metadata = getattr(response, "usage_metadata", None)
        input_tokens = None
        output_tokens = None
        if usage_metadata:
            input_tokens = getattr(usage_metadata, "prompt_token_count", None)
            output_tokens = getattr(usage_metadata, "candidates_token_count", None)

        return LLMResponse(
            text=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
        )


class OpenRouterProvider(LLMProvider):
    """OpenRouter unified API provider."""

    # Curated quick select models (13 newest premium models from 2025)
    QUICK_SELECT_MODELS = [
        # Budget tier
        ("Qwen3 VL 8B - $0.06 (Cheapest)", "qwen/qwen3-vl-8b-instruct"),
        ("Llama 4 Scout - $0.08 (327K context)", "meta-llama/llama-4-scout"),
        ("Mistral Small Creative - $0.10", "mistralai/mistral-small-creative"),
        ("Llama 3.3 70B - $0.10 (Proven)", "meta-llama/llama-3.3-70b-instruct"),

        # Balanced tier (recommended)
        ("DeepSeek V3.2 - $0.26 ⭐ DEFAULT", "deepseek/deepseek-v3.2"),
        ("Gemini 3 Flash - $0.50 (1M context)", "google/gemini-3-flash-preview"),
        ("Claude Haiku 4.5 - $1.00 (Fast)", "anthropic/claude-haiku-4.5"),
        ("GPT-5.1 - $1.25 (400K context)", "openai/gpt-5.1"),
        ("GPT-5.2 Chat - $1.75 (Newest)", "openai/gpt-5.2-chat"),

        # Premium tier
        ("Gemini 3 Pro - $2.00 (1M context)", "google/gemini-3-pro-preview"),
        ("Claude Sonnet 4.5 - $3.00 (Best)", "anthropic/claude-sonnet-4.5"),
        ("Grok 4 - $3.00 (xAI)", "x-ai/grok-4"),
        ("Claude Opus 4.5 - $5.00 (Premium)", "anthropic/claude-opus-4.5"),
    ]

    def __init__(self, api_key: str, default_model: str = "deepseek/deepseek-v3.2"):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key
            default_model: Default model to use
        """
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = "https://openrouter.ai/api/v1"

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        """Generate text using OpenRouter API."""
        model_name = model or self.default_model

        # Verify API key is set
        if not self.api_key:
            raise ValueError("OpenRouter API key is not set")

        # OpenRouter uses OpenAI-compatible chat completions API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/claude-code-utils",
            "X-Title": "Claude Code Analytics",
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get('temperature', 0.1),
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,  # 5 minute timeout for long analysis
        )

        # Better error handling
        if response.status_code != 200:
            error_detail = response.text
            raise ValueError(
                f"OpenRouter API error (status {response.status_code}): {error_detail}"
            )

        data = response.json()

        # Extract response
        text = data["choices"][0]["message"]["content"]

        # Extract token usage
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
        )

    @staticmethod
    def fetch_all_models() -> list[dict]:
        """
        Fetch all available models from OpenRouter.

        Returns:
            List of model dictionaries with metadata
        """
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
        response.raise_for_status()
        return response.json()["data"]


def create_provider(
    openrouter_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    default_model: Optional[str] = None,
) -> LLMProvider:
    """
    Factory function to create appropriate LLM provider.

    Precedence:
    1. OpenRouter if OPENROUTER_API_KEY is set
    2. Gemini if GOOGLE_API_KEY is set
    3. Raise error if neither is set

    Args:
        openrouter_api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        gemini_api_key: Google AI API key (defaults to GOOGLE_API_KEY env var)
        default_model: Default model to use (provider-specific)

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If no API key is configured
    """
    openrouter_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
    gemini_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")

    if openrouter_key:
        # Validate key format
        if not openrouter_key.startswith("sk-or-"):
            raise ValueError(
                f"Invalid OpenRouter API key format. Keys should start with 'sk-or-'. "
                f"Got: {openrouter_key[:10]}..."
            )
        return OpenRouterProvider(
            api_key=openrouter_key,
            default_model=default_model or "deepseek/deepseek-v3.2"
        )
    elif gemini_key:
        return GeminiProvider(
            api_key=gemini_key,
            default_model=default_model or "gemini-2.0-flash-exp"
        )
    else:
        raise ValueError(
            "No LLM API key configured. Set either OPENROUTER_API_KEY or GOOGLE_API_KEY environment variable."
        )
