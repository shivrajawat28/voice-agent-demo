"""
Tests for Live LLM Providers (Gemini, OpenAI), Error States, Secret Redaction, and Fallback Transparency
"""
import pytest
from app.providers.live_llm import GeminiLLMProvider, OpenAILLMProvider
from app.providers.llm_base import LLMAuthenticationError, LLMInferenceError
from app.services.orchestrator import LLMOrchestrator
from app.config import redact_sensitive, is_llm_configured


@pytest.mark.anyio
async def test_gemini_missing_credentials_raises_auth_error():
    provider = GeminiLLMProvider(api_key="")
    assert provider.is_live_ready() is False
    assert provider.provider_status == "unavailable"

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_text("Test query")
    assert "Gemini API key is missing" in str(exc_info.value)


@pytest.mark.anyio
async def test_openai_missing_credentials_raises_auth_error():
    provider = OpenAILLMProvider(api_key="")
    assert provider.is_live_ready() is False
    assert provider.provider_status == "unavailable"

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_text("Test query")
    assert "OpenAI API key is missing" in str(exc_info.value)


@pytest.mark.anyio
async def test_gemini_invalid_key_produces_honest_auth_error():
    # Makes a real HTTP request to the live Gemini REST endpoint with a dummy invalid key
    provider = GeminiLLMProvider(api_key="AIza_DUMMY_INVALID_TEST_KEY_FOR_TESTS", timeout_seconds=10.0)
    assert provider.is_live_ready() is True

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_text("Hello Gemini")
    err_msg = str(exc_info.value)
    assert "authentication failed" in err_msg.lower() or "400" in err_msg or "invalid" in err_msg.lower()
    # Ensure key is never leaked
    assert "AIza_DUMMY_INVALID_TEST_KEY_FOR_TESTS" not in err_msg


@pytest.mark.anyio
async def test_openai_invalid_key_produces_honest_auth_error():
    # Makes a real HTTP request to the live OpenAI endpoint with an invalid key
    provider = OpenAILLMProvider(api_key="sk-proj-invalidtestkey1234567890abcdef", timeout_seconds=10.0)
    assert provider.is_live_ready() is True

    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_text("Hello OpenAI")
    err_msg = str(exc_info.value)
    assert "authentication failed" in err_msg.lower() or "401" in err_msg or "invalid" in err_msg.lower()
    # Ensure key is never leaked
    assert "sk-proj-invalidtestkey1234567890abcdef" not in err_msg


@pytest.mark.anyio
async def test_orchestrator_reports_gemini_fallback_when_live_fails():
    provider = GeminiLLMProvider(api_key="AIza_DUMMY_INVALID_TEST_KEY_FOR_TESTS", timeout_seconds=4.0)
    orch = LLMOrchestrator(provider)

    res = await orch.process_query("Why are my cotton leaves turning yellow?", language="en-US")
    # Must NOT silently claim to be mock!
    assert res.provider_status == "gemini_fallback"
    # Warning must explain the live failure honestly
    assert any("Live 'gemini' inference failed" in w for w in res.warnings)
    # Execution trace must record plan failure
    plan_step = next(s for s in res.execution_trace if s.action == "plan_execution")
    assert plan_step.status == "failed"
    assert "Gemini" in plan_step.details


@pytest.mark.anyio
async def test_orchestrator_reports_gemini_unavailable_when_unconfigured():
    provider = GeminiLLMProvider(api_key="", timeout_seconds=2.0)
    orch = LLMOrchestrator(provider)

    res = await orch.process_query("Should I irrigate the wheat field today?", language="en-US")
    assert res.provider_status == "gemini_unavailable"
    assert any("unconfigured" in w.lower() for w in res.warnings)


def test_secret_redaction_sanitizes_tokens_and_keys():
    raw = (
        "Error calling endpoint with X-API-Key-ID: secret_key_12345 "
        "and x-goog-api-key: test_dummy_goog_key_12345 and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    )
    sanitized = redact_sensitive(raw)
    assert "secret_key_12345" not in sanitized
    assert "test_dummy_goog_key_12345" not in sanitized
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
    assert "[REDACTED_KEY]" in sanitized or "[REDACTED_TOKEN]" in sanitized
