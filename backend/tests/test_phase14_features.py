"""
Unit tests for Phase 14 features:
- Sentence splitting without breaking decimal numbers (e.g. 6.8, 48.2%)
- Open-domain query routing (bypassing literal fast-path reading templates)
- Session context extraction (location and season)
- Sentence chunks in ChatResponse
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.orchestrator import split_into_sentences, orchestrator

client = TestClient(app)


def test_split_into_sentences_preserves_decimals():
    text = "पीएच मान 6.8 है। मिट्टी की नमी 48.2% और EC 1.15 dS/m दर्ज की गई है। क्या आप अगली फसल बोना चाहते हैं?"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert "6.8" in sentences[0]
    assert "48.2%" in sentences[1]
    assert "1.15" in sentences[1]
    assert "फसल" in sentences[2]


def test_split_into_sentences_english():
    text = "Soil pH is 6.8 which is neutral. Soil moisture is 48.2% and temp is 22.4C. Would you like fertilizer advice?"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert "6.8" in sentences[0]
    assert "48.2%" in sentences[1]
    assert "fertilizer advice?" in sentences[2]


def test_conceptual_ph_query_bypasses_fast_path():
    # "Soil pH 6.8 ka kya matlab hai?" must NOT route to route_ph_temperature literal template
    response = client.post("/api/chat", json={
        "message": "Soil pH 6.8 ka kya matlab hai?",
        "language": "hi-IN",
        "session_id": "test-ph-conceptual",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] != "soil_ph_temp_query"
    assert "sentences" in data
    assert len(data["sentences"]) >= 1


def test_conceptual_npk_difference_bypasses_fast_path():
    # "Nitrogen aur phosphorus mein kya difference hai?" must NOT route to route_npk_query
    response = client.post("/api/chat", json={
        "message": "Nitrogen aur phosphorus mein kya difference hai?",
        "language": "hi-IN",
        "session_id": "test-npk-diff",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] != "npk_nutrient_query"
    assert "sentences" in data
    assert len(data["sentences"]) >= 1


def test_literal_moisture_still_routes_fast_path():
    # Literal sensor check without conceptual words should route to fast path in sub-millisecond
    response = client.post("/api/chat", json={
        "message": "मेरे खेत में अभी मिट्टी की नमी कितनी है?",
        "language": "hi-IN",
        "session_id": "test-literal-moisture",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["intent"] == "soil_moisture_query"
    assert data["provider_status"] == "fast_path"
    assert "sentences" in data
    assert len(data["sentences"]) >= 1


def test_session_location_and_season_retention():
    # Query mentions Punjab and Rabi
    response = client.post("/api/chat", json={
        "message": "Main Punjab se hoon aur Rabi season mein kya ugaun?",
        "language": "hi-IN",
        "session_id": "sess-punjab-rabi",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert orchestrator._session_locations.get("sess-punjab-rabi") == "Punjab"
    assert orchestrator._session_seasons.get("sess-punjab-rabi") == "Rabi"
