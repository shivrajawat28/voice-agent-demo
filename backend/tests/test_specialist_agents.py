"""
Unit Tests for Specialist Agents (Crop Symptom, Irrigation Advisory, Weather Context)
"""
import pytest
from app.agents.base import AgentContext
from app.agents.crop_symptom_agent import CropSymptomAgent
from app.agents.irrigation_advisory_agent import IrrigationAdvisoryAgent
from app.agents.weather_context_agent import WeatherContextAgent
from app.tools.crop_knowledge_tool import CropKnowledgeTool
from app.tools.weather_tool import WeatherTool
from app.tools.telemetry_tool import TelemetryTool


@pytest.fixture
def test_tools():
    return {
        "crop_knowledge": CropKnowledgeTool(),
        "weather_context": WeatherTool(timeout_seconds=1.0),
        "farm_telemetry": TelemetryTool(),
    }


@pytest.mark.anyio
async def test_crop_symptom_agent(test_tools):
    agent = CropSymptomAgent()
    assert agent.agent_id == "crop_symptom"
    assert "crop_knowledge" in agent.permitted_tools

    ctx = AgentContext(query="Why are my leaves turning yellow?", language="en-US")
    res = await agent.execute(ctx, test_tools)

    assert res.status == "completed"
    assert "Nitrogen" in res.summary or "waterlogging" in res.summary
    assert len(res.evidence) > 0
    # Confirms limitation disclosure when crop species is missing
    assert any("Crop species not specified" in lim for lim in res.limitations)


@pytest.mark.anyio
async def test_crop_symptom_agent_hindi(test_tools):
    agent = CropSymptomAgent()
    ctx = AgentContext(query="गेहूं की पत्तियां पीली पड़ रही हैं", language="hi-IN")
    res = await agent.execute(ctx, test_tools)

    assert res.status == "completed"
    assert "नाइट्रोजन" in res.summary or "पीला" in res.summary
    assert res.data["detected_crop"] == "wheat"


@pytest.mark.anyio
async def test_irrigation_advisory_agent(test_tools):
    agent = IrrigationAdvisoryAgent()
    assert agent.agent_id == "irrigation_advisory"

    ctx = AgentContext(query="Should I water the field today?", language="en-US")
    res = await agent.execute(ctx, test_tools)

    assert res.status == "completed"
    assert res.data["soil_moisture_pct"] == 48.2
    # Because moisture is 48.2% and rain prob varies, it should advise stable, optimal, or postponed
    assert "postponed" in res.summary.lower() or "optimal" in res.summary.lower() or "stable" in res.summary.lower()
    assert any("locked" in lim for lim in res.limitations)


@pytest.mark.anyio
async def test_weather_context_agent(test_tools):
    agent = WeatherContextAgent()
    assert agent.agent_id == "weather_context"

    ctx = AgentContext(query="What is the forecast?", language="en-US")
    res = await agent.execute(ctx, test_tools)

    assert res.status == "completed"
    assert "temperature_c" in res.data
    assert len(res.evidence) >= 4
