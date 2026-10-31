"""
Tests for Safe Pump Control Approval Workflow (Phase 18)
Validates:
- Intent separation: Advice vs. Activation vs. Shutdown vs. Status
- State machine: AWAITING_USER_APPROVAL -> APPROVED/REJECTED -> COMPLETED
- 5-minute expiration
- Single-use / Replay / Duplicate click protection
- Cross-session security isolation
- Emergency Stop (immediate shutdown without secondary approval)
- Strict simulated safety boundaries (actuation_permitted: False)
"""
import time
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.pump_control_service import pump_control_service
from app.services.telemetry_service import telemetry_service


@pytest.fixture(autouse=True)
def reset_service():
    """Reset pump and telemetry services before each test."""
    pump_control_service.reset()
    telemetry_service.reset_demo_dataset()
    yield
    pump_control_service.reset()


@pytest.mark.anyio
async def test_pump_activation_creates_awaiting_approval():
    """Verifies that pump activation request returns an approval card payload without actuating the pump."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/chat",
            json={
                "message": "फर्टोबॉट, मेरा पंप चालू कर दो",
                "language": "hi-IN",
                "session_id": "test-farmer-01",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "pump_activation_request"
        assert data["pending_action"] is not None
        act = data["pending_action"]
        assert act["state"] == "AWAITING_USER_APPROVAL"
        assert act["action_type"] == "PUMP_ON"
        assert act["zone_id"] == "DEMO-ZONE-001"
        assert act["simulation_mode"] is True
        assert act["actuation_permitted"] is False
        assert "हाँ, चालू करें" in data["reply"] or "पुष्टि करें" in data["reply"]

        # Crucial: The pump must NOT be running yet!
        assert pump_control_service.get_pump_state("DEMO-ZONE-001") is False


@pytest.mark.anyio
async def test_pump_advice_does_not_trigger_activation():
    """Verifies that asking for advice does NOT create a pending pump action."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Hindi advice query
        res_hi = await client.post(
            "/api/chat",
            json={
                "message": "क्या अभी पंप चालू करना चाहिए?",
                "language": "hi-IN",
                "session_id": "test-farmer-02",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        assert res_hi.status_code == 200
        data_hi = res_hi.json()
        assert data_hi["pending_action"] is None
        assert data_hi["intent"] != "pump_activation_request"

        # English advice query
        res_en = await client.post(
            "/api/chat",
            json={
                "message": "Should I turn on the pump right now?",
                "language": "en-US",
                "session_id": "test-farmer-02",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        assert res_en.status_code == 200
        data_en = res_en.json()
        assert data_en["pending_action"] is None
        assert data_en["intent"] != "pump_activation_request"


@pytest.mark.anyio
async def test_pump_explicit_approval_flow():
    """Verifies clicking 'Yes, Turn On' transitions state to COMPLETED and starts simulated pump."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Request activation
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "खेत में सिंचाई शुरू करो",
                "language": "hi-IN",
                "session_id": "test-farmer-03",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        act = chat_res.json()["pending_action"]
        action_id = act["action_id"]

        # 2. Farmer clicks 'हाँ, चालू करें'
        approve_res = await client.post(
            "/api/pump/approve",
            json={
                "action_id": action_id,
                "session_id": "test-farmer-03",
                "language": "hi-IN",
            },
        )
        assert approve_res.status_code == 200
        app_data = approve_res.json()
        assert app_data["success"] is True
        assert app_data["state"] == "COMPLETED"
        assert app_data["simulated_pump_running"] is True
        assert "पंप चालू कर दिया गया है" in app_data["reply"]

        # 3. Check pump status endpoint
        status_res = await client.get("/api/pump/status?zone_id=DEMO-ZONE-001")
        assert status_res.status_code == 200
        st = status_res.json()
        assert st["pump_running"] is True
        assert st["zone_states"]["DEMO-ZONE-001"] is True
        assert st["safety_boundary"]["simulation_mode"] is True
        assert st["safety_boundary"]["actuation_permitted"] is False


@pytest.mark.anyio
async def test_pump_explicit_rejection_flow():
    """Verifies clicking 'No, Cancel' transitions state to REJECTED and pump remains OFF."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "पानी का पंप ऑन कर दो",
                "language": "hi-IN",
                "session_id": "test-farmer-04",
                "zone_id": "DEMO-ZONE-002",
            },
        )
        action_id = chat_res.json()["pending_action"]["action_id"]

        # Farmer clicks 'नहीं, रद्द करें'
        reject_res = await client.post(
            "/api/pump/reject",
            json={
                "action_id": action_id,
                "session_id": "test-farmer-04",
                "language": "hi-IN",
            },
        )
        assert reject_res.status_code == 200
        rej_data = reject_res.json()
        assert rej_data["success"] is True
        assert rej_data["state"] == "REJECTED"
        assert rej_data["simulated_pump_running"] is False
        assert "रद्द कर दिया गया है" in rej_data["reply"]

        # Confirm pump remains OFF
        assert pump_control_service.get_pump_state("DEMO-ZONE-002") is False


@pytest.mark.anyio
async def test_emergency_shutdown_without_second_approval():
    """Verifies that saying 'पंप बंद कर दो' stops pump immediately without requiring secondary confirmation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Pre-set pump to running
        pump_control_service._zone_pump_states["DEMO-ZONE-001"] = True
        assert pump_control_service.get_pump_state("DEMO-ZONE-001") is True

        # Stop command
        stop_res = await client.post(
            "/api/chat",
            json={
                "message": "पंप बंद कर दो",
                "language": "hi-IN",
                "session_id": "test-farmer-05",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        assert stop_res.status_code == 200
        data = stop_res.json()
        assert data["intent"] == "pump_shutdown"
        assert data["pending_action"] is None
        assert "तुरंत बंद कर दिया गया है" in data["reply"]
        assert pump_control_service.get_pump_state("DEMO-ZONE-001") is False


@pytest.mark.anyio
async def test_replay_protection_duplicate_clicks():
    """Verifies that approving or rejecting twice is rejected by replay protection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "turn on pump",
                "language": "en-US",
                "session_id": "test-farmer-06",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        action_id = chat_res.json()["pending_action"]["action_id"]

        # 1st approval -> OK
        app1 = await client.post(
            "/api/pump/approve",
            json={"action_id": action_id, "session_id": "test-farmer-06", "language": "en-US"},
        )
        assert app1.status_code == 200

        # 2nd approval (duplicate click) -> HTTP 400
        app2 = await client.post(
            "/api/pump/approve",
            json={"action_id": action_id, "session_id": "test-farmer-06", "language": "en-US"},
        )
        assert app2.status_code == 400
        assert "already been approved" in app2.json()["detail"].lower()


@pytest.mark.anyio
async def test_cross_session_security_isolation():
    """Verifies that User B cannot approve User A's pending action."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "पंप चालू कर दो",
                "language": "hi-IN",
                "session_id": "farmer-user-A",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        action_id = chat_res.json()["pending_action"]["action_id"]

        # Unauthorized session attempts approval
        hijack_res = await client.post(
            "/api/pump/approve",
            json={
                "action_id": action_id,
                "session_id": "rogue-user-B",
                "language": "hi-IN",
            },
        )
        assert hijack_res.status_code == 400
        assert "अनधिकृत सत्र" in hijack_res.json()["detail"]
        assert pump_control_service.get_pump_state("DEMO-ZONE-001") is False


@pytest.mark.anyio
async def test_action_expiration():
    """Verifies that actions older than 5 minutes expire and cannot be approved."""
    action = pump_control_service.create_action(
        session_id="exp-session",
        zone_id="DEMO-ZONE-001",
        action_type="PUMP_ON",
    )
    # Fast-forward time past 5 minutes
    action.expires_at = time.time() - 10.0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        exp_res = await client.post(
            "/api/pump/approve",
            json={
                "action_id": action.action_id,
                "session_id": "exp-session",
                "language": "hi-IN",
            },
        )
        assert exp_res.status_code == 400
        assert "समय सीमा" in exp_res.json()["detail"] or "expired" in exp_res.json()["detail"].lower()
        assert action.state == "EXPIRED"
        assert pump_control_service.get_pump_state("DEMO-ZONE-001") is False


@pytest.mark.anyio
async def test_pump_status_query():
    """Verifies queries about pump status report simulated state correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initially OFF
        res1 = await client.post(
            "/api/chat",
            json={
                "message": "पंप चालू है या बंद?",
                "language": "hi-IN",
                "session_id": "status-sess",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        assert res1.status_code == 200
        assert res1.json()["intent"] == "pump_status"
        assert "बंद" in res1.json()["reply"]

        # Turn ON via service
        pump_control_service._zone_pump_states["DEMO-ZONE-001"] = True

        res2 = await client.post(
            "/api/chat",
            json={
                "message": "is pump running?",
                "language": "en-US",
                "session_id": "status-sess",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        assert res2.status_code == 200
        assert res2.json()["intent"] == "pump_status"
        assert "RUNNING" in res2.json()["reply"]


@pytest.mark.anyio
async def test_strict_no_physical_actuation_boundary():
    """
    Phase 21 Audit: Proves conclusively that no physical actuation occurs.
    Validates:
    - simulation_mode is strictly True across all states
    - actuation_permitted is strictly False
    - hardware_isolated is strictly True
    - Timed execution cycle is 100% simulated software state, never physical relay
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Inspect initial safety boundary via status endpoint
        st_res = await client.get("/api/pump/status")
        assert st_res.status_code == 200
        boundary = st_res.json()["safety_boundary"]
        assert boundary["simulation_mode"] is True
        assert boundary["actuation_permitted"] is False
        assert boundary["hardware_isolated"] is True

        # 2. Create and approve an action
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "start irrigation pump",
                "language": "en-US",
                "session_id": "test-safety-sess",
                "zone_id": "DEMO-ZONE-001",
            },
        )
        action_payload = chat_res.json()["pending_action"]
        assert action_payload["simulation_mode"] is True
        assert action_payload["actuation_permitted"] is False

        # 3. Approve action
        app_res = await client.post(
            "/api/pump/approve",
            json={
                "action_id": action_payload["action_id"],
                "session_id": "test-safety-sess",
                "language": "en-US",
            },
        )
        assert app_res.status_code == 200
        approved_data = app_res.json()
        assert approved_data["success"] is True
        assert approved_data["simulated_pump_running"] is True

        # 4. Audit log verification: all events are simulated software events
        for entry in pump_control_service._audit_log:
            assert entry["action_id"] == action_payload["action_id"]
            assert entry["event"] in ["ACTION_REQUESTED", "APPROVED_AND_COMPLETED"]
            # No hardware command or pin toggling field exists
            assert "gpio_state" not in entry
            assert "relay_command" not in entry

        # 5. Emergency stop immediately disarms without hardware side-effects
        stop_res = await client.post("/api/pump/emergency-stop", json={"session_id": "test-safety-sess"})
        assert stop_res.status_code == 200
        assert pump_control_service.get_pump_state("DEMO-ZONE-001") is False

