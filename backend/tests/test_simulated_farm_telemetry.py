"""
Automated Test Suite for Phase 10: Simulated Farm Telemetry & Grounded Intelligence
Verifies:
- 3 distinct zones with non-duplicated realistic readings
- Parameter units (%, mg/kg, °C, dS/m) and timestamps
- Strict simulated provenance (data_source="simulated", is_simulated=True)
- Zero hardware actuation (actuation_permitted=False)
- All 5 telemetry tools (Latest, Historical, DeviceStatus, WaterLevel, AlertHistory)
- DeviceHealthAgent functionality
- Missing sensor handling (Zone 3 Nitrogen uncalibrated)
- Reset and active zone switching
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.services.telemetry_service import telemetry_service
from app.tools.telemetry_tool import (
    LatestTelemetryTool,
    HistoricalTelemetryTool,
    DeviceStatusTool,
    WaterLevelTool,
    AlertHistoryTool,
)
from app.agents.device_health_agent import DeviceHealthAgent
from app.agents.base import AgentContext

client = TestClient(app)


def test_three_distinct_zones_have_unique_readings():
    overview = telemetry_service.get_farm_overview()
    zones = {z["zone_id"]: z for z in overview["zones"]}

    assert "DEMO-ZONE-001" in zones
    assert "DEMO-ZONE-002" in zones
    assert "DEMO-ZONE-003" in zones
    assert "DEMO-ZONE-004" in zones

    z1 = zones["DEMO-ZONE-001"]
    z2 = zones["DEMO-ZONE-002"]
    z3 = zones["DEMO-ZONE-003"]
    z4 = zones["DEMO-ZONE-004"]

    # Verify completely different moisture values
    assert z1["soil_moisture_pct"] == 48.2
    assert z2["soil_moisture_pct"] == 28.5
    assert z3["soil_moisture_pct"] == 64.5
    assert z4["soil_moisture_pct"] == 38.5

    # Verify distinct crops
    assert z1["crop"] == "wheat"
    assert z2["crop"] == "cotton"
    assert z3["crop"] == "tomato"
    assert z4["crop"] == "mustard"

    # Verify different NPK values
    assert z1["nitrogen_mg_kg"] == 38.0
    assert z2["nitrogen_mg_kg"] == 62.0
    assert z3["nitrogen_mg_kg"] is None  # Missing sensor test requirement

    # Verify distinct batteries and devices
    assert z1["device_id"] == "DEMO-DEVICE-001"
    assert z2["device_id"] == "DEMO-DEVICE-002"
    assert z3["device_id"] == "DEMO-DEVICE-003"
    assert z3["battery_level_pct"] == 16.0  # Low battery alert condition

    # Strict simulated provenance across all zones
    for zid, z in zones.items():
        assert z["data_source"] == "simulated"
        assert z["is_simulated"] is True
        assert z["actuation_permitted"] is False


@pytest.mark.anyio
async def test_latest_telemetry_tool():
    tool = LatestTelemetryTool()
    assert tool.name == "latest_telemetry"

    # Test Zone 1
    res1 = await tool.execute(zone_id="DEMO-ZONE-001")
    assert res1["status"] == "success"
    assert res1["zone_id"] == "DEMO-ZONE-001"
    assert res1["soil_moisture_pct"] == 48.2
    assert res1["units"]["nitrogen_mg_kg"] == "mg/kg"
    assert res1["units"]["electrical_conductivity_ds_m"] == "dS/m"
    assert res1["data_source"] == "simulated"
    assert res1["is_simulated"] is True
    assert res1["actuation_permitted"] is False

    # Test Zone 2 (Cotton, dry)
    res2 = await tool.execute(zone_id="DEMO-ZONE-002")
    assert res2["zone_id"] == "DEMO-ZONE-002"
    assert res2["soil_moisture_pct"] == 28.5
    assert res2["crop"] == "cotton"

    # Test Zone 3 (Missing nitrogen)
    res3 = await tool.execute(zone_id="DEMO-ZONE-003")
    assert res3["zone_id"] == "DEMO-ZONE-003"
    assert res3["nitrogen_mg_kg"] is None
    assert "nitrogen_mg_kg" in res3["missing_fields"]


@pytest.mark.anyio
async def test_historical_telemetry_tool_trend():
    tool = HistoricalTelemetryTool()
    assert tool.name == "historical_telemetry"

    # 7-day trend for Zone 2 (drying out from 38.2 to 28.5%)
    trend_z2 = await tool.execute(zone_id="DEMO-ZONE-002", parameter="soil_moisture_pct", time_range="7d")
    assert trend_z2["status"] == "success"
    assert trend_z2["time_range"] == "7d"
    assert trend_z2["trend_direction"] == "decreasing"
    assert len(trend_z2["points"]) == 7
    assert "Declined" in trend_z2["trend_summary"]
    assert trend_z2["is_simulated"] is True

    # 24-hour trend for Zone 1
    trend_z1_24h = await tool.execute(zone_id="DEMO-ZONE-001", parameter="soil_moisture_pct", time_range="24h")
    assert len(trend_z1_24h["points"]) == 24
    assert trend_z1_24h["time_range"] == "24h"


@pytest.mark.anyio
async def test_device_status_tool():
    tool = DeviceStatusTool()
    assert tool.name == "device_status"

    dev1 = await tool.execute(zone_id="DEMO-ZONE-001")
    assert dev1["device_id"] == "DEMO-DEVICE-001"
    assert dev1["status"] == "online"
    assert dev1["battery_level_pct"] >= 90.0
    assert dev1["is_simulated"] is True

    dev3 = await tool.execute(zone_id="DEMO-ZONE-003")
    assert dev3["device_id"] == "DEMO-DEVICE-003"
    assert dev3["battery_level_pct"] == 16.0
    assert dev3["status"] == "warning"


@pytest.mark.anyio
async def test_water_level_tool():
    tool = WaterLevelTool()
    assert tool.name == "water_level"

    w1 = await tool.execute(zone_id="DEMO-ZONE-001")
    assert w1["water_tank_level_pct"] == 82.0
    assert w1["status"] == "adequate"
    assert w1["unit"] == "%"
    assert w1["is_simulated"] is True


@pytest.mark.anyio
async def test_alert_history_tool():
    tool = AlertHistoryTool()
    assert tool.name == "alert_history"

    all_alerts = await tool.execute()
    assert all_alerts["total_alerts"] >= 3
    assert all_alerts["is_simulated"] is True

    # Zone 3 specific alerts
    z3_alerts = await tool.execute(zone_id="DEMO-ZONE-003")
    assert any("Battery" in a["title"] for a in z3_alerts["alerts"])


@pytest.mark.anyio
async def test_device_health_agent():
    agent = DeviceHealthAgent()
    assert agent.agent_id == "device_health"
    assert "device_status" in agent.permitted_tools
    assert "water_level" in agent.permitted_tools

    tools = {
        "device_status": DeviceStatusTool(),
        "water_level": WaterLevelTool(),
        "alert_history": AlertHistoryTool(),
    }

    # Query device status
    ctx1 = AgentContext(query="Is my device online and what is the battery?", language="en-US", zone_id="DEMO-ZONE-001")
    res1 = await agent.execute(ctx1, tools)
    assert res1.status == "completed"
    assert "ONLINE" in res1.summary
    assert "92.0%" in res1.summary
    assert res1.data["is_simulated"] is True

    # Query water tank level
    ctx2 = AgentContext(query="मेरे water tank mein kitna paani hai?", language="hi-IN", zone_id="DEMO-ZONE-001")
    res2 = await agent.execute(ctx2, tools)
    assert res2.status == "completed"
    assert "82.0%" in res2.summary


def test_farm_telemetry_rest_endpoints():
    # 1. Overview
    res = client.get("/api/farm/overview")
    assert res.status_code == 200
    ov = res.json()
    assert ov["farm_id"] == "DEMO-FARM-001"
    assert len(ov["zones"]) == 4
    assert ov["is_simulated"] is True

    # 2. Zones list
    res_z = client.get("/api/farm/zones")
    assert res_z.status_code == 200
    zd = res_z.json()
    assert zd["active_zone_id"] in ["DEMO-ZONE-001", "DEMO-ZONE-002", "DEMO-ZONE-003", "DEMO-ZONE-004"]

    # 3. Latest telemetry
    res_lat = client.get("/api/farm/telemetry/latest?zone_id=DEMO-ZONE-002")
    assert res_lat.status_code == 200
    assert res_lat.json()["soil_moisture_pct"] == 28.5

    # 4. History
    res_h = client.get("/api/farm/telemetry/history?zone_id=DEMO-ZONE-002&parameter=soil_moisture_pct&time_range=7d")
    assert res_h.status_code == 200
    assert res_h.json()["trend_direction"] == "decreasing"

    # 5. Alerts
    res_a = client.get("/api/farm/alerts")
    assert res_a.status_code == 200
    assert len(res_a.json()["alerts"]) >= 3

    # 6. Set Active Zone
    res_set = client.post("/api/farm/active-zone", json={"zone_id": "DEMO-ZONE-002"})
    assert res_set.status_code == 200
    assert res_set.json()["active_zone_id"] == "DEMO-ZONE-002"

    # 7. Reset
    res_rst = client.post("/api/farm/reset")
    assert res_rst.status_code == 200
    assert res_rst.json()["active_zone_id"] == "DEMO-ZONE-001"
