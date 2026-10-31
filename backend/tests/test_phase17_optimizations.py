"""
Tests for Phase 17 Optimizations:
1. Response Latency & Fast Deterministic Planning (<5ms)
2. Conversational Memory & Greeting Policy (Greeting once on Turn 1; Never on Turns 2+)
3. Concise Agronomic Answers
4. Context-Aware Warning Logic (No false 'Grower Context Needed' alerts when crop/zone is known)
5. Session Reset via POST /api/chat/clear
"""
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.services.orchestrator import LLMOrchestrator
from app.providers.mock_llm import MockLLMProvider

client = TestClient(app)


@pytest.mark.anyio
async def test_fast_planning_latency():
    """Verify deterministic agronomist dispatch runs in under 5ms."""
    orch = LLMOrchestrator(MockLLMProvider(), fast_planning=True)
    t0 = time.perf_counter()
    res = await orch.process_query("क्या अभी पानी देना चाहिए?", language="hi-IN")
    duration_ms = (time.perf_counter() - t0) * 1000

    plan_step = next(s for s in res.execution_trace if s.action == "plan_execution")
    assert plan_step.status == "completed"
    assert plan_step.duration_ms < 5.0  # Must be sub-5ms


@pytest.mark.anyio
async def test_greeting_only_once_per_session():
    """Verify greeting occurs on Turn 1, but is suppressed on Turns 2-5 of the same session."""
    session_id = f"test-session-greeting-{time.time()}"
    orch = LLMOrchestrator(MockLLMProvider(), fast_planning=True)

    # Turn 1: Grower greets and asks for moisture
    t1 = await orch.process_query("नमस्ते फर्टोबॉट, मेरी मिट्टी में नमी कितनी है?", language="hi-IN", session_id=session_id)
    assert t1.success is True
    # Turn 1 may contain greeting because grower greeted
    assert "नमस्ते" in t1.reply or "फर्टोबॉट" in t1.reply

    # Turn 2: Follow-up question about watering
    t2 = await orch.process_query("क्या अभी पानी देना चाहिए?", language="hi-IN", session_id=session_id)
    assert t2.success is True
    # Turn 2 MUST NOT start with greeting or contain repeated greeting
    assert not t2.reply.startswith("नमस्ते")
    assert not t2.reply.startswith("नमस्कार")
    assert "किसान भाई" not in t2.reply[:30]

    # Turn 3: Follow-up question about rain
    t3 = await orch.process_query("अगर अगले दो दिन बारिश हो तो?", language="hi-IN", session_id=session_id)
    assert t3.success is True
    assert not t3.reply.startswith("नमस्ते")
    assert "किसान भाई" not in t3.reply[:30]

    # Turn 4: Sensor pH query
    t4 = await orch.process_query("मेरी मिट्टी का पीएच कितना है?", language="hi-IN", session_id=session_id)
    assert t4.success is True
    assert not t4.reply.startswith("नमस्ते")
    assert "किसान भाई" not in t4.reply[:30]

    # Turn 5: Improvement query
    t5 = await orch.process_query("इसे बेहतर करने के लिए क्या करना चाहिए?", language="hi-IN", session_id=session_id)
    assert t5.success is True
    assert not t5.reply.startswith("नमस्ते")
    assert "किसान भाई" not in t5.reply[:30]


@pytest.mark.anyio
async def test_pure_greeting_subsequent_turns():
    """Verify pure greeting on Turn 2+ responds concisely without re-introduction."""
    session_id = f"test-session-pure-greet-{time.time()}"
    orch = LLMOrchestrator(MockLLMProvider(), fast_planning=True)

    # Turn 1: Initial pure greeting
    r1 = await orch.process_query("नमस्ते", language="hi-IN", session_id=session_id)
    assert "नमस्ते! मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ" in r1.reply

    # Turn 2: Grower says 'नमस्ते' again
    r2 = await orch.process_query("नमस्ते", language="hi-IN", session_id=session_id)
    assert "हाँ जी, बताइए" in r2.reply
    # Must NOT repeat full introduction
    assert "मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ" not in r2.reply


@pytest.mark.anyio
async def test_context_aware_warning_not_triggered_when_crop_known():
    """Verify that when the zone crop is Wheat and telemetry is present, needs_clarification is False."""
    session_id = f"test-session-context-{time.time()}"
    orch = LLMOrchestrator(MockLLMProvider(), fast_planning=True)

    res = await orch.process_query("क्या अभी पानी देना चाहिए?", language="hi-IN", session_id=session_id, zone_id="DEMO-ZONE-001")
    assert res.success is True
    assert res.needs_clarification is False
    assert res.clarification_prompt is None


def test_clear_session_endpoint():
    """Verify POST /api/chat/clear resets greeting memory and turn counter."""
    session_id = "test-clear-endpoint-session"

    # Turn 1: pure greeting
    r1 = client.post("/api/chat", json={"message": "नमस्ते", "session_id": session_id, "language": "hi-IN"}).json()
    assert "नमस्ते! मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ" in r1["reply"]

    # Turn 2: pure greeting
    r2 = client.post("/api/chat", json={"message": "नमस्ते", "session_id": session_id, "language": "hi-IN"}).json()
    assert "हाँ जी, बताइए" in r2["reply"]

    # Clear session
    res = client.post("/api/chat/clear", json={"session_id": session_id})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Turn 3 (treated as fresh Turn 1 after clear)
    r3 = client.post("/api/chat", json={"message": "नमस्ते", "session_id": session_id, "language": "hi-IN"}).json()
    assert "नमस्ते! मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ" in r3["reply"]
