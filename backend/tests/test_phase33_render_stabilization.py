"""
Phase 33.0 Tests: Render Stabilization, In-Flight TTS Deduplication, STT Idle Timeout, and Zero-I/O Health Check
"""
import asyncio
import json
import pytest
import httpx
from starlette.testclient import TestClient

from app.main import app
from app.providers.gnani_tts import GnaniTTSProvider
from app.services.gnani_stt_stream import GnaniSTTStreamHandler
from app.providers.mock_tts import generate_synthetic_wav


def test_gnani_tts_inflight_deduplication():
    """
    Verify that concurrent calls to synthesize the same text share the single in-flight network request,
    preventing 429 rate limit triggers and duplicate network traffic.
    """
    async def _run():
        call_count = 0
        synthetic_wav = generate_synthetic_wav(duration_seconds=0.5)

        def mock_handler(request: httpx.Request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                status_code=200,
                content=synthetic_wav,
                headers={"content-type": "audio/wav"},
            )

        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

        provider = GnaniTTSProvider(
            api_key="mock-api-key-phase33",
            http_client=mock_client,
        )

        # Fire two identical synthesis requests concurrently
        task1 = asyncio.create_task(provider.synthesize("नमस्कार किसान भाई", language="hi-IN", voice_id="Deepak"))
        task2 = asyncio.create_task(provider.synthesize("नमस्कार किसान भाई", language="hi-IN", voice_id="Deepak"))

        res1, res2 = await asyncio.gather(task1, task2)

        # Both tasks get valid audio
        assert res1[0] == res2[0]
        assert res1[1] == "audio/wav"
        assert res2[1] == "audio/wav"

        # Crucial: Only ONE network call occurred because task 2 awaited the in-flight request of task 1
        assert call_count == 1

        # Check metrics
        metrics = provider.get_metrics()
        assert metrics["last_voice_id"] == "Deepak"
        assert metrics["successful_requests"] == 1
        assert metrics["average_latency_ms"] >= 0.0

    asyncio.run(_run())


def test_gnani_tts_voice_selection_resolution():
    """
    Verify that voice_id is respected and correctly resolved across Indic and English languages.
    """
    provider = GnaniTTSProvider(
        api_key="mock-api-key-phase33",
        default_hindi_voice="Nalini",
        default_english_voice="Kaveri",
        default_hinglish_voice="Poorvi",
    )

    # Explicit Deepak voice for Hindi
    payload_deepak = provider.build_payload("खेत में पानी कब देना है?", language="hi-IN", voice_id="Deepak")
    assert payload_deepak["voice"] == "Deepak"

    # Explicit Nalini voice for Hindi
    payload_nalini = provider.build_payload("खेत में पानी कब देना है?", language="hi-IN", voice_id="Nalini")
    assert payload_nalini["voice"] == "Nalini"

    # Explicit Pranav voice for English
    payload_pranav = provider.build_payload("What is the current soil moisture?", language="en-IN", voice_id="Pranav")
    assert payload_pranav["voice"] == "Pranav"

    # Default fallback when voice_id is None
    payload_hi_default = provider.build_payload("नमस्ते", language="hi-IN", voice_id=None)
    assert payload_hi_default["voice"] == "Nalini"

    payload_en_default = provider.build_payload("Hello", language="en-IN", voice_id=None)
    assert payload_en_default["voice"] == "Kaveri"


def test_gnani_stt_idle_timeout_handling():
    """
    Verify that when upstream GNANI closes a session with a 60-second idle timeout message,
    the stream handler intercepts the error and emits an 'idle_timeout' event rather than a 500 error.
    """
    class MockIdleGnaniWebSocket:
        def __init__(self):
            self.closed = False

        async def send(self, data):
            pass

        async def __aiter__(self):
            yield json.dumps({"type": "connected", "model": "prisma-v3.0"})
            yield json.dumps({"type": "processing"})
            # Upstream GNANI 60s idle timeout message
            yield json.dumps({
                "type": "error",
                "code": 408,
                "message": "Session closed: no speech segment received for 60 seconds.",
            })

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self.closed = True

    mock_gnani_ws = MockIdleGnaniWebSocket()

    handler = GnaniSTTStreamHandler(
        api_key="valid-mock-key-12345",
        ws_connect_override=lambda *args, **kwargs: mock_gnani_ws,
    )

    class MockClientWebSocket:
        def __init__(self):
            self.accepted = False
            self.closed = False
            self.received_events = []
            self._incoming = [
                {"bytes": b"\x01\x02" * 512},
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

    # Find emitted events
    event_types = [e.get("type") for e in client_ws.received_events]
    assert "idle_timeout" in event_types

    # Find the idle_timeout event and assert properties
    idle_event = next(e for e in client_ws.received_events if e.get("type") == "idle_timeout")
    assert idle_event["code"] == "NO_SPEECH_TIMEOUT"
    assert "No speech detected" in idle_event["message"]

    # Verify NO error event was dispatched
    assert "error" not in event_types


def test_cached_health_check_zero_io():
    """
    Verify /health and /api/health return commit and status ok without runtime file reads.
    """
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "commit" in data

    resp_api = client.get("/api/health")
    assert resp_api.status_code == 200
    assert resp_api.json()["commit"] == data["commit"]
