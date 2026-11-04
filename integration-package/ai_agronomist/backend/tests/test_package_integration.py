"""
Standalone Package Integration & Smoke Tests
--------------------------------------------
Tests that the ai_agronomist package can be imported, mounted in a fresh
FastAPI application, injected with custom telemetry, and executed without errors.
"""
from typing import Dict, Any, Optional
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_agronomist import (
    ai_agronomist_router,
    BaseTelemetryProvider,
    set_global_telemetry_provider,
    reset_global_telemetry_provider,
    get_telemetry_provider,
    telemetry_service,
)


@pytest.fixture
def host_client():
    """Builds a minimal mock host FastAPI application."""
    app = FastAPI(title="FertoBot Host Application")
    app.include_router(ai_agronomist_router, prefix="/api")
    with TestClient(app) as client:
        yield client
    reset_global_telemetry_provider()


def test_package_exports():
    """Verify top-level package symbols are exported cleanly."""
    import ai_agronomist
    expected = [
        "ai_agronomist_router",
        "BaseTelemetryProvider",
        "set_global_telemetry_provider",
        "get_telemetry_provider",
        "reset_global_telemetry_provider",
        "telemetry_service",
        "orchestrator",
        "pump_control_service",
    ]
    for sym in expected:
        assert hasattr(ai_agronomist, sym), f"Missing exported symbol: {sym}"


def test_host_health_check(host_client):
    """Verify health endpoint responds under /api/health."""
    response = host_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_host_farm_overview(host_client):
    """Verify farm overview responds under /api/farm/overview."""
    response = host_client.get("/api/farm/overview")
    assert response.status_code == 200
    data = response.json()
    assert "zones" in data
    assert len(data["zones"]) == 4


def test_host_chat_endpoint(host_client):
    """Verify conversational greeting through orchestrator."""
    response = host_client.post(
        "/api/chat",
        json={"message": "नमस्ते", "session_id": "test-pkg-session-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "reply" in data
    assert len(data["reply"]) > 0


def test_dynamic_telemetry_provider_injection(host_client):
    """Verify custom telemetry adapter injection into host application."""
    class CustomHostTelemetry(BaseTelemetryProvider):
        @property
        def is_simulation(self) -> bool:
            return False

        def get_farm_overview(self) -> Dict[str, Any]:
            return {"farm_id": "CUSTOM-HOST-01", "zones": []}

        def get_active_zone_id(self) -> str:
            return "CUSTOM-ZONE-01"

        def set_active_zone_id(self, zone_id: str) -> bool:
            return True

        def get_zone(self, zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
            return {"zone_id": zone_id or "CUSTOM-ZONE-01", "crop": "Wheat"}

        def get_latest_telemetry(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
            return {
                "farm_id": "CUSTOM-HOST-01",
                "zone_id": zone_id or "CUSTOM-ZONE-01",
                "soil_moisture_pct": 44.4,
                "soil_temperature_c": 21.0,
                "reading_timestamp_iso": "2026-11-04T12:00:00+05:30",
            }

        def get_historical_telemetry(self, zone_id=None, parameter="soil_moisture_pct", hours=24):
            return {"points": [], "zone_id": zone_id}

        def get_fertilizer_consumption(self, zone_id=None, window="24h"):
            return {"available": False}

        def calculate_nutrient_depletion_rate(self, zone_id=None, nutrient="nitrogen", window_days=7):
            return {"success": False}

        def get_device_status(self, zone_id=None):
            return {"device_status": "online"}

        def get_water_tank_level(self, zone_id=None):
            return {"water_tank_level_pct": 80.0}

        def get_alert_history(self, zone_id=None):
            return {"alerts": []}

    set_global_telemetry_provider(CustomHostTelemetry())
    response = host_client.get("/api/farm/telemetry/latest?zone_id=CUSTOM-ZONE-01")
    assert response.status_code == 200
    data = response.json()
    assert data["soil_moisture_pct"] == 44.4
    assert data["farm_id"] == "CUSTOM-HOST-01"

    # Reset
    reset_global_telemetry_provider()
    reset_resp = host_client.get("/api/farm/telemetry/latest?zone_id=DEMO-ZONE-001")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["soil_moisture_pct"] == 48.2
