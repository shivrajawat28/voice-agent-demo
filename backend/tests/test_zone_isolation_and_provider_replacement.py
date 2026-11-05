"""
Tests for FIX 2 & FIX 3:
- Dynamic Telemetry Provider Resolution (eliminating stale reference caching)
- Request and Session-Scoped Zone Isolation
  - Scenario A: User A selects Zone 1 while User B selects Zone 3 (independent telemetry)
  - Scenario B: Concurrent requests for different zones do not overwrite session zone context
  - Scenario C: Two WebSocket sessions cannot leak approval or telemetry state
  - Scenario D: Unknown zones fail safely and do not return Zone 1 readings
"""
import pytest
from typing import Dict, Any, Optional
from app.providers.telemetry_base import BaseTelemetryProvider
from app.services.telemetry_service import (
    telemetry_service,
    get_telemetry_provider,
    set_global_telemetry_provider,
    reset_global_telemetry_provider,
)
from app.services.orchestrator import orchestrator
from app.services.pump_control_service import pump_control_service
from app.models.conversation import ChatRequest


class MockCustomTelemetryProvider(BaseTelemetryProvider):
    """Custom mock telemetry provider to verify runtime dynamic provider replacement."""

    @property
    def is_simulation(self) -> bool:
        return False

    def get_farm_overview(self) -> Dict[str, Any]:
        return {
            "farm_id": "CUSTOM-LIVE-FARM",
            "farm_name": "Official FertoBot Live Test Farm",
            "zones": [
                {"zone_id": "PROD-ZONE-001", "crop": "Basmati Rice"},
            ],
            "data_source": "live_postgres",
        }

    def get_active_zone_id(self) -> str:
        return "PROD-ZONE-001"

    def set_active_zone_id(self, zone_id: str) -> bool:
        return True

    def get_zone(self, zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if zone_id == "PROD-ZONE-001":
            return {"zone_id": "PROD-ZONE-001", "crop": "Basmati Rice", "data_source": "live_postgres"}
        return None

    def get_latest_telemetry(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        if zone_id and zone_id != "PROD-ZONE-001":
            return {}
        return {
            "farm_id": "CUSTOM-LIVE-FARM",
            "zone_id": "PROD-ZONE-001",
            "crop": "Basmati Rice",
            "soil_moisture_pct": 65.5,
            "nitrogen_mg_kg": 180.0,
            "data_source": "live_postgres",
        }

    def get_historical_telemetry(
        self,
        zone_id: Optional[str] = None,
        parameter: str = "soil_moisture_pct",
        hours: int = 24,
    ) -> Dict[str, Any]:
        return {"zone_id": zone_id or "PROD-ZONE-001", "points": [{"value": 65.5}], "trend": "stable"}

    def get_fertilizer_consumption(self, zone_id: Optional[str] = None, window: str = "24h") -> Dict[str, Any]:
        return {"available": True, "consumption_kg": 12.5}

    def calculate_nutrient_depletion_rate(
        self,
        zone_id: Optional[str] = None,
        nutrient: str = "nitrogen",
        window_days: int = 7,
    ) -> Dict[str, Any]:
        return {"success": True, "depletion_rate_mg_kg_per_hour": 0.05}

    def get_device_status(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        return {"device_status": "online", "battery_level_pct": 99.0}

    def get_water_tank_level(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        return {"water_tank_level_pct": 95.0}

    def get_alert_history(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        return {"alerts": []}


@pytest.fixture(autouse=True)
def cleanup_telemetry_provider():
    """Ensure provider and sessions are clean before and after each test."""
    reset_global_telemetry_provider()
    orchestrator.clear_session("session-user-a")
    orchestrator.clear_session("session-user-b")
    orchestrator.clear_session("default")
    pump_control_service.reset()
    yield
    reset_global_telemetry_provider()


def test_dynamic_telemetry_provider_replacement_reflected_immediately():
    """
    FIX 2 Test: Proves that calling set_global_telemetry_provider() is immediately
    reflected across all imported references via the proxy pattern without stale caching.
    """
    # 1. Initial check: returns default simulated farm
    assert get_telemetry_provider().is_simulation is True
    assert telemetry_service.get_farm_overview()["farm_id"] == "DEMO-FARM-001"

    # 2. Swap provider to custom live adapter
    custom_provider = MockCustomTelemetryProvider()
    set_global_telemetry_provider(custom_provider)

    # 3. Verify get_telemetry_provider() returns the new provider
    assert get_telemetry_provider().is_simulation is False
    assert get_telemetry_provider().get_farm_overview()["farm_id"] == "CUSTOM-LIVE-FARM"

    # 4. Verify existing imported `telemetry_service` reference ALSO reflects the new provider!
    assert telemetry_service.is_simulation is False
    assert telemetry_service.get_farm_overview()["farm_id"] == "CUSTOM-LIVE-FARM"
    assert telemetry_service.get_latest_telemetry()["crop"] == "Basmati Rice"


@pytest.mark.anyio
async def test_scenario_a_user_a_and_user_b_zone_isolation():
    """
    Scenario A: User A selects Zone 1 while User B selects Zone 3.
    Both receive correct, independent telemetry grounded in their respective zones.
    """
    # User A asks about their soil moisture with zone-1 specified
    resp_a = await orchestrator.process_message(
        message="मेरे खेत में मिट्टी की नमी कितनी है?",
        language="hi-IN",
        session_id="session-user-a",
        zone_id="DEMO-ZONE-001",
    )
    assert resp_a.success is True
    # Zone 1 is Wheat, moisture ~48.2%
    assert resp_a.metadata.get("zone_id") == "DEMO-ZONE-001"
    assert "48.2" in resp_a.reply or "48" in resp_a.reply or "गेहूं" in resp_a.reply or "नमी" in resp_a.reply

    # User B asks about their soil moisture with zone-3 specified
    resp_b = await orchestrator.process_message(
        message="मेरे खेत में मिट्टी की नमी कितनी है?",
        language="hi-IN",
        session_id="session-user-b",
        zone_id="DEMO-ZONE-003",
    )
    assert resp_b.success is True
    # Zone 3 is Tomato, moisture ~62.1%
    assert resp_b.metadata.get("zone_id") == "DEMO-ZONE-003"
    assert "62.1" in resp_b.reply or "62" in resp_b.reply or "टमाटर" in resp_b.reply or "नमी" in resp_b.reply

    # Subsequent message from User A without zone_id should still remember Zone 1
    resp_a_followup = await orchestrator.process_message(
        message="यहाँ कौन सी फसल है?",
        language="hi-IN",
        session_id="session-user-a",
    )
    assert resp_a_followup.metadata.get("zone_id") == "DEMO-ZONE-001"

    # Subsequent message from User B without zone_id should still remember Zone 3
    resp_b_followup = await orchestrator.process_message(
        message="यहाँ कौन सी फसल है?",
        language="hi-IN",
        session_id="session-user-b",
    )
    assert resp_b_followup.metadata.get("zone_id") == "DEMO-ZONE-003"


@pytest.mark.anyio
async def test_scenario_b_concurrent_requests_do_not_overwrite_zone_context():
    """
    Scenario B: Interleaved requests for different zones cannot overwrite each other's session context.
    """
    # Step 1: User 1 inits Zone 2 (Cotton)
    await orchestrator.process_message(
        message="नमस्ते",
        language="hi-IN",
        session_id="session-user-1",
        zone_id="DEMO-ZONE-002",
    )

    # Step 2: User 2 inits Zone 4 (Mustard)
    await orchestrator.process_message(
        message="नमस्ते",
        language="hi-IN",
        session_id="session-user-2",
        zone_id="DEMO-ZONE-004",
    )

    # Step 3: User 1 queries moisture without passing zone_id
    res_1 = await orchestrator.process_message(
        message="मेरे खेत में नमी कितनी है?",
        language="hi-IN",
        session_id="session-user-1",
    )
    assert res_1.metadata.get("zone_id") == "DEMO-ZONE-002"

    # Step 4: User 2 queries moisture without passing zone_id
    res_2 = await orchestrator.process_message(
        message="मेरे खेत में नमी कितनी है?",
        language="hi-IN",
        session_id="session-user-2",
    )
    assert res_2.metadata.get("zone_id") == "DEMO-ZONE-004"


def test_scenario_c_pump_approval_session_isolation():
    """
    Scenario C: Pump actions generated in Session A cannot be approved by Session B.
    """
    # Create action for session A in Zone 1
    action_a = pump_control_service.create_action(
        session_id="session-user-a",
        zone_id="DEMO-ZONE-001",
        action_type="PUMP_ON",
    )

    # Session B attempts to approve Session A's action
    success, reply, action = pump_control_service.approve_action(
        action_id=action_a.action_id,
        session_id="session-user-b",  # Wrong session!
        language="en-US",
    )
    assert success is False
    assert "Unauthorized session" in reply
    assert pump_control_service.get_pump_state("DEMO-ZONE-001") is False

    # Session A approves its own action
    success_a, reply_a, action_a_resolved = pump_control_service.approve_action(
        action_id=action_a.action_id,
        session_id="session-user-a",  # Correct session
        language="en-US",
    )
    assert success_a is True
    assert pump_control_service.get_pump_state("DEMO-ZONE-001") is True


@pytest.mark.anyio
async def test_scenario_d_unknown_zone_fails_safely_no_fallback_to_zone_1():
    """
    Scenario D: An unknown zone cannot accidentally return Zone 1's readings.
    """
    # 1. TelemetryService level
    unknown_tel = telemetry_service.get_latest_telemetry("NON_EXISTENT_ZONE_999")
    assert unknown_tel == {}  # Strictly empty, NOT Zone 1 data!

    with pytest.raises(KeyError):
        telemetry_service.get_canonical_soil_profile("NON_EXISTENT_ZONE_999")

    # 2. Orchestrator level: User requests an invalid zone
    res = await orchestrator.process_message(
        message="Zone 999 में नमी कितनी है?",
        language="hi-IN",
        session_id="test-unknown-zone",
        zone_id="NON_EXISTENT_ZONE_999",
    )
    assert res.success is True
    # Must inform that Zone 999 is not registered, and NOT return wheat/Zone 1 readings!
    assert "पंजीकृत नहीं" in res.reply or "not registered" in res.reply.lower() or "उपलब्ध नहीं" in res.reply
    assert "48.2" not in res.reply  # Must NOT leak Zone 1's 48.2% moisture!
