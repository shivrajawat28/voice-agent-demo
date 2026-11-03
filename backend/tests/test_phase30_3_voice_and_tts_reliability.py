"""
Phase 30.3 - Voice Consistency, TTS Rate Limiting, and Farmer Response Quality Tests
"""
import asyncio
import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.providers.gnani_tts import GnaniTTSProvider, GnaniAPIError, parse_retry_after
from app.services.orchestrator import orchestrator
from app.services.voice_service import voice_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Retry-After Parsing & Unit Tests
# ---------------------------------------------------------------------------
def test_parse_retry_after_numeric():
    assert parse_retry_after("2") == 2.0
    assert parse_retry_after("0.2") == 0.5  # Clamped to min 0.5s
    assert parse_retry_after("10.0") == 5.0  # Clamped to max 5.0s
    assert parse_retry_after(None) is None
    assert parse_retry_after("invalid") is None


# ---------------------------------------------------------------------------
# 2. TTS Rate Limiting (HTTP 429) & Concurrency Ceiling
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_gnani_tts_rate_limit_with_retry_after_success():
    """
    Simulates a 429 response on attempt 0 with Retry-After header,
    followed by a successful 200 response on attempt 1.
    """
    mock_client = AsyncMock()

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.5"}

    valid_wav = b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 50
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.headers = {"Content-Type": "audio/wav"}
    resp_200.content = valid_wav

    mock_client.post = AsyncMock(side_effect=[resp_429, resp_200])

    provider = GnaniTTSProvider(
        api_key="gnani-test-key-12345",
        http_client=mock_client,
        concurrency_limit=2,
        max_retries=2,
    )

    audio_bytes, mime = await provider.synthesize("नमस्कार किसान भाई", "hi-IN", "Nalini")
    assert mime == "audio/wav"
    assert len(audio_bytes) > 40

    metrics = provider.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["successful_requests"] == 1
    assert metrics["rate_limit_429_count"] == 1
    assert metrics["retry_count"] == 1
    assert metrics["exhausted_retries_count"] == 0


@pytest.mark.anyio
async def test_gnani_tts_rate_limit_exhausted():
    """
    Simulates persistent 429 responses exceeding max_retries.
    Must raise GnaniAPIError and update exhausted_retries_count.
    """
    mock_client = AsyncMock()
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {}
    mock_client.post = AsyncMock(return_value=resp_429)

    provider = GnaniTTSProvider(
        api_key="gnani-test-key-12345",
        http_client=mock_client,
        concurrency_limit=2,
        max_retries=1,
    )

    with pytest.raises(GnaniAPIError) as exc_info:
        await provider.synthesize("खेत की स्थिति", "hi-IN", "Nalini")
    assert "rate limit exceeded" in str(exc_info.value).lower()

    metrics = provider.get_metrics()
    assert metrics["rate_limit_429_count"] >= 1
    assert metrics["exhausted_retries_count"] == 1


@pytest.mark.anyio
async def test_gnani_tts_concurrency_ceiling():
    """
    Ensures that active concurrency never exceeds the configured concurrency limit.
    """
    max_active = 0
    lock = asyncio.Lock()

    async def slow_post(*args, **kwargs):
        nonlocal max_active
        async with lock:
            provider._metrics.active_concurrency
            if provider._metrics.active_concurrency > max_active:
                max_active = provider._metrics.active_concurrency
        await asyncio.sleep(0.05)
        valid_wav = b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 50
        r = MagicMock()
        r.status_code = 200
        r.headers = {"Content-Type": "audio/wav"}
        r.content = valid_wav
        return r

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=slow_post)

    provider = GnaniTTSProvider(
        api_key="gnani-test-key-12345",
        http_client=mock_client,
        concurrency_limit=2,
        max_retries=1,
    )

    tasks = [
        provider.synthesize(f"वाक्य क्रमांक {i}", "hi-IN", "Nalini")
        for i in range(6)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 6
    metrics = provider.get_metrics()
    assert metrics["peak_concurrency"] <= 2
    assert max_active <= 2


@pytest.mark.anyio
async def test_gnani_tts_transient_502_recovery():
    """
    Simulates transient 502 Bad Gateway from Gnani API, followed by success.
    """
    mock_client = AsyncMock()
    resp_502 = MagicMock()
    resp_502.status_code = 502

    valid_wav = b"RIFF" + b"\x00" * 36 + b"WAVE" + b"\x00" * 50
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.headers = {"Content-Type": "audio/wav"}
    resp_200.content = valid_wav

    mock_client.post = AsyncMock(side_effect=[resp_502, resp_200])

    provider = GnaniTTSProvider(
        api_key="gnani-test-key-12345",
        http_client=mock_client,
        concurrency_limit=2,
        max_retries=2,
    )

    audio_bytes, mime = await provider.synthesize("मौसम कैसा रहेगा", "hi-IN", "Nalini")
    assert mime == "audio/wav"
    metrics = provider.get_metrics()
    assert metrics["server_error_5xx_count"] == 1
    assert metrics["retry_count"] == 1
    assert metrics["successful_requests"] == 1


# ---------------------------------------------------------------------------
# 3. Two-Level Response Policy: Farmer-Friendly vs Detailed
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_farm_status_concise_default_level1():
    """
    Farmer Query: "इन readings के मुताबिक यह बताओ कि क्या मेरे खेत की स्थिति सही है या गलत है?"
    Must return Level 1 concise summary:
    - Overall status: Good / Attention needed.
    - Mentions Cotton (low moisture) and Tomato (high moisture).
    - Mentions Wheat/Mustard normal.
    - NO raw telemetry dump (no NPK mg/kg values, battery %, tank %, timestamps).
    - Preserves Hindi Nalini voice metadata.
    """
    query = "इन readings के मुताबिक यह बताओ कि क्या मेरे खेत की स्थिति सही है या गलत है?"
    resp = await orchestrator.process_query(
        message=query,
        language="hi-IN",
        session_id="test-p30-3-concise-1",
    )
    reply = resp.reply
    assert resp.intent == "farm_status"
    assert "ठीक है" in reply or "ध्यान देने की जरूरत" in reply
    assert "कपास" in reply
    assert "टमाटर" in reply
    assert "गेहूं" in reply or "सरसों" in reply

    # Ensure NO technical telemetry dump
    assert "mg/kg" not in reply
    assert "डिवाइस बैटरी" not in reply
    assert "मुख्य पानी का टैंक" not in reply

    # Metadata check
    assert resp.metadata.get("turn_language") == "hi-IN"
    assert resp.metadata.get("turn_voice") == "Nalini"


@pytest.mark.anyio
async def test_farm_status_explicit_readings_level2():
    """
    Farmer Query: "सभी zones की readings दिखाओ"
    Must return Level 2 detailed breakdown with actual numbers and zones.
    """
    query = "सभी zones की readings दिखाओ"
    resp = await orchestrator.process_query(
        message=query,
        language="hi-IN",
        session_id="test-p30-3-detailed-1",
    )
    reply = resp.reply
    assert resp.intent == "farm_status"
    # Level 2 includes numbered breakdown and tank percentage
    assert "वास्तविक समग्र अवलोकन" in reply
    assert "पानी का टैंक" in reply


# ---------------------------------------------------------------------------
# 4. Fertilizer Consumption: Sensor Scope vs Volumetric
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_fertilizer_consumption_no_unrelated_npk_dump_english():
    """
    Query: "How much fertilizer was consumed in the last 24 hours?"
    Must explain 7-in-1 probe scope vs volumetric meters, without dumping unrelated current NPK numbers.
    """
    query = "How much fertilizer was consumed in the last 24 hours?"
    resp = await orchestrator.process_query(
        message=query,
        language="en-US",
        session_id="test-p30-3-fert-en",
    )
    reply = resp.reply
    assert resp.intent == "fertilizer_consumption_query"
    assert "cannot measure actual volumetric fertilizer consumption" in reply
    assert "in-situ soil nutrient concentrations" in reply
    assert "flow meters" in reply or "dosing controllers" in reply

    # Must NOT dump raw NPK values in reply text
    assert "Nitrogen: 1" not in reply
    assert "Phosphorus: 4" not in reply
    assert resp.metadata.get("turn_language") == "en-US"
    assert resp.metadata.get("turn_voice") == "Kaveri"


@pytest.mark.anyio
async def test_fertilizer_consumption_no_unrelated_npk_dump_hindi():
    """
    Query: "पिछले 24 घंटों में कितना उर्वरक खर्च हुआ?"
    Must explain in Hindi clearly without dumping unrelated NPK numbers.
    """
    query = "पिछले 24 घंटों में कितना उर्वरक खर्च हुआ?"
    resp = await orchestrator.process_query(
        message=query,
        language="hi-IN",
        session_id="test-p30-3-fert-hi",
    )
    reply = resp.reply
    assert resp.intent == "fertilizer_consumption_query"
    assert "7-in-1 सॉइल प्रोब" in reply
    assert "खाद की वास्तविक खपत नहीं माप सकता" in reply
    assert "फ्लो मीटर" in reply or "डोजिंग कंट्रोलर" in reply
    assert resp.metadata.get("turn_language") == "hi-IN"
    assert resp.metadata.get("turn_voice") == "Nalini"


# ---------------------------------------------------------------------------
# 5. Sugarcane pH: Unregistered Zone and Reference-Only Standard
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sugarcane_ph_agronomy_english():
    """
    Query: "Is the pH level currently optimal for sugarcane?"
    Must state sugarcane is not registered, cite ICAR-IISR 6.0-7.5 (optimal 6.5) as reference,
    and prompt for zone. Must NOT fall back to wheat zone.
    """
    query = "Is the pH level currently optimal for sugarcane?"
    resp = await orchestrator.process_query(
        message=query,
        language="en-US",
        session_id="test-p30-3-sugarcane-en",
    )
    reply = resp.reply
    assert resp.intent == "soil_ph_temp_query"
    assert "Sugarcane is not registered in any of your farm's active zones" in reply
    assert "ICAR-IISR standards" in reply
    assert "6.0 to 7.5" in reply
    assert "6.5" in reply
    assert resp.metadata.get("registered_on_farm") is False
    assert resp.metadata.get("turn_language") == "en-US"
    assert resp.metadata.get("turn_voice") == "Kaveri"


@pytest.mark.anyio
async def test_sugarcane_ph_agronomy_hindi():
    """
    Query: "गन्ने के लिए मिट्टी का पीएच कितना होना चाहिए?"
    Must state unregistered, provide ICAR-IISR 6.0-7.5, prompt for zone, keep Hindi Nalini voice.
    """
    query = "गन्ने के लिए मिट्टी का पीएच कितना होना चाहिए?"
    resp = await orchestrator.process_query(
        message=query,
        language="hi-IN",
        session_id="test-p30-3-sugarcane-hi",
    )
    reply = resp.reply
    assert resp.intent == "soil_ph_temp_query"
    assert "गन्ना आपके खेत के किसी भी सक्रिय ज़ोन में पंजीकृत नहीं है" in reply
    assert "ICAR-IISR मानकों के अनुसार" in reply
    assert "6.0 से 7.5" in reply
    assert resp.metadata.get("registered_on_farm") is False
    assert resp.metadata.get("turn_language") == "hi-IN"
    assert resp.metadata.get("turn_voice") == "Nalini"


# ---------------------------------------------------------------------------
# 6. TTS Metrics API Endpoint
# ---------------------------------------------------------------------------
def test_tts_metrics_api_endpoint():
    response = client.get("/api/tts/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "concurrency_limit" in data
    assert "rate_limit_429_count" in data
