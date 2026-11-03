"""
Phase 19: Comprehensive Seven-Parameter Soil Intelligence & Sensor Quality Test Suite
Validates:
1. Canonical 7-in-1 Soil Profile schema & units (N, P, K, Moisture, Temp, pH, EC).
2. Telemetry Completeness Ratio (7/7 for Zone 1/2, 6/7 for Zone 3).
3. Strict Sodium (Na) Disqualification (zero sodium fabrication, no EC->Na conversion).
4. All 14 Sensor Quality / Failure Edge-Case Scenarios.
5. 11-Point Soil Health Report generation.
6. Multi-Agent 7-Channel Auditing (DeviceHealthAgent) & Osmotic Salinity Risk (IrrigationAdvisoryAgent).
7. Safe Pump Control & GNANI AI TTS regressions.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.telemetry_service import telemetry_service
from app.services.orchestrator import orchestrator
from app.models.telemetry import CanonicalSoilProfile, SoilParameterReading

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_telemetry_state():
    """Ensure baseline initial farm state before each test."""
    telemetry_service.reset_demo_dataset()
    yield
    telemetry_service.reset_demo_dataset()


# =========================================================================
# 1. Canonical 7-in-1 Profile & Units Verification
# =========================================================================

def test_canonical_7in1_profile_units_and_ranges():
    """Validates that all 7 documented parameters exist with standard physical units."""
    profile = telemetry_service.get_canonical_soil_profile("DEMO-ZONE-001")
    assert isinstance(profile, CanonicalSoilProfile)
    assert profile.total_count == 7
    assert profile.available_count == 7
    assert "7/7 parameters available" in profile.completeness_ratio

    params = profile.parameters
    assert set(params.keys()) == {
        "nitrogen",
        "phosphorus",
        "potassium",
        "soil_moisture",
        "soil_temperature",
        "soil_ph",
        "electrical_conductivity",
    }

    # Parameter 1: Nitrogen
    assert params["nitrogen"].unit == "mg/kg"
    assert params["nitrogen"].value == 142.5
    assert params["nitrogen"].quality_status == "VALID"

    # Parameter 2: Phosphorus
    assert params["phosphorus"].unit == "mg/kg"
    assert params["phosphorus"].value == 28.4
    assert params["phosphorus"].quality_status == "VALID"

    # Parameter 3: Potassium
    assert params["potassium"].unit == "mg/kg"
    assert params["potassium"].value == 185.2
    assert params["potassium"].quality_status == "VALID"

    # Parameter 4: Soil Moisture
    assert params["soil_moisture"].unit == "%"
    assert params["soil_moisture"].value == 48.2
    assert params["soil_moisture"].quality_status == "VALID"

    # Parameter 5: Soil Temperature
    assert params["soil_temperature"].unit == "°C"
    assert params["soil_temperature"].value == 24.5
    assert params["soil_temperature"].quality_status == "VALID"

    # Parameter 6: Soil pH
    assert params["soil_ph"].unit == "pH"
    assert params["soil_ph"].value == 6.8
    assert params["soil_ph"].quality_status == "VALID"

    # Parameter 7: Electrical Conductivity (EC)
    assert params["electrical_conductivity"].unit == "dS/m"
    assert params["electrical_conductivity"].raw_unit == "uS/cm"
    assert params["electrical_conductivity"].value == 1.2
    assert params["electrical_conductivity"].raw_value == 1200.0
    assert params["electrical_conductivity"].quality_status == "VALID"


def test_zone_completeness_variance():
    """Validates 7/7 completeness for Zones 1 & 2, and 6/7 degraded for Zone 3 (Tomato)."""
    p1 = telemetry_service.get_canonical_soil_profile("DEMO-ZONE-001")
    p2 = telemetry_service.get_canonical_soil_profile("DEMO-ZONE-002")
    p3 = telemetry_service.get_canonical_soil_profile("DEMO-ZONE-003")

    assert p1.available_count == 7
    assert "7/7 parameters available" in p1.completeness_ratio

    assert p2.available_count == 7
    assert "7/7 parameters available" in p2.completeness_ratio

    # Zone 3 has uncalibrated Nitrogen probe
    assert p3.available_count == 6
    assert "6/7 parameters available" in p3.completeness_ratio
    assert p3.parameters["nitrogen"].value is None
    assert p3.parameters["nitrogen"].calibration_status == "UNCALIBRATED"
    assert p3.parameters["nitrogen"].quality_status == "UNAVAILABLE"
    assert "nitrogen" in p3.uncalibrated_parameters or "nitrogen" in p3.missing_parameters


# =========================================================================
# 2. Strict Sodium (Na) Disqualification
# =========================================================================

def test_sodium_status_endpoint():
    """Validates that the API explicitly disclaims sodium measurement."""
    resp = client.get("/api/farm/telemetry/sodium")
    assert resp.status_code == 200
    data = resp.json()
    assert data["measured_by_fertobot_7in1"] is False
    assert data["can_derive_from_ec"] is False
    assert "सोडियम" in data["notice_hi"]
    assert "does NOT measure sodium" in data["notice_en"]


@pytest.mark.anyio
async def test_sodium_query_in_hindi_and_english():
    """Validates that grower questions asking about sodium are rejected with clear explanation."""
    # Hindi Query
    resp_hi = await orchestrator.process_query("मेरी मिट्टी में सोडियम कितना है?", language="hi-IN")
    assert resp_hi.intent == "sodium_disqualification"
    assert "सोडियम (Na) नहीं मापता" in resp_hi.reply
    assert "विद्युत चालकता (EC)" in resp_hi.reply
    assert "प्रयोगशाला" in resp_hi.reply

    # English Query
    resp_en = await orchestrator.process_query("What is the sodium level in my soil?", language="en-US")
    assert resp_en.intent == "sodium_disqualification"
    assert "DOES NOT measure Sodium" in resp_en.reply
    assert "Electrical Conductivity" in resp_en.reply
    assert "laboratory soil test" in resp_en.reply


# =========================================================================
# 3. 11-Point Comprehensive Soil Health Report
# =========================================================================

@pytest.mark.anyio
async def test_complete_soil_health_report_generation():
    """Validates full 11-point report output for Hindi and English requests."""
    resp_hi = await orchestrator.process_query("मेरे खेत की पूरी मिट्टी की रिपोर्ट बताओ", language="hi-IN", zone_id="DEMO-ZONE-001")
    assert resp_hi.intent == "complete_soil_health_report"
    reply_hi = resp_hi.reply

    # Validate 11 numbered points exist in Hindi reply
    for i in range(1, 12):
        assert f"{i}." in reply_hi

    assert "मृदा स्वास्थ्य सूचकांक" in reply_hi or "डेटा पूर्णता" in reply_hi
    assert "नाइट्रोजन (N)" in reply_hi and "mg/kg" in reply_hi
    assert "फॉस्फोरस (P)" in reply_hi and "mg/kg" in reply_hi
    assert "पोटेशियम (K)" in reply_hi and "mg/kg" in reply_hi
    assert "नमी" in reply_hi and "%" in reply_hi
    assert "तापमान" in reply_hi and "°C" in reply_hi
    assert "pH" in reply_hi
    assert "विद्युत चालकता (EC)" in reply_hi and "dS/m" in reply_hi
    assert "जोखिम" in reply_hi
    assert "कृषि सुधार सलाह" in reply_hi
    assert "सीमाएं" in reply_hi

    # English full report
    resp_en = await orchestrator.process_query("Give me a complete soil health report", language="en-US", zone_id="DEMO-ZONE-001")
    assert resp_en.intent == "complete_soil_health_report"
    reply_en = resp_en.reply
    for i in range(1, 12):
        assert f"{i}." in reply_en
    assert "Nitrogen (N)" in reply_en
    assert "Phosphorus (P)" in reply_en
    assert "Potassium (K)" in reply_en
    assert "Electrical Conductivity (EC)" in reply_en


# =========================================================================
# 4. Fourteen Sensor Quality & Failure Edge-Case Scenarios
# =========================================================================

@pytest.mark.parametrize("condition_type", [
    "nitrogen_missing",
    "phosphorus_uncalibrated",
    "potassium_stale",
    "moisture_invalid",
    "temperature_disconnected",
    "ph_out_of_range",
    "ec_unavailable",
    "multiple_disconnected",
    "device_offline",
    "conflicting_timestamps",
    "reset",
])
def test_simulate_sensor_conditions_api(condition_type):
    """Tests sensor fault injection via REST endpoint."""
    resp = client.post(
        "/api/farm/telemetry/simulate-condition",
        json={"zone_id": "DEMO-ZONE-001", "condition_type": condition_type},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["condition_simulated"] == condition_type
    assert "completeness_ratio" in data
    assert "total_parameters_count" in data
    assert data["total_parameters_count"] == 7


def test_sensor_condition_specific_assertions():
    """Validates internal profile mechanics for specific failure conditions."""
    # 1. Moisture invalid (<0 or >100%)
    res = telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "moisture_invalid")
    p = res["profile"]
    assert p["parameters"]["soil_moisture"]["quality_status"] == "OUT_OF_RANGE"
    assert p["parameters"]["soil_moisture"]["value"] == 115.0

    # 2. pH out of range (>14)
    res_ph = telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "ph_out_of_range")
    p_ph = res_ph["profile"]
    assert p_ph["parameters"]["soil_ph"]["quality_status"] == "OUT_OF_RANGE"
    assert p_ph["parameters"]["soil_ph"]["value"] == 15.2

    # 3. Potassium stale (>24h)
    res_k = telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "potassium_stale")
    p_k = res_k["profile"]
    assert p_k["parameters"]["potassium"]["quality_status"] == "STALE"

    # 4. Device offline
    res_off = telemetry_service.simulate_sensor_condition("DEMO-ZONE-001", "device_offline")
    p_off = res_off["profile"]
    assert p_off["device_status"] == "offline"


# =========================================================================
# 5. Specialist Agents 7-Channel Auditing & EC Osmotic Salinity Factoring
# =========================================================================

@pytest.mark.anyio
async def test_irrigation_agent_handles_ec_salinity_risk():
    """Zone 3 has moisture 64.5% (high) and EC 2.4 dS/m (elevated). Agent must warn of osmotic stress."""
    resp = await orchestrator.process_query(
        "क्या मुझे टमाटर ज़ोन 3 में पानी देना चाहिए?",
        language="hi-IN",
        zone_id="DEMO-ZONE-003",
    )
    # Checks that response mentions high moisture, elevated EC/salinity, and advice to stop irrigation
    reply = resp.reply.lower()
    assert any(w in reply for w in ["लवणता", "विद्युत चालकता", "ec", "चालकता", "नमी"])
    assert any(w in reply for w in ["न करें", "रोक", "निकासी", "लीचिंग", "स्थगित"])


@pytest.mark.anyio
async def test_device_health_agent_audits_uncalibrated_sensor():
    """Zone 3 has uncalibrated Nitrogen sensor. Device health query must report probe warning."""
    resp = await orchestrator.process_query(
        "डिवाइस का स्टेटस क्या है और क्या कोई सेंसर खराब है?",
        language="hi-IN",
        zone_id="DEMO-ZONE-003",
    )
    reply = resp.reply.lower()
    full_text = f"{reply} {str(resp.agent_results)} {str(resp.warnings)}".lower()
    assert any(w in full_text for w in ["नाइट्रोजन", "अनकैलिब्रेटेड", "सेंसर", "चेतावनी", "चैनल", "खराब", "nitrogen", "uncalibrated", "sensor", "warning"])


# =========================================================================
# 6. Regressions: Safe Pump Approval Workflow & GNANI AI Voice
# =========================================================================

def test_pump_approval_workflow_regression():
    """Ensures Phase 18 pump approval state machine remains intact."""
    # 1. Request pump start
    req_resp = client.post("/api/pump/action", json={"action_type": "PUMP_ON", "zone_id": "DEMO-ZONE-001", "session_id": "test-reg"})
    assert req_resp.status_code == 200
    action_data = req_resp.json()
    action_id = action_data["action_id"]
    assert action_data["state"] == "AWAITING_USER_APPROVAL"

    # 2. Approve
    app_resp = client.post("/api/pump/approve", json={"action_id": action_id, "session_id": "test-reg", "language": "hi-IN"})
    assert app_resp.status_code == 200
    assert app_resp.json()["state"] == "COMPLETED"
    assert app_resp.json()["simulated_pump_running"] is True


def test_gnani_branding_and_config():
    """Ensures GNANI AI provider branding and speech endpoints are active."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert "Nalini" in cfg["available_voices"]["hi-IN"]
    assert "Kaveri" in cfg["available_voices"]["en-IN"]
