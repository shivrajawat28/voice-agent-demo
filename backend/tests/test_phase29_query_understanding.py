"""
Phase 29 Regression Test Suite: Query Understanding, Intent Routing & Agronomic Safety
Validates that natural Hindi, Hinglish, and English queries are understood accurately
without hitting generic "I don't understand" fallbacks.
"""
import pytest
from app.services.orchestrator import orchestrator


@pytest.mark.anyio
async def test_phase29_ten_core_queries():
    """
    Tests the exact 10 core agricultural queries from Phase B:
    1. मुझे मेरे खेत की जानकारी दो।
    2. मेरे खेत की स्थिति कैसी है?
    3. मेरी गेहूं की फसल कैसी चल रही है?
    4. खेत में पानी की कमी है क्या?
    5. North zone में moisture कितना है?
    6. यूरिया और DAP की सही मात्रा क्या होनी चाहिए?
    7. मेरी मिट्टी का pH कितना है?
    8. क्या मुझे अभी सिंचाई करनी चाहिए?
    9. पिछले सात दिनों में मिट्टी की नमी कैसे बदली?
    10. मेरे खेत में कोई समस्या है क्या?
    """
    test_cases = [
        ("मुझे मेरे खेत की जानकारी दो।", "farm_status"),
        ("मेरे खेत की स्थिति कैसी है?", "farm_status"),
        ("मेरी गेहूं की फसल कैसी चल रही है?", "agricultural_inquiry"),
        ("खेत में पानी की कमी है क्या?", "agricultural_inquiry"),
        ("North zone में moisture कितना है?", "soil_moisture_query"),
        ("यूरिया और DAP की सही मात्रा क्या होनी चाहिए?", "agricultural_inquiry"),
        ("मेरी मिट्टी का pH कितना है?", "soil_ph_temp_query"),
        ("क्या मुझे अभी सिंचाई करनी चाहिए?", "agricultural_inquiry"),
        ("पिछले सात दिनों में मिट्टी की नमी कैसे बदली?", "historical_trend_query"),
        ("मेरे खेत में कोई समस्या है क्या?", "alert_history_query"),
    ]

    for query, expected_intent in test_cases:
        resp = await orchestrator.process_query(
            message=query,
            language="hi-IN",
            session_id=f"test-p29-{expected_intent}",
        )
        assert resp.intent != "unknown", f"Query '{query}' was falsely classified as unknown!"
        assert "समझ नहीं आया" not in resp.reply, f"Query '{query}' returned fallback error message!"
        assert resp.intent == expected_intent, f"Query '{query}' expected intent '{expected_intent}', got '{resp.intent}'"
        assert len(resp.reply) > 10, f"Query '{query}' returned an empty or stub reply!"


@pytest.mark.anyio
async def test_phase29_zone_resolution_all_four_zones():
    """
    Validates zone resolution across all four farm zones:
    Zone 1: North / Wheat
    Zone 2: South / Cotton
    Zone 3: East / Tomato
    Zone 4: West / Mustard & Gram
    """
    zone_queries = [
        ("North zone में नमी कितनी है?", "DEMO-ZONE-001"),
        ("South zone का हाल बताओ", "DEMO-ZONE-002"),
        ("East zone में टमाटर कैसा है?", "DEMO-ZONE-003"),
        ("West zone में सरसों की क्या स्थिति है?", "DEMO-ZONE-004"),
    ]

    for q, expected_zone in zone_queries:
        resp = await orchestrator.process_query(message=q, language="hi-IN")
        resolved = resp.metadata.get("zone_id")
        assert resolved == expected_zone, f"Query '{q}' expected zone '{expected_zone}', got '{resolved}'"


@pytest.mark.anyio
async def test_phase29_english_and_hinglish_farm_status():
    """
    Validates English and Hinglish paraphrasing for farm status.
    """
    queries = [
        "Give me my farm status",
        "Field overview",
        "Khet ki jankari do",
        "Khet ka haal batao",
        "Field telemetry report",
    ]
    for q in queries:
        resp = await orchestrator.process_query(message=q, language="en-US")
        assert resp.intent == "farm_status", f"Query '{q}' failed to route to farm_status, got {resp.intent}"
        assert "didn't quite catch" not in resp.reply


@pytest.mark.anyio
async def test_phase29_sodium_policy():
    """
    Validates that sodium queries explicitly clarify that 7-in-1 sensor does not measure sodium,
    and that sodium is not derived from EC.
    """
    resp = await orchestrator.process_query("खेत की मिट्टी में सोडियम कितना है?", language="hi-IN")
    assert resp.intent == "sodium_disqualification"
    assert "सोडियम (Na) नहीं मापता" in resp.reply
    assert resp.metadata.get("sodium_measured") is False
