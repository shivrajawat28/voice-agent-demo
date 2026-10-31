"""
Unit Tests for Read-Only Agricultural Tools
"""
import pytest
from app.tools.crop_knowledge_tool import CropKnowledgeTool
from app.tools.weather_tool import WeatherTool
from app.tools.telemetry_tool import TelemetryTool


@pytest.mark.anyio
async def test_crop_knowledge_tool():
    tool = CropKnowledgeTool()
    assert tool.name == "crop_knowledge"

    # Test wheat query
    data_wheat = await tool.execute(crop="wheat", symptom="yellow leaves")
    assert data_wheat["has_specific_crop_match"] is True
    assert data_wheat["thresholds"]["soil_moisture_opt_pct"] == 55.0
    assert data_wheat["diagnostic_data"] is not None
    assert len(data_wheat["diagnostic_data"]["primary_hypotheses"]) >= 2

    # Test unknown crop fallback
    data_unknown = await tool.execute(crop="quinoa", symptom="wilting")
    assert data_unknown["has_specific_crop_match"] is False
    assert data_unknown["thresholds"]["soil_moisture_opt_pct"] == 50.0
    assert data_unknown["diagnostic_data"] is not None


@pytest.mark.anyio
async def test_weather_tool():
    tool = WeatherTool(timeout_seconds=1.5)
    assert tool.name == "weather_context"

    data = await tool.execute()
    assert "temperature_c" in data
    assert "relative_humidity_pct" in data
    assert "rain_probability_24h_pct" in data
    assert "source" in data
    assert data["rain_probability_24h_pct"] >= 0


@pytest.mark.anyio
async def test_telemetry_tool_read_only():
    tool = TelemetryTool()
    assert tool.name == "farm_telemetry"

    data = await tool.execute()
    assert data["actuation_permitted"] is False
    assert data["soil_moisture_pct"] == 48.2
    assert data["soil_temperature_c"] == 24.5
    assert data["water_tank_level_pct"] == 82.0
    assert data["sensors_online_count"] == 3
