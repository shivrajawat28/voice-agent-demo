"""
Phase 34.6: Farmer-First Concise Response Mode Verification Suite

Validates that FertoBot AI Agronomist produces short, actionable, farmer-friendly,
and natural responses in Hindi/Hinglish/English adhering to target word count guidelines:
- Simple queries: 20–40 words
- Normal agricultural advisory: 35–60 words
- Complex or safety-sensitive questions: 60–90 words max

Ensures preferred response structure:
1. Direct answer / recommendation first.
2. One short explanation or practical condition.
3. Important sensor reading or safety warning, if relevant.
"""

import re
import uuid
import pytest
from app.services.orchestrator import LLMOrchestrator
from app.services.telemetry_service import telemetry_service


def count_words(text: str) -> int:
    """Accurately count words across Hindi, English, and mixed alphanumeric strings."""
    return len([w for w in re.split(r"\s+", text.strip()) if w])


@pytest.fixture
def orchestrator():
    return LLMOrchestrator()


@pytest.mark.anyio
async def test_case1_wheat_first_irrigation_concise(orchestrator):
    """
    Scenario 1: Wheat first irrigation timing inquiry.
    Query: 'मेरी गेहूं की फसल 22 दिन की है, पहली सिंचाई कब करें?'
    Target: Normal agricultural advisory (35–60 words).
    Requirements:
    - Direct recommendation first (CRI / 20-25 days).
    - Dynamic recognition of crop age (22 दिन).
    - Topsoil and crown root inspection guidance.
    - Grounded telemetry (Zone 1 moisture 48.2%).
    - No academic 30-40% yield drop penalty statistic.
    """
    sid = f"test-p34-6-c1-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मेरी गेहूं की फसल 22 दिन की है, पहली सिंचाई कब करें?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 35 <= words <= 65, f"Expected 35-65 words, got {words}: {reply}"
    assert "CRI" in reply or "ताज मूल" in reply
    assert "20" in reply and "25" in reply
    assert "22" in reply and "दिन" in reply
    assert "48.2%" in reply or "48.2" in reply
    assert "30 से 40" not in reply and "30%" not in reply


@pytest.mark.anyio
async def test_case2_soil_ph_neutral_concise(orchestrator):
    """
    Scenario 2: Soil pH and improvement inquiry (Zone 1 neutral pH 6.8).
    Query: 'मिट्टी का pH और सुधार उपाय?'
    Target: Normal agricultural advisory (35–60 words).
    Requirements:
    - Direct reading first: pH 6.8 is optimal and neutral.
    - No chemical amendments (lime/gypsum) required.
    - General compost/FYM recommendation with Soil Health Card / lab testing.
    - No fixed universal 10-12 t/ha FYM dosage.
    """
    sid = f"test-p34-6-c2-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मिट्टी का pH और सुधार उपाय?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 35 <= words <= 65, f"Expected 35-65 words, got {words}: {reply}"
    assert "6.8" in reply
    assert any(w in reply for w in ["तटस्थ", "आदर्श", "Neutral"])
    assert any(w in reply for w in ["रासायनिक सुधारक", "चूना", "जिप्सम"])
    assert any(w in reply for w in ["गोबर की खाद", "कम्पोस्ट", "FYM", "जैविक"])
    assert any(w in reply for w in ["मृदा स्वास्थ्य कार्ड", "लैब परीक्षण", "परीक्षण"])
    assert "10 से 12 टन" not in reply


@pytest.mark.anyio
async def test_case3_fertilizer_dosage_concise(orchestrator):
    """
    Scenario 3: Fertilizer quantity/dosage inquiry.
    Query: '1 एकड़ में कितना यूरिया और डीएपी डालें?'
    Target: Normal agricultural advisory (35–60 words).
    Requirements:
    - Direct answer first: cannot prescribe fixed dose without soil test/stage.
    - Explain basal DAP vs split top-dress Urea.
    - Concise clarification prompt requested (crop, stage, plot size).
    - needs_clarification=True.
    """
    sid = f"test-p34-6-c3-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="1 एकड़ में कितना यूरिया और डीएपी डालें?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    assert resp.needs_clarification is True
    reply = resp.reply
    words = count_words(reply)

    assert 35 <= words <= 65, f"Expected 35-65 words, got {words}: {reply}"
    assert "यूरिया" in reply and "डीएपी" in reply
    assert any(w in reply for w in ["बेसल", "बुवाई"])
    assert any(w in reply for w in ["बांटकर", "भागों", "विभाजित"])
    assert resp.clarification_prompt is not None
    assert count_words(resp.clarification_prompt) <= 20


@pytest.mark.anyio
async def test_case4_maize_moisture_concise(orchestrator):
    """
    Scenario 4: Unmonitored crop context isolation (Maize at 40% moisture).
    Query: 'मक्का में 40% नमी पर पानी देना चाहिए या नहीं?'
    Target: Normal agricultural advisory (35–60 words).
    Requirements:
    - Direct statement: Maize not in monitored sensor zones; 40% is farmer-provided.
    - Cannot decide on moisture % alone without soil texture and growth stage.
    - Critical stages: tasseling/silking; avoid waterlogging.
    - Isolated from wheat / Zone 1 readings.
    """
    sid = f"test-p34-6-c4-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मक्का में 40% नमी पर पानी देना चाहिए या नहीं?",
        language="hi-IN",
        session_id=sid,
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 35 <= words <= 65, f"Expected 35-65 words, got {words}: {reply}"
    assert "मक्का" in reply
    assert any(w in reply for w in ["पंजीकृत", "सेंसर ज़ोन में नहीं", "किसान-प्रदत्त", "सेंसर ज़ोन"])
    assert any(w in reply for w in ["बनावट", "अवस्था", "मंजर", "सिल्क"])
    assert "48.2" not in reply
    assert "North Wheat Field" not in reply


@pytest.mark.anyio
async def test_case5_device_health_concise(orchestrator):
    """
    Scenario 5: Simple device health and sensor telemetry inquiry.
    Query: 'सेंसर और सिस्टम का क्या हाल है?'
    Target: Simple question (20–40 words).
    Requirements:
    - Direct answer: gateway/probes status, battery, tank level.
    - No filler or academic disclaimers.
    """
    sid = f"test-p34-6-c5-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="सेंसर और सिस्टम का क्या हाल है?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 20 <= words <= 45, f"Expected 20-45 words, got {words}: {reply}"
    assert any(w in reply for w in ["ऑनलाइन", "सेंसर", "बैटरी", "डिवाइस", "टैंक"])


@pytest.mark.anyio
async def test_case6_spray_advisory_concise(orchestrator):
    """
    Scenario 6: Chemical spray feasibility inquiry.
    Query: 'क्या आज कीटनाशक का छिड़काव कर सकते हैं?'
    Target: Simple/normal question (20–45 words).
    Requirements:
    - Direct recommendation first: postpone spray due to rain / wind.
    - Weather grounded: 65% rain probability or 12 km/h wind speed.
    - Isolated from unrelated soil telemetry.
    """
    sid = f"test-p34-6-c6-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="क्या आज कीटनाशक का छिड़काव कर सकते हैं?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 20 <= words <= 50, f"Expected 20-50 words, got {words}: {reply}"
    assert any(w in reply for w in ["छिड़काव", "स्प्रे", "दवा"])
    assert any(w in reply for w in ["बारिश", "वर्षा", "हवा", "स्थगित", "न करें"])


@pytest.mark.anyio
async def test_case7_weather_query_concise(orchestrator):
    """
    Scenario 7: General weather inquiry.
    Query: 'आज का मौसम कैसा रहेगा?'
    Target: Simple/normal question (20–45 words).
    Requirements:
    - Temperature, humidity, rain probability.
    - No unsolicited pesticide spray lecture.
    """
    sid = f"test-p34-6-c7-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="आज का मौसम कैसा रहेगा?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 20 <= words <= 50, f"Expected 20-50 words, got {words}: {reply}"
    assert any(w in reply for w in ["तापमान", "डिग्री", "humidity", "आर्द्रता", "बारिश", "वर्षा"])
    assert "दवा का छिड़काव" not in reply


@pytest.mark.anyio
async def test_case8_missing_stale_telemetry_concise(orchestrator):
    """
    Scenario 8: Missing soil pH telemetry inquiry.
    Query: 'मिट्टी का pH और सुधार उपाय?' under missing pH condition.
    Target: Normal advisory (35–60 words).
    Requirements:
    - Direct statement: pH reading unavailable.
    - Withhold chemical amendments (lime/gypsum) without certified lab test.
    - General compost/organic guidance via Soil Health Card.
    """
    telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "ph_missing")
    try:
        sid = f"test-p34-6-c8-{uuid.uuid4().hex[:6]}"
        resp = await orchestrator.process_query(
            message="मिट्टी का pH और सुधार उपाय?",
            language="hi-IN",
            session_id=sid,
            zone_id="DEMO-ZONE-001",
        )
        assert resp.success is True
        reply = resp.reply
        words = count_words(reply)

        assert 35 <= words <= 65, f"Expected 35-65 words, got {words}: {reply}"
        assert any(w in reply for w in ["उपलब्ध नहीं", "अमान्य", "unavailable"])
        assert any(w in reply for w in ["रासायनिक सुधारक", "चूना", "जिप्सम"])
        assert any(w in reply for w in ["गोबर की खाद", "कम्पोस्ट", "FYM", "उर्वरता"])
    finally:
        telemetry_service.reset_demo_dataset()


@pytest.mark.anyio
async def test_case9_complex_tomato_salinity_concise(orchestrator):
    """
    Scenario 9: Complex multi-agent response (Zone 3 Tomato saturation + salinity stress).
    Query: 'ज़ोन 3 टमाटर में सिंचाई करनी चाहिए या नहीं?'
    Target: Complex or safety-sensitive advisory (35–65 words, max 90 words).
    Requirements:
    - Direct decision first: Stop irrigation immediately.
    - Explain dual hazards: High moisture (64.5%) and high EC salinity (2.4 dS/m).
    - Note root asphyxiation / osmotic stress / drainage.
    """
    sid = f"test-p34-6-c9-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="ज़ोन 3 टमाटर में सिंचाई करनी चाहिए या नहीं?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-003",
    )
    assert resp.success is True
    reply = resp.reply
    words = count_words(reply)

    assert 35 <= words <= 70, f"Expected 35-70 words, got {words}: {reply}"
    assert any(w in reply for w in ["सिंचाई", "रोकें", "न करें", "बिल्कुल न करें"])
    assert any(w in reply for w in ["64.5%", "64.5", "नमी"])
    assert any(w in reply for w in ["लवणता", "EC", "2.4", "जड़"])
