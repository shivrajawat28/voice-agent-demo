from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "fertobot-voice-agent-backend"
    assert "version" in data


def test_config_endpoint_returns_active_settings():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "tts_provider" in data
    assert "stt_provider" in data
    assert "conversation_provider" in data
    assert "gnani_configured" in data
    assert "available_voices" in data
    assert "hi-IN" in data["available_voices"]
    assert "Shivani" in data["available_voices"]["hi-IN"]
