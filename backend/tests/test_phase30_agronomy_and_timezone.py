"""
Phase 30 Regression Test Suite:
1. Fertilizer Consumption Query (Intent routing, 7-in-1 sensor scope vs flow meter, no fabrication, 12h IST)
2. Crop-Specific pH Intelligence (Sugarcane unregistered check, ICAR-IISR standards, wheat evaluation)
3. Nitrogen Depletion Rate (Initial/Final rate in mg/kg/day, Zone 3 uncalibrated, instantaneous snapshot disambiguation)
4. Sector 4 Mapping & Irrigation Disambiguation (Start approval card, Advisory, Stop, Negative cancellation)
5. Fertigation Scheduling (Dynamic tomorrow IST date, slot-filling)
6. Timezone Presentation (12-hour IST with AM/PM across boundaries, elimination of raw UTC)
7. Hindi Voice Consistency (Locked turn_language and turn_voice, pure Hindi templates)
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.orchestrator import LLMOrchestrator
from app.providers.mock_llm import MockLLMProvider
from app.services.telemetry_service import telemetry_service
from app.utils.timezone import to_ist, format_to_ist, get_tomorrow_ist


@pytest.fixture
def orchestrator():
    return LLMOrchestrator(MockLLMProvider())


# ---------------------------------------------------------------------------
# 1. Timezone Utility Unit Tests
# ---------------------------------------------------------------------------
def test_timezone_conversion_and_formatting():
    # 2026-11-03 00:00:00 UTC -> 05:30 AM IST (same day)
    dt1 = datetime(2026, 11, 3, 0, 0, 0, tzinfo=timezone.utc)
    assert format_to_ist(dt1) == "03 Nov 2026, 05:30 AM IST"

    # 2026-11-03 06:30:00 UTC -> 12:00 PM IST (noon)
    dt2 = datetime(2026, 11, 3, 6, 30, 0, tzinfo=timezone.utc)
    assert format_to_ist(dt2) == "03 Nov 2026, 12:00 PM IST"

    # 2026-11-03 13:00:00 UTC -> 06:30 PM IST (evening)
    dt3 = datetime(2026, 11, 3, 13, 0, 0, tzinfo=timezone.utc)
    assert format_to_ist(dt3) == "03 Nov 2026, 06:30 PM IST"

    # Across midnight boundary: 2026-11-03 20:00:00 UTC -> 2026-11-04 01:30 AM IST
    dt4 = datetime(2026, 11, 3, 20, 0, 0, tzinfo=timezone.utc)
    assert format_to_ist(dt4) == "04 Nov 2026, 01:30 AM IST"


# ---------------------------------------------------------------------------
# 2. Fertilizer Consumption Query
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_fertilizer_consumption_query_english(orchestrator):
    res = await orchestrator.process_query(
        "How much fertilizer was consumed in the last 24 hours?",
        language="en-US",
        session_id="test-fert-1",
    )
    assert res.intent == "fertilizer_consumption_query"
    # Must NOT be historical moisture trend
    assert "Soil moisture trend" not in res.reply
    # Must explain in-situ sensor scope vs volumetric consumption
    assert "in-situ soil nutrient concentrations" in res.reply
    assert "volumetric fertilizer consumption" in res.reply
    assert "flow meters" in res.reply.lower() or "dosing pump controllers" in res.reply.lower()
    # Must include IST timestamp
    assert "IST" in res.reply
    assert "UTC" not in res.reply
    # Must include metadata
    assert res.metadata.get("volumetric_tracking") == "unavailable"
    assert res.metadata.get("current_npk") is not None


@pytest.mark.anyio
async def test_fertilizer_consumption_query_hindi(orchestrator):
    res = await orchestrator.process_query(
        "पिछले 24 घंटे में कितना उर्वरक खर्च हुआ?",
        language="hi-IN",
        session_id="test-fert-2",
    )
    assert res.intent == "fertilizer_consumption_query"
    assert "7-in-1 सॉइल प्रोब" in res.reply
    assert "खपत" in res.reply
    assert "फ्लो मीटर" in res.reply or "डोजिंग" in res.reply
    assert "IST" in res.reply
    assert "UTC" not in res.reply


# ---------------------------------------------------------------------------
# 3. Crop-Specific pH Intelligence
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sugarcane_ph_query_unregistered(orchestrator):
    res = await orchestrator.process_query(
        "Is the pH level currently optimal for sugarcane?",
        language="en-US",
        session_id="test-crop-1",
    )
    assert res.intent == "soil_ph_temp_query"
    # Must state sugarcane is not registered
    assert "sugarcane is not registered" in res.reply.lower()
    # Must mention registered zones
    assert "Zone 1: Wheat" in res.reply
    # Must give ICAR-IISR optimal range 6.0 to 7.5
    assert "6.0 to 7.5" in res.reply
    assert "ICAR-IISR" in res.reply
    # Must NOT silently claim Zone 1 is sugarcane
    assert "in Zone 1 (Wheat Field), the current soil pH is 6.8 (balanced) and soil temperature" not in res.reply
    assert res.metadata.get("crop_queried") == "sugarcane"
    assert res.metadata.get("registered_on_farm") is False


@pytest.mark.anyio
async def test_sugarcane_ph_query_hindi(orchestrator):
    res = await orchestrator.process_query(
        "क्या गन्ने के लिए पीएच सही है?",
        language="hi-IN",
        session_id="test-crop-2",
    )
    assert res.intent == "soil_ph_temp_query"
    assert "गन्ना आपके खेत के किसी भी सक्रिय ज़ोन में पंजीकृत नहीं है" in res.reply
    assert "6.0 से 7.5" in res.reply
    assert "ICAR-IISR" in res.reply


@pytest.mark.anyio
async def test_wheat_ph_query_optimal(orchestrator):
    res = await orchestrator.process_query(
        "Is the pH optimal for wheat?",
        language="en-US",
        session_id="test-crop-3",
    )
    assert res.intent == "soil_ph_temp_query"
    assert "Zone 1 (Wheat Field)" in res.reply
    assert "6.8" in res.reply
    assert "6.0 to 7.5" in res.reply
    assert "IST" in res.reply
    assert "UTC" not in res.reply


# ---------------------------------------------------------------------------
# 4. Nitrogen Depletion Rate vs Instantaneous NPK Snapshot
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_nitrogen_depletion_rate_wheat(orchestrator):
    res = await orchestrator.process_query(
        "Tell me the average nitrogen depletion rate this week.",
        language="en-US",
        session_id="test-n-1",
    )
    assert res.intent == "nitrogen_depletion_query"
    assert "depletion rate" in res.reply.lower()
    assert "mg/kg/day" in res.reply
    assert "3.2" in res.reply
    assert "165.0" in res.reply
    assert "142.5" in res.reply
    # Explains biological dynamics (crop uptake, leaching, microbial)
    assert "soil-solution concentration change" in res.reply or "crop uptake" in res.reply
    assert "IST" in res.reply
    assert "UTC" not in res.reply
    assert res.metadata.get("depletion_rate_mg_kg_day") == 3.2


@pytest.mark.anyio
async def test_nitrogen_depletion_rate_hindi(orchestrator):
    res = await orchestrator.process_query(
        "इस सप्ताह नाइट्रोजन की खपत दर क्या रही?",
        language="hi-IN",
        session_id="test-n-hi",
    )
    assert res.intent == "nitrogen_depletion_query"
    assert "3.2" in res.reply
    assert "mg/kg/day" in res.reply
    assert "IST" in res.reply


@pytest.mark.anyio
async def test_nitrogen_depletion_rate_zone3_uncalibrated(orchestrator):
    res = await orchestrator.process_query(
        "Tell me the nitrogen depletion rate in zone 3.",
        language="en-US",
        session_id="test-n-2",
        zone_id="DEMO-ZONE-003",
    )
    assert res.intent == "nitrogen_depletion_query"
    assert "uncalibrated" in res.reply.lower()
    assert "cannot be calculated" in res.reply.lower()
    assert "Phosphorus is 41.0 mg/kg" in res.reply
    assert "Potassium is 195.0 mg/kg" in res.reply
    assert "Moisture is 64.5%" in res.reply
    assert res.metadata.get("status") == "uncalibrated"


@pytest.mark.anyio
async def test_current_npk_snapshot_routing(orchestrator):
    res = await orchestrator.process_query(
        "Show current NPK levels",
        language="en-US",
        session_id="test-n-3",
    )
    # Must route to instantaneous snapshot, NOT depletion rate
    assert res.intent == "npk_nutrient_query"
    assert "depletion rate" not in res.reply.lower()
    assert "142.5" in res.reply
    assert "28.4" in res.reply
    assert "185.2" in res.reply
    assert "IST" in res.reply
    assert "UTC" not in res.reply


# ---------------------------------------------------------------------------
# 5. Sector 4 Mapping & Irrigation Disambiguation
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_start_irrigation_sector4_creates_approval_card(orchestrator):
    res = await orchestrator.process_query(
        "Start the automated irrigation cycle for sector 4.",
        language="en-US",
        session_id="test-sec4-1",
    )
    assert res.intent == "pump_activation_request"
    assert res.pending_action is not None
    assert res.pending_action.zone_id == "DEMO-ZONE-004"
    assert res.pending_action.action_type == "PUMP_ON"
    assert "Sector 4" in res.reply or "DEMO-ZONE-004" in res.reply
    assert "Permission required" in res.reply
    assert res.metadata.get("zone_id") == "DEMO-ZONE-004"
    assert res.metadata.get("simulation_mode") is True
    assert res.metadata.get("actuation_permitted") is False


@pytest.mark.anyio
async def test_start_irrigation_sector4_hindi_creates_approval_card(orchestrator):
    res = await orchestrator.process_query(
        "सेक्टर 4 के लिए स्वचालित सिंचाई चक्र शुरू करें।",
        language="hi-IN",
        session_id="test-sec4-1-hi",
    )
    assert res.intent == "pump_activation_request"
    assert res.pending_action is not None
    assert res.pending_action.zone_id == "DEMO-ZONE-004"
    assert "सेक्टर 4" in res.reply
    assert "अनुमति" in res.reply


@pytest.mark.anyio
async def test_irrigation_advisory_sector4_no_action_card(orchestrator):
    res = await orchestrator.process_query(
        "Should I irrigate sector 4?",
        language="en-US",
        session_id="test-sec4-2",
    )
    assert res.intent == "irrigation_advisory_query"
    assert res.pending_action is None  # Advisory must NEVER create action card
    assert "28.2%" in res.reply
    assert "35%" in res.reply
    assert "recommended" in res.reply.lower()
    assert "IST" in res.reply
    assert "UTC" not in res.reply
    assert res.metadata.get("irrigation_recommended") is True


@pytest.mark.anyio
async def test_stop_irrigation_sector4(orchestrator):
    res = await orchestrator.process_query(
        "Stop irrigation for sector 4.",
        language="en-US",
        session_id="test-sec4-3",
    )
    assert res.intent == "pump_shutdown"
    assert "stopped" in res.reply.lower() or "shutdown" in res.reply.lower() or "off" in res.reply.lower()
    assert res.metadata.get("zone_id") == "DEMO-ZONE-004"


@pytest.mark.anyio
async def test_negative_irrigation_sector4(orchestrator):
    res = await orchestrator.process_query(
        "Do not start irrigation for sector 4.",
        language="en-US",
        session_id="test-sec4-4",
    )
    assert res.intent == "irrigation_negative_command"
    assert res.pending_action is None
    assert "will NOT be started" in res.reply
    assert "remains safely off" in res.reply
    assert res.metadata.get("zone_id") == "DEMO-ZONE-004"
    assert res.metadata.get("action_taken") == "none"


# ---------------------------------------------------------------------------
# 6. Fertigation Scheduling
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_schedule_fertigation_dynamic_tomorrow(orchestrator):
    res = await orchestrator.process_query(
        "Schedule a fertigation session for tomorrow at 6:00 AM.",
        language="en-US",
        session_id="test-fert-sched-1",
    )
    assert res.intent == "schedule_fertigation"
    tomorrow_ist = get_tomorrow_ist().strftime("%d %b %Y")
    assert tomorrow_ist in res.reply
    assert "06:00 AM IST" in res.reply
    # Missing zone triggers slot-filling clarification
    assert res.needs_clarification is True
    assert "Which zone or sector" in res.reply
    assert "simulation_mode=true" in res.reply or "Simulation Mode" in res.reply
    assert res.metadata.get("scheduled_time_ist") == f"{tomorrow_ist}, 06:00 AM IST"


# ---------------------------------------------------------------------------
# 7. Hindi Voice Consistency & Clean Templates
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_hindi_voice_locking_and_template_cleanliness(orchestrator):
    # Query 14: Historical trend in Hindi
    res = await orchestrator.process_query(
        "पिछले 7 दिनों में नमी का क्या हाल रहा?",
        language="hi-IN",
        session_id="test-hi-1",
    )
    assert res.intent == "historical_trend_query"
    # Must lock turn_language and turn_voice
    assert res.metadata.get("turn_language") == "hi-IN"
    assert res.metadata.get("turn_voice") == "Nalini"
    # Must not contain mixed English strings
    assert "Soil moisture trend" not in res.reply
    assert "Maintained stable levels" not in res.reply
    assert "over 7d" not in res.reply
    assert "नमी का रुख" in res.reply


@pytest.mark.anyio
async def test_english_voice_locking(orchestrator):
    res = await orchestrator.process_query(
        "What is the status of the water tank?",
        language="en-US",
        session_id="test-en-1",
    )
    assert res.intent == "water_level_query"
    assert res.metadata.get("turn_language") == "en-US"
    assert res.metadata.get("turn_voice") == "Kaveri"
    assert "82.0%" in res.reply or "82%" in res.reply


@pytest.mark.anyio
async def test_device_warning_query(orchestrator):
    res = await orchestrator.process_query(
        "Which device is showing a warning?",
        language="en-US",
        session_id="test-dev-warn-1",
    )
    assert res.intent == "device_warning_query"
    assert "DEMO-DEVICE-002" in res.reply
    assert "DEMO-DEVICE-003" in res.reply
    assert "16.0%" in res.reply
    assert "uncalibrated" in res.reply.lower()


# ---------------------------------------------------------------------------
# 8. Phase 30.1: Historical Data Integrity & Regression Proofs
# ---------------------------------------------------------------------------
def test_nitrogen_rate_changes_when_historical_readings_change():
    """Proves depletion rate is calculated from observed readings, not hardcoded."""
    # Baseline: 165.0 to 142.5 over 7.0 days = 3.2 mg/kg/day
    base_res = telemetry_service.calculate_nutrient_depletion_rate("DEMO-ZONE-001", "nitrogen", 7)
    assert base_res["status"] == "calculated"
    assert base_res["depletion_rate_mg_kg_day"] == 3.2
    assert base_res["initial_reading"] == 165.0
    assert base_res["final_reading"] == 142.5

    # Modify history dynamically: Initial 180.0, Final 138.0 over exactly 7.0 days
    # Expected rate: (180.0 - 138.0) / 7.0 = 42.0 / 7.0 = 6.0 mg/kg/day
    now = datetime.now(timezone.utc)
    custom_series = [
        {"timestamp_iso": (now - timedelta(days=7)).isoformat(), "nitrogen_mg_kg": 180.0},
        {"timestamp_iso": (now - timedelta(days=3.5)).isoformat(), "nitrogen_mg_kg": 159.0},
        {"timestamp_iso": now.isoformat(), "nitrogen_mg_kg": 138.0},
    ]
    telemetry_service._history["DEMO-ZONE-001"]["7d"] = custom_series

    try:
        dyn_res = telemetry_service.calculate_nutrient_depletion_rate("DEMO-ZONE-001", "nitrogen", 7)
        assert dyn_res["status"] == "calculated"
        assert dyn_res["initial_reading"] == 180.0
        assert dyn_res["final_reading"] == 138.0
        assert dyn_res["depletion_rate_mg_kg_day"] == 6.0
        assert dyn_res["total_change"] == -42.0
    finally:
        telemetry_service.reset_demo_dataset()


def test_missing_readings_produce_insufficient_data():
    """Proves missing or insufficient history produces explicit unavailable status."""
    telemetry_service._history["DEMO-ZONE-001"]["7d"] = []
    try:
        res = telemetry_service.calculate_nutrient_depletion_rate("DEMO-ZONE-001", "nitrogen", 7)
        assert res["status"] == "insufficient_data"
        assert res["valid"] is False
        assert res["available"] is False
        assert "Insufficient historical telemetry records" in res["reason"]
    finally:
        telemetry_service.reset_demo_dataset()


def test_uncalibrated_readings_excluded_and_zone3_no_fabrication():
    """Proves Zone 3 uncalibrated nitrogen probe is never fabricated."""
    res = telemetry_service.calculate_nutrient_depletion_rate("DEMO-ZONE-003", "nitrogen", 7)
    assert res["status"] == "uncalibrated"
    assert res["valid"] is False
    assert res["available"] is False
    assert res.get("initial_reading") is None
    assert res.get("depletion_rate_mg_kg_day") is None
    assert "UNCALIBRATED" in res["reason"]


def test_unknown_zones_never_return_zone1_readings():
    """Proves unknown zones return explicit error and never fallback to Zone 1."""
    # Fertilizer consumption
    fert_res = telemetry_service.get_fertilizer_consumption("DEMO-ZONE-UNKNOWN-999")
    assert fert_res["status"] == "unknown_zone"
    assert fert_res["available"] is False
    assert fert_res["current_npk"] is None
    assert "not registered on this farm" in fert_res["reason"]

    # Nutrient depletion
    dep_res = telemetry_service.calculate_nutrient_depletion_rate("DEMO-ZONE-UNKNOWN-999")
    assert dep_res["status"] == "unknown_zone"
    assert dep_res["valid"] is False
    assert dep_res["available"] is False
    assert "not registered on this farm" in dep_res["reason"]


def test_fertilizer_consumption_unavailable_without_application_records():
    """Proves fertilizer consumption is unavailable across all zones without flow meter logs."""
    for zone_id in ["DEMO-ZONE-001", "DEMO-ZONE-002", "DEMO-ZONE-003", "DEMO-ZONE-004"]:
        res = telemetry_service.get_fertilizer_consumption(zone_id)
        assert res["available"] is False
        assert res["status"] == "unavailable"
        assert "volumetric fertilizer consumption" in res["reason"]
        assert "flow meter" in res["required_hardware"].lower()
        assert res["current_npk"] is not None
        # Zone 3 nitrogen must be uncalibrated / None
        if zone_id == "DEMO-ZONE-003":
            assert res["current_npk"]["nitrogen_mg_kg"] is None
            assert res["current_npk"]["nitrogen_status"] == "uncalibrated"
        else:
            assert res["current_npk"]["nitrogen_mg_kg"] > 0
            assert res["current_npk"]["nitrogen_status"] == "active"
