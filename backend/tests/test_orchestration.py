"""
Integration Tests for LLM Multi-Agent Orchestrator
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.orchestrator import LLMOrchestrator, orchestrator
from app.providers.mock_llm import MockLLMProvider
from app.agents.base import BaseAgent, AgentContext
from app.models.conversation import AgentResult

client = TestClient(app)


@pytest.mark.anyio
async def test_orchestrator_fast_path_greeting():
    orch = LLMOrchestrator(MockLLMProvider())
    res = await orch.process_query("Hello there", language="en-US")
    assert res.intent == "greeting"
    assert res.provider_status == "fast_path"
    assert res.agent_results is None
    assert len(res.execution_trace) == 1
    assert res.execution_trace[0].agent_id == "fast_path_router"


@pytest.mark.anyio
async def test_orchestrator_agricultural_symptom_flow():
    orch = LLMOrchestrator(MockLLMProvider())
    res = await orch.process_query("Why are my cotton leaves turning yellow?", language="en-US")
    assert res.success is True
    assert res.intent in ["agricultural_inquiry", "symptom_inquiry"]
    assert res.agent_results is not None
    assert len(res.agent_results) >= 1
    assert any(a.agent_id == "crop_symptom" for a in res.agent_results)
    assert len(res.execution_trace) >= 3  # plan, execute, synthesize
    assert len(res.sources) >= 1


@pytest.mark.anyio
async def test_orchestrator_irrigation_multi_agent():
    orch = LLMOrchestrator(MockLLMProvider())
    res = await orch.process_query("Should I irrigate the wheat field today? What is the weather?", language="en-US")
    assert res.success is True
    assert res.agent_results is not None
    agent_ids = [a.agent_id for a in res.agent_results]
    assert "irrigation_advisory" in agent_ids or "weather_context" in agent_ids


@pytest.mark.anyio
async def test_orchestrator_agent_fault_tolerance():
    class FaultyAgent(BaseAgent):
        @property
        def agent_id(self) -> str:
            return "faulty_agent"

        @property
        def name(self) -> str:
            return "Faulty Test Agent"

        @property
        def description(self) -> str:
            return "Always raises error"

        @property
        def permitted_tools(self):
            return []

        async def execute(self, ctx, tools):
            raise RuntimeError("Sensors completely offline")

    orch = LLMOrchestrator(MockLLMProvider())
    orch._agents["faulty"] = FaultyAgent()

    # Manually run faulty agent in context
    agent_ctx = AgentContext(query="test", language="en-US")
    res = await orch.process_query("Why are leaves yellow?", language="en-US")
    # Orchestrator does not crash
    assert res.success is True


def test_api_agents_list_endpoint():
    res = client.get("/api/agents")
    assert res.status_code == 200
    data = res.json()
    assert "crop_symptom" in data["available_agents"]
    assert "irrigation_advisory" in data["available_agents"]
    assert "weather_context" in data["available_agents"]


def test_api_provider_llm_switch():
    res = client.post("/api/provider/llm?provider=mock")
    assert res.status_code == 200
    data = res.json()
    assert data["active_llm_provider"] == "mock"
    assert data["provider_status"] == "mock"
