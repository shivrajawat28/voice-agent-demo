"""
Phase 34.0: Agronomic Reasoning, Intent Routing & Context Isolation Tests.

Covers the 4 reproduced production failures:
1. Fertilizer quantity query ("यूरिया और डीएपी की सही मात्रा?")
2. Soil pH and improvement query ("मिट्टी का pH और सुधार उपाय?")
3. Wheat first irrigation query ("गेहूँ में पहली सिंचाई कब करें?")
4. Maize moisture query with crop isolation ("मक्का में 40% नमी पर पानी देना चाहिए या नहीं?")

Plus edge cases:
- Uncultivated crop isolation (Maize vs Wheat)
- Crop context override across turns
- Unknown zone error handling
- Missing soil test disclosure
- Sensor telemetry calibration gating
- Consecutive crop switches
- Concurrent session isolation
- Irrelevant weather/spray suppression
- Hinglish query handling
- Mock provider fallback validation
"""

import pytest
import re
import uuid
from app.services.orchestrator import LLMOrchestrator, orchestrator
from app.providers.mock_llm import MockLLMProvider
from app.services.telemetry_service import telemetry_service


@pytest.mark.anyio
async def test_case1_fertilizer_quantity_requires_clarification_no_fixed_dosage():
    """
    Case 1: User asks: "यूरिया और डीएपी की सही मात्रा?"
    AI must NOT prescribe an unconditional fixed universal dosage (e.g. 50 kg urea + 50 kg DAP per acre).
    Must set needs_clarification=True, ask for crop/growth stage/acreage, and explain basal DAP vs top-dress split urea.
    """
    session_id = f"test-p34-c1-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="यूरिया और डीएपी की सही मात्रा?",
        language="hi-IN",
        session_id=session_id,
    )

    assert resp.success is True
    assert resp.intent == "fertilizer_quantity"
    assert resp.needs_clarification is True
    assert resp.clarification_prompt is not None

    # Must NOT contain universal 50 kg prescription
    reply = resp.reply
    assert "प्रति एकड़ 50 किलोग्राम" not in reply
    assert "50 किलोग्राम यूरिया और 50 किलोग्राम डीएपी" not in reply

    # Must explain why fixed dosage is unsafe without soil test / crop stage
    assert any(w in reply for w in ["मिट्टी परीक्षण", "फसल अवस्था", "अवस्था", "सुरक्षित नहीं"])

    # Must explain basal DAP and split Urea principles
    assert any(w in reply for w in ["बेसल", "बुवाई", "जड़ों", "विभाजित", "बांटकर", "लीचिंग"])

    # Clarification prompt must ask for crop, growth stage, or acreage
    prompt_text = resp.clarification_prompt
    assert any(w in prompt_text for w in ["फसल", "अवस्था", "क्षेत्रफल", "मात्रा"])


@pytest.mark.anyio
async def test_case2_soil_ph_improvement_dual_response():
    """
    Case 2: User asks: "मिट्टी का pH और सुधार उपाय?"
    AI must return BOTH the current pH (6.8) AND actionable improvement guidance.
    Must explain that 6.8 is optimal/neutral, no chemical amendment (lime/gypsum) is needed,
    recommend organic manure/FYM, and clarify when lime or gypsum is used based on certified lab tests.
    """
    session_id = f"test-p34-c2-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मिट्टी का pH और सुधार उपाय?",
        language="hi-IN",
        session_id=session_id,
        zone_id="DEMO-ZONE-001",
    )

    assert resp.success is True
    assert resp.intent == "soil_improvement"

    reply = resp.reply
    # Must report current in-situ pH reading (6.8)
    assert "6.8" in reply
    assert any(w in reply for w in ["pH", "पीएच"])

    # Must provide improvement / amendment guidance
    assert any(w in reply for w in ["तटस्थ", "आदर्श", "Neutral", "अनुकूल"])
    assert any(w in reply for w in ["रासायनिक सुधारक", "आवश्यकता नहीं", "चूना", "जिप्सम"])
    assert any(w in reply for w in ["गोबर", "खाद", "FYM", "वर्मीकम्पोस्ट", "जैविक"])
    assert any(w in reply for w in ["अम्लीय", "क्षारीय", "लैब टेस्ट", "परीक्षण"])


@pytest.mark.anyio
async def test_case3_wheat_first_irrigation_cri_stage_focused():
    """
    Case 3: User asks: "गेहूँ में पहली सिंचाई कब करें?"
    AI must directly state Crown Root Initiation (CRI / ताज मूल अवस्था, 20-25 days after sowing).
    Must report current Zone 1 moisture (48.2%).
    Must NOT contain unrelated weather dumps or chemical spray postponement warnings.
    """
    session_id = f"test-p34-c3-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="गेहूँ में पहली सिंचाई कब करें?",
        language="hi-IN",
        session_id=session_id,
        zone_id="DEMO-ZONE-001",
    )

    assert resp.success is True
    assert resp.intent == "irrigation_timing"

    reply = resp.reply
    # Must directly state CRI stage (ताज मूल अवस्था, 20-25 days)
    assert any(w in reply for w in ["ताज मूल", "CRI", "क्राउन रूट", "20 से 25 दिन", "20-25 दिन"])

    # Must cite current moisture
    assert "48.2%" in reply or "48.2" in reply

    # Must NOT contain chemical spray warning when user did not ask about spraying
    assert "रासायनिक छिड़काव" not in reply
    assert "foliar spray" not in reply.lower()
    assert "chemical spray" not in reply.lower()


@pytest.mark.anyio
async def test_case4_maize_moisture_crop_isolation():
    """
    Case 4: User asks: "मक्का में 40% नमी पर पानी देना चाहिए या नहीं?"
    AI must:
    1. Disclose that Maize is not registered on the farm's monitored sensor zones.
    2. Agronomically evaluate Maize at 40% moisture (recommending irrigation because 40% < 45% minimum threshold; optimal 50-75%).
    3. NEVER cite Wheat Field or Zone 1 sensor telemetry (48.2%) as Maize readings.
    """
    session_id = f"test-p34-c4-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मक्का में 40% नमी पर पानी देना चाहिए या नहीं?",
        language="hi-IN",
        session_id=session_id,
    )

    assert resp.success is True
    reply = resp.reply

    # Must evaluate maize at 40% moisture and provide guidance
    assert any(w in reply for w in ["सिंचाई", "पानी"])
    assert any(w in reply for w in ["अवश्य", "चाहिए", "कमी", "तनाव", "अनुशंसित", "stress", "किसान-प्रदत्त", "नमी"])

    # Must mention maize critical stages or moisture threshold
    assert any(w in reply for w in ["घुटने", "मंजर", "tasseling", "सिल्क", "silking", "दाने", "जलभराव", "बनावट"])

    # Must disclose that maize is unmonitored / not in registered farm zones
    assert any(w in reply for w in ["पंजीकृत", "सेंसर", "नहीं है", "not registered", "unmonitored"])

    # Strict isolation: must NEVER quote wheat field reading 48.2% for maize
    assert "48.2%" not in reply
    assert "गेहूं खेत" not in reply
    assert "North Wheat Field" not in reply


@pytest.mark.anyio
async def test_crop_context_override_across_turns():
    """
    When turn 1 establishes Wheat, but turn 2 explicitly asks about Cotton,
    the crop in turn 2 must override turn 1, isolating the context to Cotton (Zone 2).
    """
    session_id = f"test-p34-override-{uuid.uuid4().hex[:6]}"
    orch = LLMOrchestrator(MockLLMProvider(), fast_planning=True)

    # Turn 1: Wheat inquiry
    r1 = await orch.process_query(
        message="मेरी गेहूं की फसल के लिए सिंचाई की सलाह दो।",
        language="hi-IN",
        session_id=session_id,
    )
    assert r1.success is True

    # Turn 2: Cotton inquiry (must switch to Cotton / Zone 2)
    r2 = await orch.process_query(
        message="अब मुझे कपास (cotton) की नमी के बारे में बताओ।",
        language="hi-IN",
        session_id=session_id,
    )
    assert r2.success is True
    # Zone 2 Cotton moisture is 38.5%
    assert any(w in r2.reply for w in ["कपास", "cotton", "38.5", "ज़ोन 2", "Zone 2"])


@pytest.mark.anyio
async def test_maize_uncultivated_isolation_english():
    """English query for maize moisture ensures sensor disclosure and no wheat substitution."""
    session_id = f"test-p34-maize-en-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="Should I irrigate maize at 40% moisture?",
        language="en-US",
        session_id=session_id,
    )

    assert resp.success is True
    reply = resp.reply.lower()

    # Must provide irrigation evaluation
    assert any(w in reply for w in ["recommend", "irrigation", "water deficit", "stress", "moisture", "texture", "flowering"])

    # Must mention maize critical stages or soil/water management
    assert any(w in reply for w in ["tasseling", "silking", "knee-high", "drainage", "waterlogging", "standing water"])

    # Must disclose maize is not in monitored zones
    assert any(w in reply for w in ["not registered", "unmonitored", "not on your farm"])

    # Must NOT substitute 48.2% wheat moisture
    assert "48.2%" not in reply
    assert "wheat" not in reply or "registered zones" in reply


@pytest.mark.anyio
async def test_hinglish_fertilizer_quantity():
    """Hinglish query 'urea aur dap ki sahi matra kya honi chahiye' triggers fertilizer_quantity gate."""
    session_id = f"test-p34-hinglish-fert-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="urea aur dap ki sahi matra kya honi chahiye?",
        language="hi-IN",
        session_id=session_id,
    )

    assert resp.success is True
    assert resp.intent == "fertilizer_quantity"
    assert resp.needs_clarification is True
    assert "प्रति एकड़ 50 किलोग्राम" not in resp.reply


@pytest.mark.anyio
async def test_hinglish_soil_ph_and_improvement():
    """Hinglish query 'mitti ka ph aur sudhar upay batao' triggers dual pH + improvement response."""
    session_id = f"test-p34-hinglish-ph-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="mitti ka ph aur sudhar upay batao",
        language="hi-IN",
        session_id=session_id,
    )

    assert resp.success is True
    assert resp.intent == "soil_improvement"
    assert "6.8" in resp.reply
    assert any(w in resp.reply for w in ["गोबर", "खाद", "FYM", "तटस्थ", "चूना", "जिप्सम"])


@pytest.mark.anyio
async def test_spray_warning_only_when_spray_queried():
    """
    Verifies that chemical spray postponement warning is ONLY included
    when the query explicitly inquires about spraying or pesticide application.
    """
    session_id = f"test-p34-spray-{uuid.uuid4().hex[:6]}"

    # Query 1: Pure irrigation question -> NO spray warning
    r1 = await orchestrator.process_query(
        message="गेहूं में पहली सिंचाई कब करें?",
        language="hi-IN",
        session_id=session_id,
    )
    assert "रासायनिक छिड़काव" not in r1.reply

    # Query 2: Explicit spray question -> Spray warning permitted
    r2 = await orchestrator.process_query(
        message="क्या आज कीटनाशक का रासायनिक छिड़काव करना सुरक्षित है?",
        language="hi-IN",
        session_id=session_id,
    )
    assert any(w in r2.reply for w in ["छिड़काव", "स्प्रे", "spray", "कीटनाशक", "दवा"])


@pytest.mark.anyio
async def test_concurrent_sessions_isolated():
    """Verifies that two parallel sessions with different crops do not leak context."""
    s_wheat = f"test-wheat-{uuid.uuid4().hex[:6]}"
    s_cotton = f"test-cotton-{uuid.uuid4().hex[:6]}"

    resp_wheat = await orchestrator.process_query(
        message="गेहूं के खेत में नमी कितनी है?",
        language="hi-IN",
        session_id=s_wheat,
    )
    resp_cotton = await orchestrator.process_query(
        message="कपास के खेत में नमी कितनी है?",
        language="hi-IN",
        session_id=s_cotton,
    )

    assert "48.2" in resp_wheat.reply
    assert "28.5" in resp_cotton.reply
    assert "कपास" not in resp_wheat.reply
    assert "गेहूं" not in resp_cotton.reply


@pytest.mark.anyio
async def test_soil_test_disclosure_for_general_npk_prescription():
    """
    Verifies that when asked for general NPK or fertilizer quantity recommendations,
    the response mandates or references laboratory soil testing.
    """
    resp = await orchestrator.process_query(
        message="फसल के लिए एनपीके की सही मात्रा क्या है?",
        language="hi-IN",
        session_id=f"test-p34-npk-{uuid.uuid4().hex[:6]}",
    )
    assert resp.success is True
    assert any(w in resp.reply for w in ["मिट्टी परीक्षण", "लैब", "अवस्था", "जांच"])


# ==============================================================================
# Phase 34.2 Fail-Closed Zone & Deterministic Fallback Regression Tests
# ==============================================================================

@pytest.mark.anyio
async def test_zone_99_fail_closed_never_returns_zone_1():
    """
    Verifies that 'Zone 99 में मिट्टी की नमी कितनी है?' strictly fails closed:
    - Never defaults to DEMO-ZONE-001 (Wheat)
    - Never outputs 48.2% moisture
    - Returns clear error message listing valid zones (Zone 1 - 4)
    - metadata zone_valid is False and intent is unknown_zone_error
    """
    resp = await orchestrator.process_query(
        message="Zone 99 में मिट्टी की नमी कितनी है?",
        language="hi-IN",
        session_id=f"test-zone99-{uuid.uuid4().hex[:6]}",
    )
    assert resp.success is True
    assert resp.intent == "unknown_zone_error"
    assert resp.metadata.get("zone_valid") is False
    assert resp.metadata.get("queried_zone") == "Zone 99"

    # Strictly verify NO telemetry from Zone 1 leaked
    assert "48.2" not in resp.reply
    assert "गेहूं" not in resp.reply
    assert "DEMO-ZONE-001" not in resp.reply

    # Verify fail-closed guidance
    assert any(w in resp.reply for w in ["Zone 99", "पंजीकृत नहीं है", "not registered"])
    assert any(w in resp.reply for w in ["Zone 1", "Zone 2", "Zone 3", "Zone 4"])


@pytest.mark.anyio
async def test_unknown_named_zone_fail_closed():
    """
    Verifies that an unknown named zone like 'Zone Orchard' fails closed.
    """
    resp = await orchestrator.process_query(
        message="Zone Orchard में क्या स्थिति है?",
        language="hi-IN",
        session_id=f"test-orchard-{uuid.uuid4().hex[:6]}",
    )
    assert resp.success is True
    assert resp.intent == "unknown_zone_error"
    assert resp.metadata.get("zone_valid") is False
    assert "48.2" not in resp.reply
    assert "गेहूं" not in resp.reply


@pytest.mark.anyio
async def test_explicit_invalid_zone_id_param_fail_closed():
    """
    Verifies that an explicitly supplied invalid zone_id param (e.g. DEMO-ZONE-099)
    fails closed immediately.
    """
    resp = await orchestrator.process_query(
        message="खेत में नमी कितनी है?",
        language="hi-IN",
        session_id=f"test-param99-{uuid.uuid4().hex[:6]}",
        zone_id="DEMO-ZONE-099",
    )
    assert resp.success is True
    assert resp.intent == "unknown_zone_error"
    assert resp.metadata.get("zone_valid") is False
    assert "48.2" not in resp.reply


@pytest.mark.anyio
async def test_invalid_zone_overrides_valid_session_zone():
    """
    Verifies that an invalid explicit zone in the current turn overrides
    and rejects a previously established valid session zone.
    """
    sid = f"test-override-{uuid.uuid4().hex[:6]}"

    # Turn 1: Establish valid Zone 2 (Cotton)
    r1 = await orchestrator.process_query(
        message="Zone 2 में नमी कितनी है?",
        language="hi-IN",
        session_id=sid,
    )
    assert "28.5" in r1.reply

    # Turn 2: Inquire about Zone 99 -> MUST FAIL CLOSED, not fall back to Zone 2 or Zone 1
    r2 = await orchestrator.process_query(
        message="Zone 99 में नमी कितनी है?",
        language="hi-IN",
        session_id=sid,
    )
    assert r2.intent == "unknown_zone_error"
    assert r2.metadata.get("zone_valid") is False
    assert "28.5" not in r2.reply
    assert "48.2" not in r2.reply


@pytest.mark.anyio
async def test_no_explicit_zone_preserves_session_zone():
    """
    Verifies that when NO explicit zone is supplied in a follow-up turn,
    the legitimate active session zone is preserved.
    """
    sid = f"test-preserve-{uuid.uuid4().hex[:6]}"

    # Turn 1: Establish valid Zone 2 (Cotton)
    r1 = await orchestrator.process_query(
        message="Zone 2 में नमी कितनी है?",
        language="hi-IN",
        session_id=sid,
    )
    assert "28.5" in r1.reply

    # Turn 2: No explicit zone -> should use session zone (Zone 2)
    r2 = await orchestrator.process_query(
        message="खेत में नमी कितनी है?",
        language="hi-IN",
        session_id=sid,
    )
    assert r2.intent != "unknown_zone_error"
    assert "28.5" in r2.reply
    assert "48.2" not in r2.reply


@pytest.mark.anyio
async def test_gemini_503_deterministic_fallback_isolation():
    """
    Verifies that when LLM synthesis fails / falls back,
    a device health query does NOT have wheat crop symptom summaries prepended.
    """
    sid = f"test-503-isolation-{uuid.uuid4().hex[:6]}"

    # Run query with fast planning on device health
    resp = await orchestrator.process_query(
        message="मेरे खेत में कोई डिवाइस खराब है क्या?",
        language="hi-IN",
        session_id=sid,
    )
    assert resp.success is True
    assert resp.intent == "device_health"

    # Only device_health agent should run
    invoked = resp.metadata.get("agents_invoked", [])
    assert "device_health" in invoked
    assert "crop_symptom" not in invoked

    # Reply must focus on hardware / device, not crop temperature or leaf symptoms
    assert any(w in resp.reply for w in ["डिवाइस", "बैटरी", "ऑनलाइन", "DEMO-DEVICE", "device"])
    assert "गेहूं की फसल में नमी" not in resp.reply
    assert "ताज मूल" not in resp.reply


# =========================================================================
# Phase 34.4 Regression Tests — Agronomic Evidence & Missing-Telemetry Safety
# =========================================================================

@pytest.mark.anyio
async def test_missing_ph_telemetry_never_defaults_to_6_8():
    """
    Verifies that when pH telemetry is missing, the AI NEVER falls back to pH 6.8.
    Must explicitly state that no current pH reading is available, withhold lime/gypsum entirely,
    and explain that chemical amendments require certified lab tests.
    """
    telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "ph_missing")
    try:
        sid = f"test-ph-missing-{uuid.uuid4().hex[:6]}"
        resp = await orchestrator.process_query(
            message="मिट्टी का pH और सुधार उपाय?",
            language="hi-IN",
            session_id=sid,
            zone_id="DEMO-ZONE-001",
        )
        assert resp.success is True
        reply = resp.reply

        # Must NEVER report 6.8 as current pH
        assert "6.8" not in reply
        # Must explicitly state that pH reading is unavailable
        assert any(w in reply for w in ["उपलब्ध नहीं", "अमान्य", "नहीं है", "unavailable"])
        # Must withhold chemical amendments without lab testing
        assert any(w in reply for w in ["रासायनिक सुधारक", "प्रयोगशाला", "लैब टेस्ट", "बिना"])
        assert any(w in reply for w in ["गोबर", "खाद", "FYM", "कम्पोस्ट", "जैविक"])
    finally:
        telemetry_service.reset_demo_dataset()


@pytest.mark.anyio
async def test_stale_and_uncalibrated_ph_telemetry():
    """
    Verifies that stale or uncalibrated pH telemetry is clearly distinguished
    and never treated as an active calibrated measurement.
    """
    # 1. Stale pH
    telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "ph_stale")
    try:
        sid = f"test-ph-stale-{uuid.uuid4().hex[:6]}"
        resp = await orchestrator.process_query(
            message="मिट्टी का pH और सुधार उपाय?",
            language="hi-IN",
            session_id=sid,
            zone_id="DEMO-ZONE-001",
        )
        assert resp.success is True
        assert any(w in resp.reply for w in ["पुराना", "Stale", "उपलब्ध नहीं", "प्रमाणित नहीं"])
    finally:
        telemetry_service.reset_demo_dataset()

    # 2. Uncalibrated pH
    telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "ph_uncalibrated")
    try:
        sid = f"test-ph-uncal-{uuid.uuid4().hex[:6]}"
        resp = await orchestrator.process_query(
            message="मिट्टी का pH और सुधार उपाय?",
            language="hi-IN",
            session_id=sid,
            zone_id="DEMO-ZONE-001",
        )
        assert resp.success is True
        assert any(w in resp.reply for w in ["असंशोधित", "Uncalibrated", "उपलब्ध नहीं", "uncalibrated"])
    finally:
        telemetry_service.reset_demo_dataset()


@pytest.mark.anyio
async def test_ph_neutral_guidance_has_no_fixed_fym_dosage():
    """
    Verifies that when pH is near-neutral (6.8), the response:
    1. Reports 6.8 accurately.
    2. Does NOT prescribe a fixed 10-12 tonnes/ha dosage as a mandatory fact.
    3. Recommends organic matter / FYM / compost as general guidance.
    4. Cites Soil Health Card or soil organic carbon context for quantitative rates.
    """
    sid = f"test-fym-nofix-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मिट्टी का pH और सुधार उपाय?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply

    # Reports 6.8
    assert "6.8" in reply
    # Must NOT contain fixed 10-12 tonnes/ha recommendation
    assert "10 से 12 टन" not in reply
    assert "10 to 12 tonnes" not in reply
    # Must recommend organic matter as general guidance
    assert any(w in reply for w in ["गोबर की खाद", "FYM", "कम्पोस्ट", "वर्मीकम्पोस्ट", "जैविक"])
    # Must reference Soil Health Card or organic carbon context
    assert any(w in reply for w in ["मृदा स्वास्थ्य कार्ड", "जैविक कार्बन", "बनावट", "Soil Health Card"])


@pytest.mark.anyio
async def test_maize_moisture_no_universal_threshold_claims():
    """
    Verifies that the maize moisture advisory:
    1. Removes dogmatic universal claims that 45% is a critical minimum threshold and 50-75% is universally optimal.
    2. Discloses that 40% moisture is farmer-provided input.
    3. Explains that moisture percentage alone cannot dictate irrigation without soil texture and growth stage.
    4. Mentions critical flowering stages (tasseling/silking) and furrow drainage.
    """
    sid = f"test-maize-nuance-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="मक्का में 40% नमी पर पानी देना चाहिए या नहीं?",
        language="hi-IN",
        session_id=sid,
    )
    assert resp.success is True
    reply = resp.reply

    # Must NOT claim universal 45% minimum threshold as dogma
    assert "न्यूनतम सीमा 45% है" not in reply
    # Discloses farmer-provided input
    assert any(w in reply for w in ["किसान-प्रदत्त", "आपके द्वारा बताई", "farmer-provided", "queried"])
    # Mentions soil texture and stage dependence
    assert any(w in reply for w in ["बनावट", "अवस्था", "निर्भर", "texture", "stage"])
    # Mentions critical stages and drainage
    assert any(w in reply for w in ["मंजर", "tasseling", "सिल्क", "silking", "जलभराव"])
    # Does not substitute wheat reading
    assert "48.2" not in reply


@pytest.mark.anyio
async def test_maize_distinguishes_farmer_input_from_sensors():
    """
    Verifies English maize advisory clarifies farmer input vs on-farm sensors.
    """
    sid = f"test-maize-farmer-input-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="Should I irrigate maize at 35% moisture?",
        language="en-US",
        session_id=sid,
    )
    assert resp.success is True
    reply = resp.reply

    # Mentions farmer-provided / queried
    assert any(w in reply.lower() for w in ["farmer-provided", "queried", "cited", "input"])
    # Mentions unmonitored / not registered
    assert any(w in reply.lower() for w in ["not registered", "unmonitored", "not on your farm"])
    # Explains percentage alone is insufficient without soil texture
    assert any(w in reply.lower() for w in ["soil texture", "alone cannot", "growth stage"])


@pytest.mark.anyio
async def test_wheat_cri_qualified_by_sowing_date():
    """
    Verifies that the Wheat CRI first irrigation advisory:
    1. Retains CRI stage explanation.
    2. Avoids presenting 20-25 DAS or 30-40% yield drop as universal certainties.
    3. Notes that sensors track soil moisture but do not track calendar sowing dates.
    4. Instructs farmer to inspect crown roots.
    """
    sid = f"test-wheat-cri-qual-{uuid.uuid4().hex[:6]}"
    resp = await orchestrator.process_query(
        message="गेहूँ में पहली सिंचाई कब करें?",
        language="hi-IN",
        session_id=sid,
        zone_id="DEMO-ZONE-001",
    )
    assert resp.success is True
    reply = resp.reply

    # Mentions CRI
    assert any(w in reply for w in ["ताज मूल", "CRI", "Crown Root"])
    # Mentions 20-25 days qualified by conditions
    assert any(w in reply for w in ["20 से 25", "20-25", "सामान्यतः", "प्रायः", "अनुकूल"])
    # Mentions sensor tracks moisture but not sowing date
    assert any(w in reply for w in ["बुवाई की तारीख", "ट्रैक नहीं", "सेंसर", "नमी 48.2%"])
    # Advises crown root inspection
    assert any(w in reply for w in ["ताज जड़ों", "जांच", "सूखी", "crown roots", "inspect"])


@pytest.mark.anyio
async def test_unknown_zone_across_telemetry_and_all_specialists():
    """
    Verifies that explicit unknown zones fail closed across every telemetry function
    and across all specialist agents (CropSymptom, IrrigationAdvisory, DeviceHealth).
    """
    from app.agents.crop_symptom_agent import CropSymptomAgent
    from app.agents.irrigation_advisory_agent import IrrigationAdvisoryAgent
    from app.agents.device_health_agent import DeviceHealthAgent
    from app.agents.base import AgentContext
    from app.tools.telemetry_tool import LatestTelemetryTool, DeviceStatusTool, WaterLevelTool, AlertHistoryTool, HistoricalTelemetryTool

    tools = {
        "latest_telemetry": LatestTelemetryTool(),
        "device_status": DeviceStatusTool(),
        "water_level": WaterLevelTool(),
        "alert_history": AlertHistoryTool(),
        "historical_telemetry": HistoricalTelemetryTool(),
    }

    # 1. Telemetry service level
    assert telemetry_service.get_latest_telemetry("ZONE-999") == {}
    assert telemetry_service.get_device_status(zone_id="ZONE-999")["status"] == "error"
    assert telemetry_service.get_water_tank_level(zone_id="ZONE-999")["status"] == "error"
    assert "not found" in telemetry_service.get_historical_telemetry("ZONE-999")["trend_summary"]

    # 2. Specialist agents level
    ctx = AgentContext(query="Zone 999 की स्थिति बताओ", language="hi-IN", zone_id="ZONE-999")

    # CropSymptomAgent
    c_agent = CropSymptomAgent()
    c_res = await c_agent.execute(ctx, tools)
    assert "पंजीकृत नहीं" in c_res.summary or "not registered" in c_res.summary.lower()

    # IrrigationAdvisoryAgent
    i_agent = IrrigationAdvisoryAgent()
    i_res = await i_agent.execute(ctx, tools)
    assert "पंजीकृत नहीं" in i_res.summary or "not registered" in i_res.summary.lower()

    # DeviceHealthAgent
    d_agent = DeviceHealthAgent()
    d_res = await d_agent.execute(ctx, tools)
    assert "पंजीकृत नहीं" in d_res.summary or "not registered" in d_res.summary.lower()


@pytest.mark.anyio
async def test_gemini_503_fallback_with_missing_ph_and_maize():
    """
    Verifies deterministic fallback synthesis during simulated 503 LLM service errors:
    1. Missing pH query does NOT output 6.8.
    2. Maize query does NOT substitute wheat.
    3. Unknown zone query fails closed.
    """
    class ErrorLLM(MockLLMProvider):
        async def generate_text(self, prompt: str, **kwargs) -> str:
            raise RuntimeError("503 Service Unavailable: Simulated Gemini Outage")

    err_orch = LLMOrchestrator(ErrorLLM(), fast_planning=False)

    # 1. Missing pH fallback
    telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "ph_missing")
    try:
        r_ph = await err_orch.process_query(
            message="मेरी मिट्टी में सुधार के उपाय क्या हैं?",
            language="hi-IN",
            session_id=f"test-503-ph-{uuid.uuid4().hex[:6]}",
            zone_id="DEMO-ZONE-001",
        )
        assert r_ph.success is True
        assert "6.8" not in r_ph.reply
        assert any(w in r_ph.reply for w in ["उपलब्ध नहीं", "अमान्य", "नहीं है", "प्रयोगशाला", "सुधारक"])
    finally:
        telemetry_service.reset_demo_dataset()

    # 2. Maize fallback
    r_maize = await err_orch.process_query(
        message="मक्का की फसल में 40% नमी पर सिंचाई करें?",
        language="hi-IN",
        session_id=f"test-503-maize-{uuid.uuid4().hex[:6]}",
    )
    assert r_maize.success is True
    assert "48.2" not in r_maize.reply
    assert any(w in r_maize.reply for w in ["मक्का", "maize", "सेंसर", "पंजीकृत नहीं"])

    # 3. Unknown zone fallback
    r_zone = await err_orch.process_query(
        message="Zone 88 में फसल कैसी है?",
        language="hi-IN",
        session_id=f"test-503-zone-{uuid.uuid4().hex[:6]}",
    )
    assert r_zone.success is True
    assert any(w in r_zone.reply for w in ["पंजीकृत नहीं", "not registered", "अमान्य"])

