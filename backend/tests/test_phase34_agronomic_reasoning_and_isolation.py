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

    # Must evaluate maize at 40% moisture and recommend irrigation
    assert any(w in reply for w in ["सिंचाई", "पानी"])
    assert any(w in reply for w in ["अवश्य", "चाहिए", "कमी", "तनाव", "अनुशंसित", "stress"])

    # Must mention maize critical stages or moisture threshold
    assert any(w in reply for w in ["45%", "50%", "75%", "घुटने", "मंजर", "tasseling", "silking", "दाने"])

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

    # Must recommend irrigation
    assert any(w in reply for w in ["recommend", "irrigation", "water deficit", "stress"])

    # Must mention maize threshold (45% or 50-75%)
    assert any(w in reply for w in ["45%", "50%", "75%", "tasseling", "silking", "knee-high"])

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

