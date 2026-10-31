from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_greeting_intent():
    response = client.post("/api/chat", json={"message": "Hello!"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "greeting"
    assert "FertoBot Voice Assistant" in data["reply"]


def test_intro_intent():
    response = client.post("/api/chat", json={"message": "Who are you?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "intro"
    assert "FertoBot Voice Agent" in data["reply"]


def test_help_intent():
    response = client.post("/api/chat", json={"message": "What can you do?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "help"
    assert "You can say" in data["reply"]


def test_repeat_intent_with_history():
    # Initial statement
    client.post("/api/chat", json={"message": "Hello!", "session_id": "test-session"})

    # Repeat statement
    response = client.post("/api/chat", json={"message": "Repeat that", "session_id": "test-session"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "repeat"
    assert "Repeating:" in data["reply"]


def test_goodbye_intent():
    response = client.post("/api/chat", json={"message": "Goodbye!"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "goodbye"
    assert "bountiful" in data["reply"]


def test_unknown_fallback():
    response = client.post("/api/chat", json={"message": "Fly to the edge of the galaxy"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "unknown"
    assert "didn't quite catch that" in data["reply"]


def test_farm_status_preview():
    response = client.post("/api/chat", json={"message": "Farm status"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "farm_status"
    assert "Soil Moisture" in data["reply"]


def test_empty_message_validation_error():
    # Pydantic validation rejects empty string (min_length=1)
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422
