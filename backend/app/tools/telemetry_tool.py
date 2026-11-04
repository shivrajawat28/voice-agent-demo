"""
Simulated Farm Telemetry Tools
Provides specialist agents with read-only access to simulated FertoBot soil sensors,
historical trends, device health, and alerts.
Hardware actuation is strictly prohibited.
All responses are flagged with data_source="simulated" and is_simulated=True.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.tools.base import BaseTool


def _get_telemetry_service():
    from app.services.telemetry_service import get_telemetry_provider
    return get_telemetry_provider()


class LatestTelemetryTool(BaseTool):
    """
    Retrieves latest simulated readings for a requested farm zone and device.
    """

    @property
    def name(self) -> str:
        return "latest_telemetry"

    @property
    def description(self) -> str:
        return (
            "Retrieves the latest simulated soil moisture, NPK nutrients, soil temperature, "
            "pH, electrical conductivity (EC), and device status for a specific farm zone."
        )

    async def execute(
        self,
        zone_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        svc = _get_telemetry_service()
        try:
            data = svc.get_latest_telemetry(zone_id=zone_id)
            if not data:
                return {
                    "status": "error",
                    "error": f"Zone '{zone_id}' not found in farm telemetry dataset.",
                    "zone_id": zone_id,
                }
            profile_obj = svc.get_canonical_soil_profile(zone_id=zone_id)
            profile = profile_obj.model_dump() if hasattr(profile_obj, "model_dump") else (profile_obj if isinstance(profile_obj, dict) else {})
            return {
                "status": "success",
                "data_source": "simulated",
                "is_simulated": True,
                "actuation_permitted": False,
                "farm_id": data.get("farm_id", "DEMO-FARM-001"),
                "farm_name": data.get("farm_name"),
                "zone_id": data.get("zone_id", zone_id),
                "zone_name": data.get("zone_name"),
                "crop": data.get("crop"),
                "variety": data.get("variety"),
                "growth_stage": data.get("growth_stage"),
                "soil_type": data.get("soil_type"),
                "device_id": data.get("device_id"),
                "device_status": data.get("device_status"),
                "battery_level_pct": data.get("battery_level_pct"),
                "water_tank_level_pct": data.get("water_tank_level_pct"),
                "reading_timestamp_iso": data.get("reading_timestamp_iso"),
                # Sensor parameters
                "soil_moisture_pct": data.get("soil_moisture_pct"),
                "nitrogen_mg_kg": data.get("nitrogen_mg_kg"),
                "phosphorus_mg_kg": data.get("phosphorus_mg_kg"),
                "potassium_mg_kg": data.get("potassium_mg_kg"),
                "soil_temperature_c": data.get("soil_temperature_c"),
                "ph": data.get("ph"),
                "electrical_conductivity_ds_m": data.get("electrical_conductivity_ds_m"),
                "canonical_soil_profile": profile,
                "completeness_ratio": profile.get("completeness_ratio"),
                "available_count": profile.get("available_count"),
                "total_count": profile.get("total_count", 7),
                "overall_soil_health_index": profile.get("overall_soil_health_index"),
                "units": {
                    "soil_moisture_pct": "%",
                    "nitrogen_mg_kg": "mg/kg",
                    "phosphorus_mg_kg": "mg/kg",
                    "potassium_mg_kg": "mg/kg",
                    "soil_temperature_c": "°C",
                    "ph": "pH scale (0-14)",
                    "electrical_conductivity_ds_m": "dS/m",
                    "battery_level_pct": "%",
                    "water_tank_level_pct": "%",
                },
                "missing_fields": data.get("missing_fields", []),
                "warnings": data.get("warnings", []),
            }
        except KeyError as ke:
            return {
                "status": "error",
                "error": str(ke),
                "zone_id": zone_id,
            }


class SoilProfileTool(BaseTool):
    """
    Retrieves the canonical seven-parameter soil profile for a farm zone.
    Includes quality status, calibration status, and crop benchmarks for all 7 channels.
    """

    @property
    def name(self) -> str:
        return "soil_profile"

    @property
    def description(self) -> str:
        return (
            "Retrieves the canonical seven-parameter soil profile (N, P, K, moisture, temperature, "
            "pH, EC) with quality, calibration, and completeness status for a farm zone."
        )

    async def execute(self, zone_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            profile = _get_telemetry_service().get_canonical_soil_profile(zone_id=zone_id)
            return {
                "status": "success",
                "profile": profile.model_dump(),
            }
        except KeyError as ke:
            return {
                "status": "error",
                "error": str(ke),
                "zone_id": zone_id,
            }



class HistoricalTelemetryTool(BaseTool):
    """
    Retrieves historical simulated readings for a requested parameter and time range (24h or 7d).
    """

    @property
    def name(self) -> str:
        return "historical_telemetry"

    @property
    def description(self) -> str:
        return (
            "Retrieves historical time-series data and trend summaries (24h or 7d) "
            "for soil moisture, soil temperature, or NPK parameters."
        )

    async def execute(
        self,
        zone_id: Optional[str] = None,
        parameter: str = "soil_moisture_pct",
        time_range: str = "7d",
        **kwargs,
    ) -> Dict[str, Any]:
        trend = _get_telemetry_service().get_historical_telemetry(
            zone_id=zone_id,
            parameter=parameter,
            time_range=time_range,
        )
        return {
            "status": "success",
            "data_source": "simulated",
            "is_simulated": True,
            "actuation_permitted": False,
            **trend,
        }


class DeviceStatusTool(BaseTool):
    """
    Retrieves simulated FertoBot hardware device status, battery level, and last packet timestamp.
    """

    @property
    def name(self) -> str:
        return "device_status"

    @property
    def description(self) -> str:
        return "Checks if a FertoBot probe device is online, its battery percentage, and signal strength."

    async def execute(
        self,
        device_id: Optional[str] = None,
        zone_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        status_data = _get_telemetry_service().get_device_status(
            device_id=device_id,
            zone_id=zone_id,
        )
        return {
            "status": "success",
            "data_source": "simulated",
            "is_simulated": True,
            "actuation_permitted": False,
            **status_data,
        }


class WaterLevelTool(BaseTool):
    """
    Retrieves current water tank reservoir levels.
    """

    @property
    def name(self) -> str:
        return "water_level"

    @property
    def description(self) -> str:
        return "Checks the farm irrigation reservoir and water tank storage percentage."

    async def execute(
        self,
        zone_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        level_data = _get_telemetry_service().get_water_tank_level(zone_id=zone_id)
        return {
            "status": "success",
            "data_source": "simulated",
            "is_simulated": True,
            "actuation_permitted": False,
            **level_data,
        }


class AlertHistoryTool(BaseTool):
    """
    Retrieves active alerts and agricultural threshold warnings for the farm or zone.
    """

    @property
    def name(self) -> str:
        return "alert_history"

    @property
    def description(self) -> str:
        return "Retrieves active warnings and alerts regarding soil moisture, device battery, or sensor faults."

    async def execute(
        self,
        zone_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        alert_data = _get_telemetry_service().get_alert_history(zone_id=zone_id)
        return {
            "status": "success",
            "data_source": "simulated",
            "is_simulated": True,
            "actuation_permitted": False,
            **alert_data,
        }


class TelemetryTool(LatestTelemetryTool):
    """
    Backwards-compatible wrapper retaining tool name 'farm_telemetry'
    used across Phase 7-9 tests and baseline agent configurations.
    """

    @property
    def name(self) -> str:
        return "farm_telemetry"

    async def execute(self, probe_id: str = "probe_alpha_1", zone_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        res = await super().execute(zone_id=zone_id, **kwargs)
        # Preserve backwards compatibility keys expected by legacy tests
        res["source"] = "Farm Probe Telemetry (Read-Only)"
        res["probe_id"] = probe_id
        res["measurement_timestamp"] = res["reading_timestamp_iso"]
        res["sensors_online_count"] = 3
        res["soil_ec_salinity_ds_m"] = res.get("electrical_conductivity_ds_m", 1.2)
        return res
