import asyncio
import pytest
import httpx
from app.providers.mock_tts import MockTTSProvider, generate_synthetic_wav
from app.providers.gnani_tts import (
    GnaniTTSProvider,
    GnaniAuthenticationError,
    GnaniAPIError,
)


def test_mock_tts_provider_generates_valid_wav_tone():
    provider = MockTTSProvider()
    assert provider.provider_name == "mock"

    async def _run():
        return await provider.synthesize("नमस्ते किसान भाई", language="hi-IN")

    audio_bytes, mime_type = asyncio.run(_run())
    assert mime_type == "audio/wav"
    assert len(audio_bytes) > 44  # Valid WAV header is at least 44 bytes
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"


def test_synthetic_wav_generator_envelope():
    wav_bytes = generate_synthetic_wav(duration_seconds=0.5, frequency_hz=440.0)
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
    assert len(wav_bytes) == 16044  # 16000 samples/sec * 0.5s * 2 bytes/sample + 44 bytes header


def test_gnani_payload_and_header_construction():
    provider = GnaniTTSProvider(
        api_key="test-gnani-secret-key-12345",
        endpoint="https://api.vachana.ai/api/v1/tts/inference",
        model="timbre-v3.0",
        default_hindi_voice="Shivani",
        default_english_voice="Pratibha",
    )

    # Headers
    headers = provider.build_headers()
    assert headers["X-API-Key-ID"] == "test-gnani-secret-key-12345"
    assert headers["Content-Type"] == "application/json"

    # Hindi payload
    payload_hi = provider.build_payload("नमस्ते", language="hi-IN")
    assert payload_hi["text"] == "नमस्ते"
    assert payload_hi["model"] == "timbre-v3.0"
    assert payload_hi["language"] == "hi-IN"
    assert payload_hi["voice"] == "Shivani"
    assert payload_hi["speed"] == 1.0
    assert payload_hi["audio_config"]["container"] == "wav"

    # English payload
    payload_en = provider.build_payload("Hello", language="en-IN")
    assert payload_en["voice"] == "Pratibha"

    # Custom voice
    payload_custom = provider.build_payload("Test", language="hi-IN", voice_id="CustomVoice")
    assert payload_custom["voice"] == "CustomVoice"


def test_gnani_blocked_error_when_key_unconfigured():
    provider = GnaniTTSProvider(api_key="")
    assert not provider.is_live_ready()

    async def _run():
        await provider.synthesize("नमस्ते", language="hi-IN")

    with pytest.raises(GnaniAuthenticationError) as exc_info:
        asyncio.run(_run())
    assert "Live integration is BLOCKED" in str(exc_info.value)


def test_gnani_live_call_success_mocked_http():
    def mock_handler(request: httpx.Request):
        assert request.headers.get("X-API-Key-ID") == "valid-key-999"
        wav_fixture = generate_synthetic_wav(0.2)
        return httpx.Response(200, content=wav_fixture, headers={"content-type": "audio/wav"})

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(
                api_key="valid-key-999",
                http_client=client,
            )
            return await provider.synthesize("नमस्ते किसान", language="hi-IN")

    audio_bytes, mime_type = asyncio.run(_run())
    assert mime_type == "audio/wav"
    assert audio_bytes[:4] == b"RIFF"


def test_gnani_handles_json_error_under_200_ok():
    def mock_handler(request: httpx.Request):
        return httpx.Response(200, json={"message": "Internal quota exceeded"}, headers={"content-type": "application/json"})

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(
                api_key="valid-key-999",
                http_client=client,
            )
            await provider.synthesize("नमस्ते", language="hi-IN")

    with pytest.raises(GnaniAPIError) as exc:
        asyncio.run(_run())
    assert "returned JSON error" in str(exc.value)


def test_gnani_handles_truncated_audio_response():
    def mock_handler(request: httpx.Request):
        return httpx.Response(200, content=b"RIFFshort", headers={"content-type": "audio/wav"})

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(
                api_key="valid-key-999",
                http_client=client,
            )
            await provider.synthesize("नमस्ते", language="hi-IN")

    with pytest.raises(GnaniAPIError) as exc:
        asyncio.run(_run())
    assert "truncated" in str(exc.value)


def test_gnani_handles_401_auth_error_mocked_http():
    def mock_handler(request: httpx.Request):
        return httpx.Response(401, text="Unauthorized: Invalid API Key")

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(
                api_key="invalid-key",
                http_client=client,
            )
            await provider.synthesize("नमस्ते", language="hi-IN")

    with pytest.raises(GnaniAuthenticationError) as exc:
        asyncio.run(_run())
    assert "401" in str(exc.value)


def test_gnani_handles_429_rate_limit_mocked_http():
    def mock_handler(request: httpx.Request):
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(
                api_key="valid-key",
                http_client=client,
            )
            await provider.synthesize("नमस्ते", language="hi-IN")

    with pytest.raises(GnaniAPIError) as exc:
        asyncio.run(_run())
    assert "429" in str(exc.value)


def test_gnani_handles_network_timeout():
    def mock_handler(request: httpx.Request):
        raise httpx.ReadTimeout("Connection timed out")

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(
                api_key="valid-key",
                http_client=client,
            )
            await provider.synthesize("नमस्ते", language="hi-IN")

    with pytest.raises(GnaniAPIError) as exc:
        asyncio.run(_run())
    assert "timed out" in str(exc.value).lower()
