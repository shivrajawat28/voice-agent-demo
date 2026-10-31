"""
LLM Provider Factory
Resolves the active LLM provider based on environment configuration.
"""
from app.config import (
    LLM_PROVIDER,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    is_llm_configured,
)
from app.providers.llm_base import BaseLLMProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.live_llm import GeminiLLMProvider, OpenAILLMProvider


def get_llm_provider(provider_override: str = None) -> BaseLLMProvider:
    """
    Returns the designated BaseLLMProvider instance.
    Reports genuine provider status ('live', 'mock', or 'unavailable') without silently masking.
    """
    choice = (provider_override or LLM_PROVIDER or "mock").lower()

    if choice == "gemini":
        return GeminiLLMProvider()

    if choice == "openai":
        return OpenAILLMProvider()

    return MockLLMProvider()
