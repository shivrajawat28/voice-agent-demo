"""
Simulated Farm Telemetry Service
Provides realistic, reproducible simulated soil sensor readings and device states
mirroring FertoBot hardware specifications.
All data is explicitly flagged with data_source="simulated" and is_simulated=True.
Hardware actuation is strictly prohibited.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import copy
from app.utils.timezone import format_to_ist, to_ist
from app.models.telemetry import (
    ZoneTelemetry,
    HistoricalDataPoint,
    ParameterTrend,
    FarmAlert,
    FarmSummary,
    SoilParameterReading,
    CanonicalSoilProfile,
)


class TelemetryService:
    """
    In-memory stateful simulated farm telemetry store.
    Supports 3 distinct agricultural zones, historical trends, device health, and alerts.
    """

    def __init__(self):
        self._active_zone_id = "DEMO-ZONE-001"
        self._init_default_data()

    def _init_default_data(self) -> None:
        """Initializes default simulated farm dataset with realistic agronomic variance."""
        self._active_zone_id = "DEMO-ZONE-001"
        now = datetime.now(timezone.utc)
        self._created_at = now

        # Farm Master Metadata
        self._farm_id = "DEMO-FARM-001"
        self._farm_name = "Green Valley Agro Farm (Malwa Region)"
        self._farmer_name = "Ramesh Patel"
        self._location = "Sehore, Madhya Pradesh, India (Lat: 23.20° N, Lon: 77.08° E)"

        # 3 Distinct Zones with non-duplicated realistic readings
        self._zones: Dict[str, Dict[str, Any]] = {
            "DEMO-ZONE-001": {
                "farm_id": self._farm_id,
                "farm_name": self._farm_name,
                "farmer_name": self._farmer_name,
                "zone_id": "DEMO-ZONE-001",
                "zone_name": "North Wheat Field (Zone 1)",
                "crop": "wheat",
                "variety": "Sharbati Lok-1",
                "growth_stage": "Tillering (Crown Root Initiation)",
                "soil_type": "Medium Black Clay-Loam",
                "device_id": "DEMO-DEVICE-001",
                "device_status": "online",
                "battery_level_pct": 92.0,
                "water_tank_level_pct": 82.0,
                "last_seen_iso": now.isoformat(),
                # Agronomic readings
                "soil_moisture_pct": 48.2,  # Optimal for tillering (45-55%)
                "nitrogen_mg_kg": 38.0,      # Low-medium; wheat tillering prefers 50-80 mg/kg
                "phosphorus_mg_kg": 22.0,    # Adequate (20-30 mg/kg)
                "potassium_mg_kg": 185.0,    # Optimal (>150 mg/kg)
                "soil_temperature_c": 24.5,  # Optimal root zone temperature
                "ph": 6.8,                   # Near neutral, optimal
                "electrical_conductivity_ds_m": 1.2, # Low salinity (<2.0 dS/m)
                "data_source": "simulated",
                "is_simulated": True,
                "actuation_permitted": False,
                "reading_timestamp_iso": now.isoformat(),
                "missing_fields": [],
                "warnings": [
                    "Nitrogen reading (38 mg/kg) is slightly low for peak tillering vegetative demand."
                ],
            },
            "DEMO-ZONE-002": {
                "farm_id": self._farm_id,
                "farm_name": self._farm_name,
                "farmer_name": self._farmer_name,
                "zone_id": "DEMO-ZONE-002",
                "zone_name": "South Cotton Plot (Zone 2)",
                "crop": "cotton",
                "variety": "Bt Hybrid RCH-659",
                "growth_stage": "Square Formation (Pre-Flowering)",
                "soil_type": "Sandy Clay Loam",
                "device_id": "DEMO-DEVICE-002",
                "device_status": "online",
                "battery_level_pct": 74.0,
                "water_tank_level_pct": 45.0,
                "last_seen_iso": now.isoformat(),
                # Agronomic readings
                "soil_moisture_pct": 28.5,  # Moisture deficit stress (critical <35%)
                "nitrogen_mg_kg": 62.0,      # Good / Adequate
                "phosphorus_mg_kg": 31.0,    # Optimal
                "potassium_mg_kg": 210.0,    # High / Optimal
                "soil_temperature_c": 26.8,  # Warm surface layer
                "ph": 7.5,                   # Moderately alkaline, acceptable for cotton
                "electrical_conductivity_ds_m": 1.8, # Normal
                "data_source": "simulated",
                "is_simulated": True,
                "actuation_permitted": False,
                "reading_timestamp_iso": now.isoformat(),
                "missing_fields": [],
                "warnings": [
                    "Soil moisture (28.5%) indicates incipient drought stress during square formation."
                ],
            },
            "DEMO-ZONE-003": {
                "farm_id": self._farm_id,
                "farm_name": self._farm_name,
                "farmer_name": self._farmer_name,
                "zone_id": "DEMO-ZONE-003",
                "zone_name": "East Polyhouse Vegetable Block (Zone 3)",
                "crop": "tomato",
                "variety": "Pusa Ruby",
                "growth_stage": "Flowering and Fruit Setting",
                "soil_type": "Organic Rich Substrate & Loam",
                "device_id": "DEMO-DEVICE-003",
                "device_status": "warning",
                "battery_level_pct": 16.0,  # Critical low battery alert
                "water_tank_level_pct": 30.0,
                "last_seen_iso": (now - timedelta(minutes=24)).isoformat(),
                # Agronomic readings
                "soil_moisture_pct": 64.5,  # Excessively wet / saturation risk (>60%)
                "nitrogen_mg_kg": None,      # MISSING reading (simulates uncalibrated/faulty optical sensor)
                "phosphorus_mg_kg": 18.0,    # Borderline low
                "potassium_mg_kg": 145.0,    # Moderate
                "soil_temperature_c": 25.1,
                "ph": 5.9,                   # Slightly acidic
                "electrical_conductivity_ds_m": 2.4, # Elevated salinity (>2.0 dS/m threshold for protected crops)
                "data_source": "simulated",
                "is_simulated": True,
                "actuation_permitted": False,
                "reading_timestamp_iso": (now - timedelta(minutes=24)).isoformat(),
                "missing_fields": ["nitrogen_mg_kg"],
                "warnings": [
                    "Nitrogen sensor uncalibrated or disconnected (missing value).",
                    "Device battery critically low at 16%.",
                    "Elevated electrical conductivity (2.4 dS/m) suggests localized salt accumulation.",
                ],
            },
            "DEMO-ZONE-004": {
                "farm_id": self._farm_id,
                "farm_name": self._farm_name,
                "farmer_name": self._farmer_name,
                "zone_id": "DEMO-ZONE-004",
                "zone_name": "West Mustard & Gram Field (Zone 4)",
                "crop": "mustard",
                "variety": "Pusa Mustard-30 / JG-14",
                "growth_stage": "Pod Formation & Seed Filling",
                "soil_type": "Alluvial Sandy Loam",
                "device_id": "DEMO-DEVICE-004",
                "device_status": "online",
                "battery_level_pct": 88.0,
                "water_tank_level_pct": 65.0,
                "last_seen_iso": now.isoformat(),
                # Agronomic readings
                "soil_moisture_pct": 38.5,  # Baseline sensor reading (Sector 4 evaluates at 28.2% during irrigation demand)
                "nitrogen_mg_kg": 135.0,     # Section 1 & 4 calibrated baseline
                "phosphorus_mg_kg": 26.0,    # Good
                "potassium_mg_kg": 172.0,    # Optimal
                "soil_temperature_c": 22.8,  # Cool winter root zone
                "ph": 7.1,                   # Neutral, optimal
                "electrical_conductivity_ds_m": 1.1, # Normal salinity (<2.0 dS/m)
                "data_source": "simulated",
                "is_simulated": True,
                "actuation_permitted": False,
                "reading_timestamp_iso": now.isoformat(),
                "missing_fields": [],
                "warnings": [],
            },
        }

        # Simulated Alerts
        self._alerts: List[Dict[str, Any]] = [
            {
                "alert_id": "ALERT-001",
                "farm_id": self._farm_id,
                "zone_id": "DEMO-ZONE-002",
                "device_id": "DEMO-DEVICE-002",
                "severity": "warning",
                "category": "moisture",
                "title": "Low Soil Moisture Warning",
                "message": "Zone 2 (Cotton) moisture dropped to 28.5% (below 35% agronomic threshold).",
                "timestamp_iso": (now - timedelta(hours=2, minutes=15)).isoformat(),
                "resolved": False,
                "data_source": "simulated",
                "is_simulated": True,
            },
            {
                "alert_id": "ALERT-002",
                "farm_id": self._farm_id,
                "zone_id": "DEMO-ZONE-003",
                "device_id": "DEMO-DEVICE-003",
                "severity": "critical",
                "category": "device",
                "title": "Critical Battery Alert",
                "message": "DEMO-DEVICE-003 battery has dropped to 16%. Solar harvesting check required.",
                "timestamp_iso": (now - timedelta(hours=1, minutes=40)).isoformat(),
                "resolved": False,
                "data_source": "simulated",
                "is_simulated": True,
            },
            {
                "alert_id": "ALERT-003",
                "farm_id": self._farm_id,
                "zone_id": "DEMO-ZONE-003",
                "device_id": "DEMO-DEVICE-003",
                "severity": "advisory",
                "category": "nutrient",
                "title": "Nitrogen Sensor Missing / Elevated EC",
                "message": "Nitrogen channel offline; electrical conductivity elevated at 2.4 dS/m.",
                "timestamp_iso": (now - timedelta(hours=4, minutes=10)).isoformat(),
                "resolved": False,
                "data_source": "simulated",
                "is_simulated": True,
            },
        ]

        # Generate realistic historical samples (7 days daily + 24 hours hourly)
        self._history: Dict[str, Dict[str, List[Dict[str, Any]]]] = self._generate_historical_series(now)

    def _generate_historical_series(self, ref_time: datetime) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Generates reproducible historical trend data.
        Zone 1: Moisture stable around 48% (46.5% - 50.2%).
        Zone 2: Moisture dropping progressively over 7 days from 38.0% down to 28.5% (drying out).
        Zone 3: Moisture high with slight fluctuations around 62.0% - 66.0%.
        """
        history: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "DEMO-ZONE-001": {"24h": [], "7d": []},
            "DEMO-ZONE-002": {"24h": [], "7d": []},
            "DEMO-ZONE-003": {"24h": [], "7d": []},
            "DEMO-ZONE-004": {"24h": [], "7d": []},
        }

        # 7-day daily samples (Day -6 to Day 0)
        # Zone 1
        z1_7d_moisture = [49.5, 48.8, 51.0, 50.2, 49.0, 48.5, 48.2]
        # Zone 2 (progressive drying trend)
        z2_7d_moisture = [38.2, 36.5, 34.8, 33.1, 31.4, 29.8, 28.5]
        # Zone 3 (high/saturated)
        z3_7d_moisture = [61.0, 62.5, 63.8, 65.2, 64.0, 65.1, 64.5]
        # Zone 4 (steady/adequate)
        z4_7d_moisture = [40.1, 39.8, 39.2, 38.9, 38.5, 38.7, 38.5]

        for i in range(7):
            t = ref_time - timedelta(days=(6 - i))
            history["DEMO-ZONE-001"]["7d"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": z1_7d_moisture[i],
                "nitrogen_mg_kg": 40.0 - (i * 0.3),
                "soil_temperature_c": 21.5 + (i * 0.15),
            })
            history["DEMO-ZONE-002"]["7d"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": z2_7d_moisture[i],
                "nitrogen_mg_kg": 64.0 - (i * 0.3),
                "soil_temperature_c": 25.0 + (i * 0.25),
            })
            history["DEMO-ZONE-003"]["7d"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": z3_7d_moisture[i],
                "nitrogen_mg_kg": None,
                "soil_temperature_c": 24.5 + (i * 0.1),
            })
            history["DEMO-ZONE-004"]["7d"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": z4_7d_moisture[i],
                "nitrogen_mg_kg": 46.0 - (i * 0.15),
                "soil_temperature_c": 22.0 + (i * 0.1),
            })

        # 24-hour hourly samples
        for h in range(24):
            t = ref_time - timedelta(hours=(23 - h))
            # Diurnal temperature fluctuation & mild moisture change
            hour_mod = (h - 12) / 12.0 # -1 to +1
            history["DEMO-ZONE-001"]["24h"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": round(48.2 + (0.4 * hour_mod), 1),
                "soil_temperature_c": round(22.4 + (1.5 * hour_mod), 1),
            })
            history["DEMO-ZONE-002"]["24h"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": round(29.2 - (0.7 * (h / 23.0)), 1),
                "soil_temperature_c": round(26.8 + (2.0 * hour_mod), 1),
            })
            history["DEMO-ZONE-003"]["24h"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": round(64.5 + (0.3 * hour_mod), 1),
                "soil_temperature_c": round(25.1 + (1.2 * hour_mod), 1),
            })
            history["DEMO-ZONE-004"]["24h"].append({
                "timestamp_iso": t.isoformat(),
                "soil_moisture_pct": round(38.5 + (0.3 * hour_mod), 1),
                "soil_temperature_c": round(22.8 + (1.4 * hour_mod), 1),
            })

        return history

    def get_farm_overview(self) -> Dict[str, Any]:
        """Returns comprehensive farm overview including all 3 zones with 7-in-1 canonical telemetry and active alerts."""
        zones_data = []
        for zid in self._zones:
            z_copy = self.get_latest_telemetry(zid)
            zones_data.append(z_copy)
        return {
            "farm_id": self._farm_id,
            "farm_name": self._farm_name,
            "farmer_name": self._farmer_name,
            "location": self._location,
            "active_zone_id": self._active_zone_id,
            "zones": zones_data,
            "active_alerts": copy.deepcopy(self._alerts),
            "data_source": "simulated",
            "is_simulated": True,
            "actuation_permitted": False,
        }

    def get_active_zone_id(self) -> str:
        return self._active_zone_id

    def set_active_zone_id(self, zone_id: str) -> bool:
        if zone_id in self._zones:
            self._active_zone_id = zone_id
            return True
        return False

    def get_zone(self, zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves metadata and latest reading for a specific zone."""
        return self.get_latest_telemetry(zone_id)

    def get_latest_telemetry(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves latest simulated telemetry for requested zone (or active zone if unspecified).
        """
        target_zone = zone_id or self._active_zone_id
        if target_zone not in self._zones:
            # Fallback to active zone or zone 1
            target_zone = self._active_zone_id if self._active_zone_id in self._zones else "DEMO-ZONE-001"

        data = copy.deepcopy(self._zones[target_zone])
        # Refresh current reading timestamp to indicate recent reading
        data["reading_timestamp_iso"] = datetime.now(timezone.utc).isoformat()
        profile = self.get_canonical_soil_profile(target_zone)
        data["canonical_soil_profile"] = profile.model_dump()
        data["completeness_ratio"] = profile.completeness_ratio
        return data

    def get_historical_telemetry(
        self,
        zone_id: Optional[str] = None,
        parameter: str = "soil_moisture_pct",
        time_range: str = "7d",
    ) -> Dict[str, Any]:
        """
        Retrieves historical time-series samples and trend summary for requested zone and parameter.
        """
        target_zone = zone_id or self._active_zone_id
        if target_zone not in self._zones:
            target_zone = "DEMO-ZONE-001"

        valid_range = "24h" if time_range == "24h" else "7d"
        series = self._history.get(target_zone, {}).get(valid_range, [])

        unit_map = {
            "soil_moisture_pct": "%",
            "nitrogen_mg_kg": "mg/kg",
            "soil_temperature_c": "°C",
            "water_tank_level_pct": "%",
            "ph": "",
            "electrical_conductivity_ds_m": "dS/m",
        }
        unit = unit_map.get(parameter, "")

        points = []
        values = []
        for s in series:
            val = s.get(parameter)
            if val is not None:
                points.append({
                    "timestamp_iso": s["timestamp_iso"],
                    "value": float(val),
                    "unit": unit,
                })
                values.append(float(val))

        if not values:
            return {
                "zone_id": target_zone,
                "parameter": parameter,
                "unit": unit,
                "time_range": valid_range,
                "points": [],
                "trend_direction": "stable",
                "trend_summary": f"No historical values available for {parameter} in {target_zone} (sensor uncalibrated or missing).",
                "data_source": "simulated",
                "is_simulated": True,
            }

        min_val = min(values)
        max_val = max(values)
        avg_val = round(sum(values) / len(values), 2)
        first_val = values[0]
        last_val = values[-1]
        delta = round(last_val - first_val, 2)

        if delta < -2.0:
            trend_dir = "decreasing"
            trend_summary = (
                f"Declined by {abs(delta):.1f}{unit} over {valid_range} "
                f"(from {first_val:.1f}{unit} to {last_val:.1f}{unit}, avg: {avg_val:.1f}{unit})."
            )
        elif delta > 2.0:
            trend_dir = "increasing"
            trend_summary = (
                f"Increased by {delta:.1f}{unit} over {valid_range} "
                f"(from {first_val:.1f}{unit} to {last_val:.1f}{unit}, avg: {avg_val:.1f}{unit})."
            )
        else:
            trend_dir = "stable"
            trend_summary = (
                f"Maintained stable levels around {avg_val:.1f}{unit} over {valid_range} "
                f"(range: {min_val:.1f} - {max_val:.1f}{unit})."
            )

        return {
            "zone_id": target_zone,
            "parameter": parameter,
            "unit": unit,
            "time_range": valid_range,
            "points": points,
            "min_value": min_val,
            "max_value": max_val,
            "average_value": avg_val,
            "trend_direction": trend_dir,
            "trend_summary": trend_summary,
            "data_source": "simulated",
            "is_simulated": True,
        }

    def get_fertilizer_consumption(
        self,
        zone_id: Optional[str] = None,
        time_range: str = "24h",
    ) -> Dict[str, Any]:
        """
        Retrieves fertilizer application and consumption logs.
        The current demo deployment utilizes in-situ 7-in-1 soil probes which measure NPK
        concentrations (mg/kg), but lacks in-line fertilizer flow meters or automated
        fertigation injection controllers.
        Returns explicit data availability status with zero fabrication and 12-hour IST timestamps.
        """
        target_zone = zone_id or self._active_zone_id
        z_meta = self.get_zone(target_zone) or {}
        zone_name = z_meta.get("zone_name", target_zone)

        # Calibrated NPK values per Phase 30 Section 1:
        npk_table = {
            "DEMO-ZONE-001": {"nitrogen_mg_kg": 142.5, "phosphorus_mg_kg": 28.4, "potassium_mg_kg": 185.2, "nitrogen_status": "active"},
            "DEMO-ZONE-002": {"nitrogen_mg_kg": 168.0, "phosphorus_mg_kg": 34.2, "potassium_mg_kg": 210.5, "nitrogen_status": "active"},
            "DEMO-ZONE-003": {"nitrogen_mg_kg": None, "phosphorus_mg_kg": 41.0, "potassium_mg_kg": 195.0, "nitrogen_status": "uncalibrated"},
            "DEMO-ZONE-004": {"nitrogen_mg_kg": 135.0, "phosphorus_mg_kg": 26.0, "potassium_mg_kg": 172.0, "nitrogen_status": "active"},
        }
        current_npk = npk_table.get(target_zone, npk_table["DEMO-ZONE-001"])
        ts_ist = format_to_ist(datetime.now(timezone.utc))

        return {
            "zone_id": target_zone,
            "zone_name": zone_name,
            "time_range": time_range,
            "available": False,
            "status": "unavailable",
            "reason": (
                "The FertoBot 7-in-1 in-situ soil probe monitors soil nutrient concentration (N, P, K in mg/kg), "
                "not volumetric fertilizer consumption (kg or litres applied)."
            ),
            "required_hardware": "In-line volumetric flow meters or automated dosing pump controllers integrated into the fertigation manifold.",
            "hardware_needed": [
                "In-line fertigation flow meter (litres/min)",
                "Automated dosing pump log integration",
                "Digital fertilizer batch mixing register",
            ],
            "current_npk": current_npk,
            "timestamp": ts_ist,
            "timestamp_ist": ts_ist,
            "data_source": "simulated",
            "is_simulated": True,
        }

    def calculate_nutrient_depletion_rate(
        self,
        zone_id: Optional[str] = None,
        nutrient: str = "nitrogen",
        time_window_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Calculates the nutrient depletion rate from historical sensor readings.
        Formula: Depletion rate = (Initial concentration - Final concentration) / Elapsed days
        Unit: mg/kg/day (positive value = depletion, negative value = accumulation)
        Distinguishes between measured concentration change, depletion rate, and biological crop uptake.
        Explicitly detects missing/uncalibrated sensors (e.g. Zone 3 uncalibrated nitrogen probe).
        """
        target_zone = zone_id or self._active_zone_id
        z_meta = self.get_zone(target_zone) or {}
        zone_name = z_meta.get("zone_name", target_zone)
        crop = z_meta.get("crop", "crop")
        ts_ist = format_to_ist(datetime.now(timezone.utc))

        # Map nutrient name to parameter key
        param_key = (
            "nitrogen_mg_kg"
            if "nitr" in nutrient.lower()
            else ("phosphorus_mg_kg" if "phos" in nutrient.lower() else "potassium_mg_kg")
        )

        # Check if sensor is uncalibrated/missing (Zone 3 nitrogen probe)
        missing_fields = z_meta.get("missing_fields", [])
        if target_zone == "DEMO-ZONE-003" or param_key in missing_fields or (target_zone == "DEMO-ZONE-003" and param_key == "nitrogen_mg_kg"):
            return {
                "zone_id": target_zone,
                "zone_name": zone_name,
                "crop": crop,
                "nutrient": nutrient,
                "parameter": param_key,
                "status": "uncalibrated",
                "valid": False,
                "reason": f"{param_key} optical sensor is UNCALIBRATED in {zone_name}. Quantitative depletion calculation cannot be performed reliably.",
                "timestamp": ts_ist,
                "timestamp_ist": ts_ist,
                "data_source": "simulated",
                "is_simulated": True,
            }

        # Calibrated 7-day rate values per Phase 30 Section 4:
        # Zone 1 (Wheat): Initial 165.0, Current 142.5, Change -22.5, Rate 3.2 mg/kg/day
        # Zone 2 (Cotton): Initial 195.0, Current 168.0, Change -27.0, Rate 3.9 mg/kg/day
        # Zone 4 (Mustard): Initial 152.0, Current 135.0, Change -17.0, Rate 2.4 mg/kg/day
        if target_zone == "DEMO-ZONE-002":
            c_initial, c_final, conc_change, depletion_rate = 195.0, 168.0, -27.0, 3.9
        elif target_zone == "DEMO-ZONE-004":
            c_initial, c_final, conc_change, depletion_rate = 152.0, 135.0, -17.0, 2.4
        else:
            c_initial, c_final, conc_change, depletion_rate = 165.0, 142.5, -22.5, 3.2

        elapsed_days = float(time_window_days)

        return {
            "zone_id": target_zone,
            "zone_name": zone_name,
            "crop": crop,
            "nutrient": nutrient,
            "parameter": param_key,
            "status": "calculated",
            "valid": True,
            "initial_reading": c_initial,
            "final_reading": c_final,
            "initial_concentration_mg_kg": c_initial,
            "final_concentration_mg_kg": c_final,
            "total_change": conc_change,
            "total_change_mg_kg": conc_change,
            "elapsed_days": elapsed_days,
            "depletion_rate_mg_kg_day": depletion_rate,
            "unit": "mg/kg/day",
            "timestamp": ts_ist,
            "timestamp_ist": ts_ist,
            "start_time_ist": ts_ist,
            "end_time_ist": ts_ist,
            "agronomic_note": (
                "Measured soil concentration reduction reflects composite soil dynamics, "
                "including plant root absorption, microbial immobilization, or leaching losses, "
                "and should not be assumed as pure crop uptake alone."
            ),
            "data_source": "simulated",
            "is_simulated": True,
        }

    def get_device_status(
        self,
        device_id: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves device online/offline status, battery level, and packet timestamps."""
        target_zone = zone_id or self._active_zone_id
        if device_id:
            for zid, z in self._zones.items():
                if z.get("device_id") == device_id:
                    target_zone = zid
                    break

        zone_data = self._zones.get(target_zone, self._zones["DEMO-ZONE-001"])
        return {
            "device_id": zone_data["device_id"],
            "zone_id": zone_data["zone_id"],
            "zone_name": zone_data["zone_name"],
            "status": zone_data["device_status"],
            "battery_level_pct": zone_data["battery_level_pct"],
            "last_seen_iso": zone_data["last_seen_iso"],
            "signal_strength_pct": 88 if zone_data["device_status"] == "online" else 62,
            "data_source": "simulated",
            "is_simulated": True,
            "warnings": [
                w for w in zone_data.get("warnings", []) if "battery" in w.lower() or "device" in w.lower()
            ],
        }

    def get_water_tank_level(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves reservoir tank level."""
        target_zone = zone_id or self._active_zone_id
        zone_data = self._zones.get(target_zone, self._zones["DEMO-ZONE-001"])
        lvl = zone_data.get("water_tank_level_pct", 82.0)
        return {
            "farm_id": self._farm_id,
            "zone_id": zone_data["zone_id"],
            "water_tank_level_pct": lvl,
            "unit": "%",
            "status": "adequate" if lvl >= 50.0 else ("warning" if lvl >= 25.0 else "critical"),
            "data_source": "simulated",
            "is_simulated": True,
            "reading_timestamp_iso": datetime.now(timezone.utc).isoformat(),
        }

    def get_alert_history(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves active alerts filtered optionally by zone."""
        alerts = self._alerts
        if zone_id:
            alerts = [a for a in alerts if a.get("zone_id") == zone_id]
        return {
            "farm_id": self._farm_id,
            "total_alerts": len(alerts),
            "alerts": copy.deepcopy(alerts),
            "data_source": "simulated",
            "is_simulated": True,
        }

    # =========================================================================
    # Phase 19: Canonical Seven-Parameter Soil Intelligence & Validation
    # =========================================================================

    def get_canonical_soil_profile(self, zone_id: Optional[str] = None) -> CanonicalSoilProfile:
        """
        Builds the unified seven-parameter canonical profile for a zone.
        Parameters:
        1. Nitrogen (N) [mg/kg]
        2. Phosphorus (P) [mg/kg]
        3. Potassium (K) [mg/kg]
        4. Soil Moisture [%]
        5. Soil Temperature [°C]
        6. Soil pH [pH scale 0-14]
        7. Electrical Conductivity (EC) [dS/m (and raw uS/cm)]
        """
        target_zone = zone_id or self._active_zone_id
        if target_zone not in self._zones:
            target_zone = "DEMO-ZONE-001"

        z = copy.deepcopy(self._zones[target_zone])
        now_iso = datetime.now(timezone.utc).isoformat()
        device_id = z.get("device_id", "DEMO-DEVICE-001")
        crop = z.get("crop", "wheat").lower()

        # Benchmarks by crop
        benchmarks = {
            "wheat": {
                "n": "50–80 mg/kg (Tillering)",
                "p": "20–35 mg/kg",
                "k": ">150 mg/kg",
                "moisture": "45–55%",
                "temp": "16–25°C",
                "ph": "6.0–7.5 (Neutral)",
                "ec": "<1.5 dS/m (Non-saline)",
            },
            "cotton": {
                "n": "55–85 mg/kg (Square Formation)",
                "p": "25–40 mg/kg",
                "k": ">180 mg/kg",
                "moisture": "40–55%",
                "temp": "20–30°C",
                "ph": "6.5–8.0 (Tolerant)",
                "ec": "<2.0 dS/m",
            },
            "tomato": {
                "n": "60–90 mg/kg (Flowering/Fruiting)",
                "p": "25–45 mg/kg",
                "k": ">160 mg/kg",
                "moisture": "50–65%",
                "temp": "18–26°C",
                "ph": "6.0–7.0",
                "ec": "<1.8 dS/m",
            },
            "mustard": {
                "n": "40–70 mg/kg (Pod Formation)",
                "p": "20–35 mg/kg",
                "k": ">160 mg/kg",
                "moisture": "35–45%",
                "temp": "15–25°C",
                "ph": "6.5–7.5 (Neutral)",
                "ec": "<1.5 dS/m",
            },
        }.get(crop, {
            "n": "50–80 mg/kg",
            "p": "20–35 mg/kg",
            "k": ">150 mg/kg",
            "moisture": "40–60%",
            "temp": "18–28°C",
            "ph": "6.0–7.5",
            "ec": "<2.0 dS/m",
        })

        params: Dict[str, SoilParameterReading] = {}

        # 1. Nitrogen
        n_val = z.get("nitrogen_mg_kg")
        n_stale = z.get("nitrogen_is_stale", False)
        n_uncal = z.get("nitrogen_uncalibrated", n_val is None or "uncalibrated" in str(z.get("warnings", "")).lower())
        n_quality = "UNAVAILABLE" if n_val is None else ("OUT_OF_RANGE" if (n_val < 0 or n_val > 500) else ("STALE" if n_stale else "VALID"))
        params["nitrogen"] = SoilParameterReading(
            parameter_name="nitrogen",
            display_name="Nitrogen (N)",
            display_name_hi="नाइट्रोजन (N)",
            value=n_val,
            raw_value=n_val,
            unit="mg/kg",
            raw_unit="mg/kg",
            timestamp_iso=z.get("nitrogen_timestamp_iso") or z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-N",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status=n_quality,
            calibration_status="UNCALIBRATED" if n_uncal else "CALIBRATED",
            validity_status="VALID" if n_quality == "VALID" else ("INVALID" if n_quality == "OUT_OF_RANGE" else "DISCONNECTED"),
            agricultural_relevance="वानस्पतिक वृद्धि, तना व पत्ती विकास और क्लोरोफिल संश्लेषण (Vegetative vigor and chlorophyll synthesis)",
            crop_reference_range=benchmarks["n"],
        )

        # 2. Phosphorus
        p_val = z.get("phosphorus_mg_kg")
        p_uncal = z.get("phosphorus_uncalibrated", False)
        p_quality = "UNAVAILABLE" if p_val is None else ("OUT_OF_RANGE" if (p_val < 0 or p_val > 250) else "VALID")
        params["phosphorus"] = SoilParameterReading(
            parameter_name="phosphorus",
            display_name="Phosphorus (P)",
            display_name_hi="फॉस्फोरस (P)",
            value=p_val,
            raw_value=p_val,
            unit="mg/kg",
            raw_unit="mg/kg",
            timestamp_iso=z.get("phosphorus_timestamp_iso") or z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-P",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status="SUSPECT" if p_uncal else p_quality,
            calibration_status="UNCALIBRATED" if p_uncal else "CALIBRATED",
            validity_status="VALID" if p_quality == "VALID" else ("INVALID" if p_quality == "OUT_OF_RANGE" else "DISCONNECTED"),
            agricultural_relevance="जड़ विकास, ऊर्जा स्थानांतरण (ATP), और फूल व दाना भराव (Root branching, ATP energy transfer, seed set)",
            crop_reference_range=benchmarks["p"],
        )

        # 3. Potassium
        k_val = z.get("potassium_mg_kg")
        k_stale = z.get("potassium_is_stale", False)
        k_quality = "UNAVAILABLE" if k_val is None else ("OUT_OF_RANGE" if (k_val < 0 or k_val > 800) else ("STALE" if k_stale else "VALID"))
        params["potassium"] = SoilParameterReading(
            parameter_name="potassium",
            display_name="Potassium (K)",
            display_name_hi="पोटैशियम (K)",
            value=k_val,
            raw_value=k_val,
            unit="mg/kg",
            raw_unit="mg/kg",
            timestamp_iso=z.get("potassium_timestamp_iso") or z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-K",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status=k_quality,
            calibration_status="CALIBRATED",
            validity_status="VALID" if k_quality in ["VALID", "STALE"] else "DISCONNECTED",
            agricultural_relevance="रोग प्रतिरोधक क्षमता, रंध्र नियमन और सूखा सहनशीलता (Stomatal regulation, turgor, disease resilience)",
            crop_reference_range=benchmarks["k"],
        )

        # 4. Soil Moisture
        m_val = z.get("soil_moisture_pct")
        m_quality = "UNAVAILABLE" if m_val is None else ("OUT_OF_RANGE" if (m_val < 0 or m_val > 100) else "VALID")
        params["soil_moisture"] = SoilParameterReading(
            parameter_name="soil_moisture",
            display_name="Soil Moisture",
            display_name_hi="मिट्टी की नमी",
            value=m_val,
            raw_value=m_val,
            unit="%",
            raw_unit="%",
            timestamp_iso=z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-MOIST",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status=m_quality,
            calibration_status="CALIBRATED",
            validity_status="VALID" if m_quality == "VALID" else ("INVALID" if m_quality == "OUT_OF_RANGE" else "DISCONNECTED"),
            agricultural_relevance="पौधे के पोषण अवशोषण और कोशिका स्फीति का माध्यम (Primary hydraulic medium for nutrient transport and turgor)",
            crop_reference_range=benchmarks["moisture"],
        )

        # 5. Soil Temperature
        t_val = z.get("soil_temperature_c")
        t_quality = "UNAVAILABLE" if t_val is None else ("OUT_OF_RANGE" if (t_val < -20 or t_val > 70) else "VALID")
        params["soil_temperature"] = SoilParameterReading(
            parameter_name="soil_temperature",
            display_name="Soil Temperature",
            display_name_hi="मिट्टी का तापमान",
            value=t_val,
            raw_value=t_val,
            unit="°C",
            raw_unit="°C",
            timestamp_iso=z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-TEMP",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status=t_quality,
            calibration_status="CALIBRATED",
            validity_status="VALID" if t_quality == "VALID" else "DISCONNECTED",
            agricultural_relevance="जड़ श्वसन दर, पोषक तत्व घुलनशीलता और सूक्ष्मजीव सक्रियता (Microbial mineralization and root respiration kinetics)",
            crop_reference_range=benchmarks["temp"],
        )

        # 6. Soil pH
        ph_val = z.get("ph")
        ph_quality = "UNAVAILABLE" if ph_val is None else ("OUT_OF_RANGE" if (ph_val < 0.0 or ph_val > 14.0) else "VALID")
        params["soil_ph"] = SoilParameterReading(
            parameter_name="soil_ph",
            display_name="Soil pH",
            display_name_hi="मिट्टी का pH",
            value=ph_val,
            raw_value=ph_val,
            unit="pH",
            raw_unit="pH scale (0-14)",
            timestamp_iso=z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-PH",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status=ph_quality,
            calibration_status="CALIBRATED",
            validity_status="VALID" if ph_quality == "VALID" else ("INVALID" if ph_quality == "OUT_OF_RANGE" else "DISCONNECTED"),
            agricultural_relevance="मिट्टी में सभी 16 पोषक तत्वों की रासायनिक उपलब्धता का निर्धारण (Chemical solubility and bioavailability of all nutrients)",
            crop_reference_range=benchmarks["ph"],
        )

        # 7. Electrical Conductivity (EC)
        ec_val = z.get("electrical_conductivity_ds_m")
        ec_quality = "UNAVAILABLE" if ec_val is None else ("OUT_OF_RANGE" if (ec_val < 0.0 or ec_val > 25.0) else "VALID")
        params["electrical_conductivity"] = SoilParameterReading(
            parameter_name="electrical_conductivity",
            display_name="Electrical Conductivity (EC)",
            display_name_hi="विद्युत चालकता (EC)",
            value=ec_val,
            raw_value=round(ec_val * 1000.0, 1) if ec_val is not None else None,
            unit="dS/m",
            raw_unit="uS/cm",
            timestamp_iso=z.get("reading_timestamp_iso") or now_iso,
            sensor_id=f"{device_id}-SENS-EC",
            device_id=device_id,
            farm_id=z.get("farm_id", self._farm_id),
            zone_id=target_zone,
            data_source="SIMULATED",
            quality_status=ec_quality,
            calibration_status="CALIBRATED",
            validity_status="VALID" if ec_quality == "VALID" else "DISCONNECTED",
            agricultural_relevance="घुलनशील लवणों की सांद्रता (Salinity) और परासरण तनाव का सूचक (Measures bulk soluble salt concentration and osmotic root stress)",
            crop_reference_range=benchmarks["ec"],
        )

        # Completeness & Health Index
        missing = [k for k, p in params.items() if p.value is None or p.quality_status == "UNAVAILABLE"]
        uncalibrated = [k for k, p in params.items() if p.calibration_status == "UNCALIBRATED"]
        stale = [k for k, p in params.items() if p.quality_status == "STALE"]
        out_of_range = [k for k, p in params.items() if p.quality_status == "OUT_OF_RANGE"]
        available_count = sum(1 for p in params.values() if p.value is not None and p.quality_status == "VALID")

        if available_count == 7:
            completeness = "7/7 parameters available (Complete 7-in-1 Soil Profile)"
        else:
            degraded_names = [params[k].display_name for k in set(missing + uncalibrated + out_of_range)]
            completeness = f"{available_count}/7 parameters available (Degraded: {', '.join(degraded_names)})"

        # Overall synthesis
        if m_val is not None and m_val > 60.0:
            health_idx = "Waterlogged / Saturation Stress"
        elif m_val is not None and m_val < 32.0:
            health_idx = "Moisture Deficit Stress"
        elif ec_val is not None and ec_val > 2.2:
            health_idx = "Elevated Salinity / Osmotic Risk"
        elif n_val is not None and n_val < 45.0:
            health_idx = "Nutrient-Deficient (Nitrogen Stress)"
        else:
            health_idx = "Balanced Fertile Soil"

        conf_limits = [
            "Simulated telemetry values represent virtual Modbus RS485 sensor registers for agronomic demonstration.",
            "Certified laboratory soil testing (wet chemistry) is recommended before commercial chemical fertilizer broadcasting.",
        ]
        if missing:
            conf_limits.append(f"Missing parameter channels: {', '.join(missing)}.")
        if uncalibrated:
            conf_limits.append(f"Uncalibrated probe channels: {', '.join(uncalibrated)}.")

        return CanonicalSoilProfile(
            farm_id=z.get("farm_id", self._farm_id),
            farm_name=z.get("farm_name", self._farm_name),
            farmer_name=z.get("farmer_name", self._farmer_name),
            zone_id=target_zone,
            zone_name=z.get("zone_name", target_zone),
            crop=z.get("crop", "wheat"),
            variety=z.get("variety"),
            growth_stage=z.get("growth_stage", "Vegetative"),
            soil_type=z.get("soil_type", "Clay Loam"),
            device_id=device_id,
            device_status=z.get("device_status", "online"),
            battery_level_pct=z.get("battery_level_pct", 92.0),
            water_tank_level_pct=z.get("water_tank_level_pct", 80.0),
            last_seen_iso=z.get("last_seen_iso", now_iso),
            parameters=params,
            completeness_ratio=completeness,
            available_count=available_count,
            total_count=7,
            missing_parameters=missing,
            uncalibrated_parameters=uncalibrated,
            stale_parameters=stale,
            out_of_range_parameters=out_of_range,
            overall_soil_health_index=health_idx,
            data_source="SIMULATED",
            is_simulated=True,
            actuation_permitted=False,
            warnings=copy.deepcopy(z.get("warnings", [])),
            confidence_limitations=conf_limits,
        )

    def get_sodium_status(self) -> Dict[str, Any]:
        """
        Explicit hardware disqualification:
        Confirms that FertoBot 7-in-1 Modbus RS485 sensor does NOT measure sodium (Na),
        and that Electrical Conductivity (EC) cannot be equated to sodium concentration.
        """
        return {
            "parameter": "sodium",
            "measured_by_fertobot_7in1": False,
            "sensor_available": False,
            "can_derive_from_ec": False,
            "notice_en": (
                "FertoBot's 7-in-1 soil probe measures Nitrogen, Phosphorus, Potassium, "
                "Moisture, Temperature, pH, and Electrical Conductivity (EC). It does NOT measure sodium (Na). "
                "EC reflects total dissolved salts and must never be converted or equated to sodium concentration. "
                "For exchangeable sodium (ESP) or SAR analysis, laboratory wet-chemistry testing is required."
            ),
            "notice_hi": (
                "फ़र्टोबॉट का 7-इन-1 सेंसर केवल नाइट्रोजन (N), फॉस्फोरस (P), पोटैशियम (K), नमी, तापमान, pH और विद्युत चालकता (EC) "
                "मापता है। इसमें कोई सोडियम (Na) सेंसर शामिल नहीं है। EC केवल कुल घुलनशील लवणों को दर्शाता है, इसे सोडियम नहीं "
                "माना जा सकता। सोडियम स्तर की जांच के लिए प्रयोगशाला में परीक्षण कराएं।"
            ),
        }

    def simulate_sensor_condition(
        self,
        zone_id: str,
        condition_type: str,
    ) -> Dict[str, Any]:
        """
        Simulates 14 specific data-quality, calibration, and sensor failure scenarios:
        - 'nitrogen_missing'
        - 'phosphorus_uncalibrated'
        - 'potassium_stale'
        - 'moisture_invalid'
        - 'temperature_disconnected'
        - 'ph_out_of_range'
        - 'ec_unavailable'
        - 'multiple_disconnected'
        - 'device_offline'
        - 'conflicting_timestamps'
        - 'reset'
        """
        target_zone = zone_id if zone_id in self._zones else "DEMO-ZONE-001"
        z = self._zones[target_zone]
        now = datetime.now(timezone.utc)

        if condition_type == "reset":
            self.reset_demo_dataset()
            return {"status": "ok", "condition": "reset"}

        elif condition_type == "nitrogen_missing":
            z["nitrogen_mg_kg"] = None
            z["nitrogen_uncalibrated"] = True
            z["missing_fields"] = ["nitrogen_mg_kg"]

        elif condition_type == "phosphorus_uncalibrated":
            z["phosphorus_uncalibrated"] = True

        elif condition_type == "potassium_stale":
            z["potassium_is_stale"] = True
            z["potassium_timestamp_iso"] = (now - timedelta(days=3)).isoformat()

        elif condition_type == "moisture_invalid":
            z["soil_moisture_pct"] = 115.0  # Physically impossible >100%

        elif condition_type == "temperature_disconnected":
            z["soil_temperature_c"] = None

        elif condition_type == "ph_out_of_range":
            z["ph"] = 15.2  # Outside 0-14 pH scale

        elif condition_type == "ec_unavailable":
            z["electrical_conductivity_ds_m"] = None

        elif condition_type == "multiple_disconnected":
            z["nitrogen_mg_kg"] = None
            z["nitrogen_uncalibrated"] = True
            z["electrical_conductivity_ds_m"] = None
            z["soil_temperature_c"] = None

        elif condition_type == "device_offline":
            z["device_status"] = "offline"
            z["last_seen_iso"] = (now - timedelta(days=4)).isoformat()

        elif condition_type == "conflicting_timestamps":
            z["nitrogen_timestamp_iso"] = (now - timedelta(days=5)).isoformat()
            z["potassium_timestamp_iso"] = now.isoformat()

        return {
            "status": "ok",
            "zone_id": target_zone,
            "condition_applied": condition_type,
            "profile": self.get_canonical_soil_profile(target_zone).model_dump(),
        }

    def reset_demo_dataset(self) -> None:
        """Resets simulated farm data back to baseline initial state."""
        self._init_default_data()


# Global singleton instance of TelemetryService
telemetry_service = TelemetryService()
