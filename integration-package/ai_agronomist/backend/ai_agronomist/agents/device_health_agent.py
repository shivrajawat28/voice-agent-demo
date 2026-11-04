"""
Device Health Specialist Agent
Inspects hardware connectivity, probe battery levels, solar charging state,
water reservoir volume, and hardware alert logs.
"""
import re
from typing import List, Dict, Any
from ai_agronomist.agents.base import BaseAgent, AgentContext
from ai_agronomist.models.conversation import AgentResult
from ai_agronomist.tools.base import BaseTool


class DeviceHealthAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "device_health"

    @property
    def name(self) -> str:
        return "Device Health & Telemetry Specialist"

    @property
    def description(self) -> str:
        return (
            "Monitors FertoBot probe connectivity, battery levels, sensor telemetry health, "
            "water reservoir storage, and active device alerts."
        )

    @property
    def permitted_tools(self) -> List[str]:
        return ["device_status", "water_level", "alert_history", "latest_telemetry"]

    async def execute(
        self,
        context: AgentContext,
        tools: Dict[str, BaseTool],
    ) -> AgentResult:
        is_hindi = context.language.lower().startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", context.query)
        )
        zone_id = getattr(context, "zone_id", None) or "DEMO-ZONE-001"

        dev_tool = tools.get("device_status")
        water_tool = tools.get("water_level")
        alert_tool = tools.get("alert_history")
        tel_tool = tools.get("latest_telemetry")

        dev_data = await dev_tool.execute(zone_id=zone_id) if dev_tool else {}
        water_data = await water_tool.execute(zone_id=zone_id) if water_tool else {}
        alert_data = await alert_tool.execute(zone_id=zone_id) if alert_tool else {}
        tel_data = await tel_tool.execute(zone_id=zone_id) if tel_tool else {}

        device_id = dev_data.get("device_id", "DEMO-DEVICE-001")
        status = dev_data.get("status", "online")
        battery = dev_data.get("battery_level_pct", 92.0)
        water_tank = water_data.get("water_tank_level_pct", 82.0)
        alerts = alert_data.get("alerts", [])

        # Audit 7-channel sensor integrity from canonical soil profile
        completeness = tel_data.get("completeness_ratio", "7/7 parameters available")
        profile = tel_data.get("canonical_soil_profile", {})
        parameters = profile.get("parameters", {})
        degraded_channels: List[str] = []
        for p_key, p_info in parameters.items():
            if p_info.get("calibration_status") == "UNCALIBRATED" or p_info.get("quality_status") != "VALID":
                disp = p_info.get("display_name", p_key)
                c_st = p_info.get("calibration_status", "UNCALIBRATED")
                q_st = p_info.get("quality_status", "UNAVAILABLE")
                degraded_channels.append(f"{disp} ({c_st}/{q_st})")

        evidence: List[str] = [
            f"Device ID: {device_id} ({dev_data.get('zone_name', zone_id)})",
            f"Connectivity Status: {status.upper()}",
            f"Battery Level: {battery:.1f}%",
            f"Water Tank Level: {water_tank:.1f}%",
            f"7-in-1 Sensor Channels: {completeness}",
            f"Active Alerts in Zone: {len(alerts)}",
            "Data Source: Simulated FertoBot Hardware Telemetry",
        ]
        if degraded_channels:
            evidence.append(f"Sensor Warnings: Degraded/Uncalibrated channels: {', '.join(degraded_channels)}")

        limitations: List[str] = [
            "Battery percentage represents simulated voltage curve under illustrative load.",
            "Water reservoir level sensor is single-point hydrostatic depth reading.",
            "7-in-1 probe health relies on Modbus communication status and calibration registry flags.",
        ]

        # Generate contextual finding
        warnings = []
        if battery < 20.0:
            warnings.append(f"Device {device_id} battery is critically low ({battery:.1f}%). Solar harvester inspection required.")
        if status != "online":
            warnings.append(f"Device {device_id} is reporting state: {status}.")

        q_lower = context.query.lower()
        if any(w in q_lower for w in ["tank", "water", "पानी", "टैंक"]):
            if is_hindi:
                summary = (
                    f"आपके पानी के टैंक में वर्तमान जल स्तर {water_tank:.1f}% है। "
                    f"({device_id} सिमुलेटेड टेलीमेट्री के अनुसार)। "
                    f"{'पानी का स्तर पर्याप्त है।' if water_tank >= 50 else 'पानी का स्तर कम है, रीफिल की आवश्यकता हो सकती है।'}"
                )
            else:
                summary = (
                    f"The water tank storage is currently at {water_tank:.1f}% "
                    f"({'Adequate' if water_tank >= 50 else 'Low'}). "
                    f"Monitored via simulated FertoBot hardware device {device_id}."
                )
        elif any(w in q_lower for w in ["alert", "चेतावनी", "अलर्ट"]):
            if alerts:
                top_alert = alerts[0]
                if is_hindi:
                    summary = (
                        f"खेत में {len(alerts)} सक्रिय अलर्ट हैं। मुख्य अलर्ट: {top_alert['title']} - {top_alert['message']}"
                    )
                else:
                    summary = (
                        f"There are {len(alerts)} active alerts for this zone. Top alert: {top_alert['title']} - {top_alert['message']}"
                    )
            else:
                summary = (
                    "खेत और सेंसर में आज कोई सक्रिय अलर्ट नहीं है। सभी सिस्टम सामान्य हैं।"
                    if is_hindi
                    else "There are no active alerts for this zone today. All sensor systems are normal."
                )
        else:
            if is_hindi:
                status_hi = "ऑनलाइन" if status == "online" else ("चेतावनी" if status == "warning" else "ऑफलाइन")
                chan_msg = f" (सेंसर चैनल: {completeness})" if completeness else ""
                deg_msg = f" ध्यान दें: {', '.join(degraded_channels)} जांच आवश्यक है।" if degraded_channels else ""
                summary = (
                    f"आपका फर्तोबॉट डिवाइस {device_id} वर्तमान में {status_hi} है{chan_msg}। "
                    f"इसकी बैटरी {battery:.1f}% है और पानी का टैंक {water_tank:.1f}% भरा हुआ है। "
                    f"{'बैटरी बहुत कम है, कृपया चार्ज जांचें।' if battery < 20 else 'डिवाइस सही तरीके से काम कर रहा है।'}"
                    f"{deg_msg}"
                )
            else:
                chan_msg = f" (Sensor channels: {completeness})" if completeness else ""
                deg_msg = f" Notice: {', '.join(degraded_channels)} requires inspection/calibration." if degraded_channels else ""
                summary = (
                    f"Your FertoBot device {device_id} is currently {status.upper()}{chan_msg}. "
                    f"Battery level is at {battery:.1f}%, and water tank storage is at {water_tank:.1f}%. "
                    f"{'Warning: battery is critically low!' if battery < 20 else 'Hardware operations are normal.'}"
                    f"{deg_msg}"
                )

        return AgentResult(
            agent_id=self.agent_id,
            name=self.name,
            status="completed",
            summary=summary,
            evidence=evidence,
            limitations=limitations,
            data={
                "device_id": device_id,
                "status": status,
                "battery_level_pct": battery,
                "water_tank_level_pct": water_tank,
                "alerts_count": len(alerts),
                "completeness_ratio": completeness,
                "degraded_channels": degraded_channels,
                "is_simulated": True,
            },
        )
