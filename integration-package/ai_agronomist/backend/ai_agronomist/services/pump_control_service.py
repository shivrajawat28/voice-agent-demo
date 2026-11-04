"""
Safe Pump Control Service with Farmer Approval Workflow
Governs state transitions, 5-minute action expiration, duplicate click / replay protection,
and strict simulated hardware safety boundaries.
"""
import time
import uuid
from typing import Dict, Any, Optional, Tuple, List
from ai_agronomist.models.conversation import PumpActionPayload
from ai_agronomist.services.telemetry_service import telemetry_service


class PumpControlService:
    def __init__(self):
        # Simulated pump states per zone (False = OFF, True = ON)
        self._zone_pump_states: Dict[str, bool] = {
            "DEMO-ZONE-001": False,
            "DEMO-ZONE-002": False,
            "DEMO-ZONE-003": False,
            "DEMO-ZONE-004": False,
        }
        # In-memory store of actions awaiting approval or resolved
        self._actions: Dict[str, PumpActionPayload] = {}
        # Action audit log
        self._audit_log: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Reset all pump states to OFF and clear pending actions."""
        for z in self._zone_pump_states:
            self._zone_pump_states[z] = False
        self._actions.clear()
        self._audit_log.clear()

    def get_pump_state(self, zone_id: str) -> bool:
        """Returns True if the simulated pump for zone_id is ON, False otherwise."""
        return self._zone_pump_states.get(zone_id, False)

    def get_all_pump_states(self) -> Dict[str, bool]:
        """Returns dictionary mapping all zone IDs to their simulated pump state."""
        return dict(self._zone_pump_states)

    def get_action(self, action_id: str) -> Optional[PumpActionPayload]:
        """Retrieve an action payload by its ID."""
        return self._actions.get(action_id)

    def create_action(
        self,
        session_id: str,
        zone_id: Optional[str] = None,
        action_type: str = "PUMP_ON",
        message: Optional[str] = None,
    ) -> PumpActionPayload:
        """
        Creates a new pump control action in AWAITING_USER_APPROVAL state.
        Expires in 300 seconds (5 minutes).
        """
        resolved_zone = zone_id or telemetry_service.get_active_zone_id()
        target_zone_meta = telemetry_service.get_zone(resolved_zone) or {
            "zone_id": resolved_zone,
            "crop": "Crop",
            "device_id": "DEMO-DEVICE-001",
        }
        probe_id = target_zone_meta.get("device_id", "DEMO-DEVICE-001")
        now = time.time()
        action_id = f"act-{uuid.uuid4().hex[:8]}"

        action = PumpActionPayload(
            action_id=action_id,
            session_id=session_id,
            zone_id=resolved_zone,
            probe_id=probe_id,
            action_type=action_type,
            state="AWAITING_USER_APPROVAL",
            created_at=now,
            expires_at=now + 300.0,  # 5 minutes expiry
            simulation_mode=True,
            actuation_permitted=False,
            message=message or f"Request to turn {action_type} for {resolved_zone}",
        )
        self._actions[action_id] = action

        self._audit_log.append({
            "action_id": action_id,
            "event": "ACTION_REQUESTED",
            "session_id": session_id,
            "zone_id": resolved_zone,
            "action_type": action_type,
            "timestamp": now,
        })
        return action

    def approve_action(
        self,
        action_id: str,
        session_id: str,
        language: str = "hi-IN",
    ) -> Tuple[bool, str, Optional[PumpActionPayload]]:
        """
        Processes explicit farmer approval ('हाँ, चालू करें').
        Validates:
        1. Action exists
        2. Session matches (authorization / cross-session security)
        3. Expiration window (5 minutes)
        4. Replay / duplicate click protection (state must be AWAITING_USER_APPROVAL)
        Transitions: AWAITING_USER_APPROVAL -> APPROVED -> EXECUTING -> COMPLETED
        Updates simulated pump state.
        """
        now = time.time()
        action = self._actions.get(action_id)
        is_hindi = language.lower().startswith("hi")

        if not action:
            msg = "कार्रवाई नहीं मिली या पहले ही प्रोसेस हो चुकी है।" if is_hindi else "Action not found or already processed."
            return False, msg, None

        if action.session_id != session_id:
            msg = "अनधिकृत सत्र। यह कार्रवाई इस सत्र से संबंधित नहीं है।" if is_hindi else "Unauthorized session for this action."
            return False, msg, action

        if now > action.expires_at:
            action.state = "EXPIRED"
            self._audit_log.append({
                "action_id": action_id,
                "event": "EXPIRED",
                "timestamp": now,
            })
            msg = "कार्रवाई की 5 मिनट की समय सीमा समाप्त हो चुकी है। कृपया पुनः अनुरोध करें।" if is_hindi else "Action expired after 5 minutes. Please request again."
            return False, msg, action

        if action.state in ["APPROVED", "EXECUTING", "COMPLETED"]:
            msg = "यह कार्रवाई पहले ही स्वीकृत और पूरी हो चुकी है।" if is_hindi else "Action has already been approved and executed."
            return False, msg, action

        if action.state == "REJECTED":
            msg = "यह कार्रवाई पहले ही रद्द की जा चुकी है।" if is_hindi else "This action was previously rejected."
            return False, msg, action

        # State transition: APPROVED -> EXECUTING -> COMPLETED
        action.state = "COMPLETED"
        zone_id = action.zone_id
        target_state = (action.action_type == "PUMP_ON")
        self._zone_pump_states[zone_id] = target_state

        self._audit_log.append({
            "action_id": action_id,
            "event": "APPROVED_AND_COMPLETED",
            "session_id": session_id,
            "zone_id": zone_id,
            "pump_state": target_state,
            "timestamp": now,
        })

        zone_meta = telemetry_service.get_zone(zone_id) or {"crop": "फसल", "zone_name": zone_id}
        crop_name = zone_meta.get("crop", "फसल")

        if is_hindi:
            if target_state:
                reply = f"अनुमोदन प्राप्त हुआ। {zone_id} ({crop_name}) के लिए पानी का पंप चालू कर दिया गया है। (सिम्युलेटेड मोड - वास्तविक रिले सुरक्षित है।)"
            else:
                reply = f"अनुमोदन प्राप्त हुआ। {zone_id} ({crop_name}) के लिए पानी का पंप बंद कर दिया गया है। (सिम्युलेटेड मोड)"
        else:
            if target_state:
                reply = f"Approval confirmed. Water pump for {zone_id} ({crop_name}) is now running. (Simulated mode - hardware relay safe.)"
            else:
                reply = f"Approval confirmed. Water pump for {zone_id} ({crop_name}) has been turned off. (Simulated mode)"

        return True, reply, action

    def reject_action(
        self,
        action_id: str,
        session_id: str,
        language: str = "hi-IN",
    ) -> Tuple[bool, str, Optional[PumpActionPayload]]:
        """
        Processes explicit farmer cancellation ('नहीं, रद्द करें').
        Transitions to REJECTED.
        """
        now = time.time()
        action = self._actions.get(action_id)
        is_hindi = language.lower().startswith("hi")

        if not action:
            msg = "कार्रवाई नहीं मिली।" if is_hindi else "Action not found."
            return False, msg, None

        if action.session_id != session_id:
            msg = "अनधिकृत सत्र।" if is_hindi else "Unauthorized session."
            return False, msg, action

        if action.state in ["COMPLETED", "APPROVED"]:
            msg = "कार्रवाई पहले ही पूरी हो चुकी है, इसे रद्द नहीं किया जा सकता।" if is_hindi else "Action already executed; cannot cancel."
            return False, msg, action

        action.state = "REJECTED"
        self._audit_log.append({
            "action_id": action_id,
            "event": "REJECTED",
            "session_id": session_id,
            "timestamp": now,
        })

        msg = "पंप चालू करने का अनुरोध रद्द कर दिया गया है। पंप बंद रहेगा।" if is_hindi else "Pump activation request has been cancelled. Pump remains off."
        return True, msg, action

    def emergency_stop(
        self,
        session_id: str,
        zone_id: Optional[str] = None,
        language: str = "hi-IN",
    ) -> Tuple[bool, str]:
        """
        Immediate shutdown / Emergency Stop.
        Immediately turns OFF pump for the specified zone (or all zones if unspecified),
        WITHOUT requiring a second approval.
        Also cancels any pending PUMP_ON actions for that zone.
        """
        now = time.time()
        resolved_zone = zone_id or telemetry_service.get_active_zone_id()
        is_hindi = language.lower().startswith("hi")

        # Turn OFF pump
        self._zone_pump_states[resolved_zone] = False

        # Cancel any pending approval requests for this zone
        for act in self._actions.values():
            if act.zone_id == resolved_zone and act.state == "AWAITING_USER_APPROVAL":
                act.state = "REJECTED"
                act.message = "Cancelled due to emergency pump stop."

        self._audit_log.append({
            "event": "EMERGENCY_STOP",
            "session_id": session_id,
            "zone_id": resolved_zone,
            "timestamp": now,
        })

        zone_meta = telemetry_service.get_zone(resolved_zone) or {"crop": "फसल"}
        crop_name = zone_meta.get("crop", "फसल")

        if is_hindi:
            reply = f"आपातकालीन आदेश: {resolved_zone} ({crop_name}) के लिए पानी का पंप तुरंत बंद कर दिया गया है। (सिम्युलेटेड मोड)"
        else:
            reply = f"Emergency stop executed: Water pump for {resolved_zone} ({crop_name}) has been shut off immediately. (Simulated mode)"

        return True, reply

    def get_status(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns full diagnostic status of pump control service and safety boundary."""
        active_zone = zone_id or telemetry_service.get_active_zone_id()
        is_running = self.get_pump_state(active_zone)
        pending = [
            act.model_dump()
            for act in self._actions.values()
            if act.state == "AWAITING_USER_APPROVAL" and act.expires_at > time.time()
        ]
        return {
            "status": "ok",
            "active_zone_id": active_zone,
            "pump_running": is_running,
            "zone_states": dict(self._zone_pump_states),
            "pending_approvals_count": len(pending),
            "pending_approvals": pending,
            "safety_boundary": {
                "simulation_mode": True,
                "actuation_permitted": False,
                "relay_pin": 26,
                "hardware_isolated": True,
                "approval_timeout_sec": 300,
            },
        }


# Global singleton instance
pump_control_service = PumpControlService()
