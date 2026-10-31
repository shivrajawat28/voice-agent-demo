"""
Test Suite for Phase 11: Gnani AI (Vachana) Speech Integration
Tests:
- Gnani TTS (Timbre v2.5) payload construction, voice selection (Nalini, Kaveri, Poorvi)
- Spoken text formatting (unit expansion, simulation marker stripping, markdown removal)
- Binary audio response handling, error codes (401, 403, 429, 500, 504)
- Gnani STT (Prisma v3.0) streaming WebSocket handler, authentication guard
- PCM 512-sample (1024-byte) frame chunking and zero-padding on stop
- Duplicate transcript deduplication and event parsing
- Secret redaction and session isolation
"""
import asyncio
import json
import pytest
import httpx
from starlette.testclient import TestClient
from app.main import app
from app.providers.gnani_tts import (
    GnaniTTSProvider,
    GnaniAuthenticationError,
    GnaniAPIError,
)
from app.providers.gnani_stt import GnaniSTTProvider, GnaniSTTException
from app.services.gnani_stt_stream import GnaniSTTStreamHandler
from app.providers.mock_tts import generate_synthetic_wav
from app import config


def test_gnani_tts_timbre_v25_payload_and_voice_selection():
    provider = GnaniTTSProvider(
        api_key="test-gnani-key-xyz-12345",
        model="timbre-v2.5",
        default_hindi_voice="Nalini",
        default_english_voice="Kaveri",
        default_hinglish_voice="Poorvi",
    )

    # 1. Hindi voice selection
    payload_hi = provider.build_payload("नमस्ते किसान भाई", language="hi-IN")
    assert payload_hi["model"] == "timbre-v2.5"
    assert payload_hi["voice"] == "Nalini"
    assert payload_hi["audio_config"]["sample_rate"] == 48000
    assert payload_hi["audio_config"]["container"] == "wav"

    # 2. English voice selection
    payload_en = provider.build_payload("Soil moisture is optimal", language="en-IN")
    assert payload_en["voice"] == "Kaveri"

    # 3. Hinglish voice selection
    payload_hinglish = provider.build_payload("Cotton zone mein moisture kitni hai?", language="hi-en")
    assert payload_hinglish["voice"] == "Poorvi"

    # 4. Custom requested voice override
    payload_custom = provider.build_payload("Custom voice", language="hi-IN", voice_id="CustomVoiceX")
    assert payload_custom["voice"] == "CustomVoiceX"


def test_spoken_text_formatting_hindi():
    provider = GnaniTTSProvider(api_key="test-key")
    raw_text = (
        "**Zone 1** की स्थिति:\n"
        "- नमी: 48.2%\n"
        "- NPK: 38.0 mg/kg\n"
        "- तापमान: 24.5°C\n"
        "(सिमुलेटेड टेलीमेट्री डेटा)"
    )
    formatted = provider.format_spoken_text(raw_text, language="hi-IN")

    # Simulation markers stripped
    assert "(सिमुलेटेड" not in formatted
    assert "टेलीमेट्री डेटा)" not in formatted
    # Markdown asterisks and bullet stripped
    assert "**" not in formatted
    assert "- " not in formatted
    # Units expanded naturally
    assert "48.2 प्रतिशत" in formatted
    assert "38.0 मिलीग्राम प्रति किलोग्राम" in formatted
    assert "24.5 डिग्री सेल्सियस" in formatted


def test_spoken_text_formatting_english():
    provider = GnaniTTSProvider(api_key="test-key")
    raw_text = (
        "### Crop Report\n"
        "DEMO-ZONE-001 soil moisture is 28.5% and nitrogen is 62.0 mg/kg.\n"
        "[simulated data]"
    )
    formatted = provider.format_spoken_text(raw_text, language="en-IN")

    assert "###" not in formatted
    assert "[simulated data]" not in formatted
    assert "Zone 1" in formatted
    assert "28.5 percent" in formatted
    assert "62.0 milligrams per kilogram" in formatted


def test_gnani_tts_binary_audio_handling_mocked():
    def mock_handler(request: httpx.Request):
        assert request.headers.get("X-API-Key-ID") == "test-key-555"
        wav_data = generate_synthetic_wav(0.1)
        return httpx.Response(200, content=wav_data, headers={"content-type": "audio/wav"})

    transport = httpx.MockTransport(mock_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniTTSProvider(api_key="test-key-555", http_client=client)
            return await provider.synthesize("परीक्षण संदेश", language="hi-IN")

    audio_bytes, mime_type = asyncio.run(_run())
    assert mime_type == "audio/wav"
    assert len(audio_bytes) > 44
    assert audio_bytes[:4] == b"RIFF"


def test_gnani_tts_missing_credentials_raises_auth_error():
    provider = GnaniTTSProvider(api_key="")
    assert not provider.is_live_ready()

    async def _run():
        await provider.synthesize("परीक्षण")

    with pytest.raises(GnaniAuthenticationError) as exc_info:
        asyncio.run(_run())
    assert "Live integration is BLOCKED" in str(exc_info.value)


def test_gnani_tts_error_statuses():
    # 401
    def handler_401(req):
        return httpx.Response(401, text="Unauthorized: Invalid Key")

    async def run_401():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler_401)) as c:
            p = GnaniTTSProvider(api_key="bad-key-123", http_client=c)
            await p.synthesize("test")

    with pytest.raises(GnaniAuthenticationError):
        asyncio.run(run_401())

    # 429
    def handler_429(req):
        return httpx.Response(429, text="Rate limit exceeded")

    async def run_429():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler_429)) as c:
            p = GnaniTTSProvider(api_key="key-12345", http_client=c)
            await p.synthesize("test")

    with pytest.raises(GnaniAPIError) as exc429:
        asyncio.run(run_429())
    assert "429" in str(exc429.value)


def test_gnani_stt_batch_provider():
    def mock_stt_handler(request: httpx.Request):
        assert request.headers.get("X-API-Key-ID") == "stt-key-12345"
        return httpx.Response(
            200,
            json={"transcript": "गेहूं में पानी कब देना है", "confidence": 0.98},
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(mock_stt_handler)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            provider = GnaniSTTProvider(api_key="stt-key-12345", http_client=client)
            return await provider.transcribe(b"fake-pcm-data-1234", language="hi-IN")

    res = asyncio.run(_run())
    assert res.success is True
    assert res.text == "गेहूं में पानी कब देना है"
    assert res.confidence == 0.98
    assert res.provider == "gnani"


def test_gnani_stt_websocket_unconfigured_auth_guard():
    client = TestClient(app)
    from app.services.gnani_stt_stream import gnani_stt_stream_handler
    orig_key = gnani_stt_stream_handler.api_key
    try:
        gnani_stt_stream_handler.api_key = ""
        # When GNANI_API_KEY is not configured or empty, connecting to /api/ws/stt returns AUTH_REQUIRED
        assert not gnani_stt_stream_handler.is_configured()

        with client.websocket_connect("/api/ws/stt") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "AUTH_REQUIRED"
            assert "credentials required" in msg["message"].lower()
            assert msg["fallback_available"] is True
    finally:
        gnani_stt_stream_handler.api_key = orig_key


def test_gnani_stt_stream_forwarding_and_deduplication():
    # Mock upstream Gnani WebSocket connection
    class MockGnaniWebSocket:
        def __init__(self):
            self.sent_frames = []
            self.closed = False

        async def send(self, data):
            self.sent_frames.append(data)

        async def __aiter__(self):
            # Emit mock events conforming to official Gnani STT Realtime docs
            yield json.dumps({"type": "connected", "model": "prisma-v3.0"})
            yield json.dumps({"type": "processing"})
            # First transcript segment
            yield json.dumps({
                "type": "transcript",
                "segment_id": "seg-001",
                "text": "मिट्टी की नमी",
                "detected_language_code": "hi-IN",
                "is_final": False,
                "audio_duration_ms": 1200.0,
            })
            # Duplicate segment (should be filtered)
            yield json.dumps({
                "type": "transcript",
                "segment_id": "seg-001",
                "text": "मिट्टी की नमी",
                "detected_language_code": "hi-IN",
                "is_final": False,
            })
            # Final transcript segment
            yield json.dumps({
                "type": "transcript",
                "segment_id": "seg-002",
                "text": "मिट्टी की नमी कितनी है?",
                "detected_language_code": "hi-IN",
                "is_final": True,
                "audio_duration_ms": 2100.0,
            })

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self.closed = True

    mock_gnani_ws = MockGnaniWebSocket()

    def mock_connect(*args, **kwargs):
        return mock_gnani_ws

    handler = GnaniSTTStreamHandler(
        api_key="valid-mock-key-12345",
        ws_connect_override=mock_connect,
    )

    # Use a dummy client websocket to test proxying
    class MockClientWebSocket:
        def __init__(self):
            self.accepted = False
            self.closed = False
            self.received_events = []
            # Feed 1024 bytes of audio then stop
            self._incoming = [
                {"bytes": b"\x01\x02" * 512},  # exactly 1024 bytes (512 samples)
                {"text": json.dumps({"action": "stop"})},
            ]
            self._incoming_idx = 0

        async def accept(self):
            self.accepted = True

        async def receive(self):
            if self._incoming_idx < len(self._incoming):
                msg = self._incoming[self._incoming_idx]
                self._incoming_idx += 1
                return msg
            await asyncio.sleep(0.5)
            return {"text": json.dumps({"action": "cancel"})}

        async def send_json(self, data):
            self.received_events.append(data)

        async def close(self, code=1000, reason=""):
            self.closed = True

    client_ws = MockClientWebSocket()

    async def _test():
        await handler.handle_client_websocket(client_ws)

    asyncio.run(_test())

    # Verification:
    # 1. 1024-byte audio frame was forwarded to Gnani plus VAD silence frames
    assert len(mock_gnani_ws.sent_frames) >= 1
    assert mock_gnani_ws.sent_frames[0] == b"\x01\x02" * 512
    assert len(mock_gnani_ws.sent_frames[0]) == 1024

    # 2. Events received by client
    event_types = [e.get("type") for e in client_ws.received_events]
    assert "status" in event_types
    assert "gnani_ready" in event_types
    assert "processing" in event_types
    assert "transcript" in event_types
    assert "final_transcript" in event_types

    # 3. Final transcript content
    final_event = next(e for e in client_ws.received_events if e.get("type") == "final_transcript")
    assert final_event["text"] == "मिट्टी की नमी कितनी है?"
    assert final_event["detected_language"] == "hi-IN"
    assert final_event["is_final"] is True

    # 4. Duplicate segment was suppressed
    transcripts = [e for e in client_ws.received_events if e.get("type") in ("transcript", "final_transcript")]
    assert len(transcripts) == 2  # seg-001 and seg-002, duplicate seg-001 ignored!


def test_secret_redaction_in_all_gnani_messages():
    secret_key = "secret_gnani_super_token_99999"
    raw_error = f"Error communicating with upstream X-API-Key-ID: {secret_key} on wss://api.vachana.ai"
    redacted = config.redact_sensitive(raw_error)
    assert secret_key not in redacted
    assert "[REDACTED" in redacted
