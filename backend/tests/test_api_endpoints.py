import base64
from fastapi.testclient import TestClient
from app.main import app
from app.services.voice_service import voice_service

client = TestClient(app)


def test_tts_binary_endpoint_mock_tone_success():
    # Activate mock provider
    client.post("/api/provider/tts?provider=mock")

    payload = {
        "text": "नमस्ते किसान",
        "language": "hi-IN",
        "speed": 1.0,
    }
    response = client.post("/api/tts", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers.get("x-tts-provider") == "mock"
    assert response.headers.get("x-audio-type") == "test-tone"
    assert response.content[:4] == b"RIFF"


def test_tts_blocked_when_gnani_unconfigured(monkeypatch):
    # Switch to gnani provider without API key
    client.post("/api/provider/tts?provider=gnani")
    gnani_prov = voice_service.get_tts_provider()
    orig_key = getattr(gnani_prov, "api_key", None)
    try:
        gnani_prov.api_key = ""
        payload = {
            "text": "नमस्ते किसान",
            "language": "hi-IN",
        }
        response = client.post("/api/tts", json=payload)
        assert response.status_code == 503
        assert response.headers.get("x-tts-blocked") == "true"
        assert "Live integration is BLOCKED" in response.json()["detail"]
    finally:
        gnani_prov.api_key = orig_key


def test_tts_rejected_when_browser_provider_active():
    # Switch to browser provider
    client.post("/api/provider/tts?provider=browser")

    payload = {
        "text": "Hello",
        "language": "en-US",
    }
    response = client.post("/api/tts", json=payload)
    assert response.status_code == 400
    assert "Client Web Speech API should be used" in response.json()["detail"]


def test_tts_json_endpoint_success():
    client.post("/api/provider/tts?provider=mock")
    payload = {
        "text": "Hello Farmer",
        "language": "en-US",
    }
    response = client.post("/api/tts?as_json=true", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "audio_base64" in data
    assert data["audio_format"] == "wav"
    decoded = base64.b64decode(data["audio_base64"])
    assert decoded[:4] == b"RIFF"


def test_tts_empty_text_returns_422():
    response = client.post("/api/tts", json={"text": ""})
    assert response.status_code == 422


def test_provider_switching_endpoints():
    # Switch TTS provider to mock
    res_tts = client.post("/api/provider/tts?provider=mock")
    assert res_tts.status_code == 200
    assert res_tts.json()["active_tts_provider"] == "mock"

    # Switch STT provider to mock
    res_stt = client.post("/api/provider/stt?provider=mock")
    assert res_stt.status_code == 200
    assert res_stt.json()["active_stt_provider"] == "mock"

    # Test STT endpoint while mock is active
    audio_sample = base64.b64encode(b"RIFFmockaudio").decode("utf-8")
    stt_res = client.post("/api/stt", json={"audio_base64": audio_sample, "language": "hi-IN"})
    assert stt_res.status_code == 200
    stt_data = stt_res.json()
    assert stt_data["success"] is True
    assert stt_data["provider"] == "mock"
    assert "नमस्ते" in stt_data["text"]

    # Switch back to browser STT and verify endpoint rejects direct audio
    client.post("/api/provider/stt?provider=browser")
    stt_browser_res = client.post("/api/stt", json={"audio_base64": audio_sample, "language": "hi-IN"})
    assert stt_browser_res.status_code == 400


def test_chat_session_id_repeat_intent_isolated():
    # Session A: Greeting
    client.post("/api/chat", json={"message": "hello", "session_id": "session-A"})
    # Session B: Help
    client.post("/api/chat", json={"message": "help", "session_id": "session-B"})

    # Session A repeat should repeat greeting
    res_a = client.post("/api/chat", json={"message": "repeat", "session_id": "session-A"})
    assert "Repeating: \"Hello!" in res_a.json()["reply"]

    # Session B repeat should repeat help
    res_b = client.post("/api/chat", json={"message": "repeat", "session_id": "session-B"})
    assert "Repeating: \"You can say:" in res_b.json()["reply"]
