"""
Unit Tests for LLM Providers (Mock, Gemini, OpenAI) and Factory
"""
import pytest
from pydantic import BaseModel
from app.providers.llm_base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMInferenceError,
)
from app.providers.mock_llm import MockLLMProvider
from app.providers.live_llm import GeminiLLMProvider, OpenAILLMProvider
from app.providers.llm_factory import get_llm_provider


class DummySchema(BaseModel):
    title: str
    confidence: float


@pytest.mark.anyio
async def test_mock_llm_text_generation():
    provider = MockLLMProvider()
    assert provider.provider_name == "mock"
    assert provider.provider_status == "mock"
    assert provider.is_live_ready() is False

    text_en = await provider.generate_text("Synthesize yellow leaf findings")
    assert "yellow" in text_en.lower() or "nitrogen" in text_en.lower()

    text_hi = await provider.generate_text("पत्तियां पीली होने का विश्लेषण")
    assert "पीला" in text_hi or "नाइट्रोजन" in text_hi


@pytest.mark.anyio
async def test_mock_llm_structured_generation():
    provider = MockLLMProvider()
    res = await provider.generate_structured("test prompt", DummySchema)
    assert isinstance(res, DummySchema)
    assert res.title is not None


@pytest.mark.anyio
async def test_gemini_unconfigured_raises_auth_error():
    provider = GeminiLLMProvider(api_key="")
    assert provider.provider_status == "unavailable"
    assert provider.is_live_ready() is False

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_text("Hello")
    assert "Gemini API key is missing" in str(exc_info.value)


@pytest.mark.anyio
async def test_openai_unconfigured_raises_auth_error():
    provider = OpenAILLMProvider(api_key="")
    assert provider.provider_status == "unavailable"
    assert provider.is_live_ready() is False

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_text("Hello")
    assert "OpenAI API key is missing" in str(exc_info.value)


def test_llm_factory_fallback():
    # If no key, requesting gemini safely returns MockLLMProvider
    provider = get_llm_provider("gemini")
    assert isinstance(provider, (GeminiLLMProvider, MockLLMProvider))
    if not provider.is_live_ready():
        assert provider.provider_status in ["mock", "unavailable"]
