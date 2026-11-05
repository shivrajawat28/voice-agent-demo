"""
Base Telemetry Provider Interface for FertoBot AI Agronomist

Defines the formal contract for retrieving soil sensor readings, historical trends,
zone metadata, and device status.

INTEGRATION NOTE FOR OFFICIAL FERTOBOT TEAM:
To connect the AI Agronomist to the official FertoBot platform:
1. Subclass `BaseTelemetryProvider` (e.g. `FertoBotProductionTelemetryProvider`).
2. Implement all abstract methods using your PostgreSQL/MongoDB database models or live Modbus/MQTT gateway.
3. Inject your provider into the AI Agronomist service container.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class BaseTelemetryProvider(ABC):
    """
    Abstract contract for agricultural telemetry sources.
    Both simulated (demo) and physical (production) telemetry adapters
    must implement this interface to be utilized by the AI Agronomist specialist agents.
    """

    @abstractmethod
    def get_farm_overview(self) -> Dict[str, Any]:
        """
        Returns high-level summary of the entire farm, including all active zones,
        current overall status, and main water reservoir telemetry.
        """
        pass

    @abstractmethod
    def get_active_zone_id(self) -> str:
        """Returns the default or currently selected active zone ID."""
        pass

    @abstractmethod
    def set_active_zone_id(self, zone_id: str) -> bool:
        """Updates the currently selected active zone ID."""
        pass

    @abstractmethod
    def get_zone(self, zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns metadata for the requested zone (crop, variety, soil type, coordinates)."""
        pass

    @abstractmethod
    def get_latest_telemetry(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns the most recent 7-in-1 soil probe reading for the specified zone:
        - Soil moisture (%)
        - Soil temperature (°C)
        - Electrical conductivity (dS/m)
        - Soil pH
        - Nitrogen (mg/kg)
        - Phosphorus (mg/kg)
        - Potassium (mg/kg)
        - Sensor calibration, quality flags, and reading timestamps
        """
        pass

    @abstractmethod
    def get_historical_telemetry(
        self,
        zone_id: Optional[str] = None,
        parameter: str = "soil_moisture_pct",
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Returns time-series historical records for the specified parameter and time window."""
        pass

    @abstractmethod
    def get_fertilizer_consumption(
        self,
        zone_id: Optional[str] = None,
        window: str = "24h",
    ) -> Dict[str, Any]:
        """
        Returns fertilizer consumption data if physical flow meters exist,
        or explicitly flags volumetric tracking as unavailable.
        """
        pass

    @abstractmethod
    def calculate_nutrient_depletion_rate(
        self,
        zone_id: Optional[str] = None,
        nutrient: str = "nitrogen",
        window_days: int = 7,
    ) -> Dict[str, Any]:
        """Calculates nutrient depletion rate from historical timestamped readings."""
        pass

    @abstractmethod
    def get_device_status(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns probe hardware health, battery level, RSSI, and last-seen timestamp."""
        pass

    @abstractmethod
    def get_water_tank_level(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns main irrigation reservoir level percentage and capacity."""
        pass

    @abstractmethod
    def get_alert_history(self, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns active agronomic and hardware alerts for the zone or farm."""
        pass

    @property
    def is_simulation(self) -> bool:
        """Returns True if the provider operates in demo/simulated mode, False for live production."""
        return True

    def get_canonical_soil_profile(self, zone_id: Optional[str] = None) -> Any:
        """Returns canonical 7-parameter profile with calibration status and health index."""
        pass

    def get_sodium_status(self) -> Dict[str, Any]:
        """Confirms that sodium is not measured by 7-in-1 sensor probes."""
        return {
            "sodium_measured": False,
            "can_derive_from_ec": False,
            "policy": "FertoBot 7-in-1 sensor does not measure sodium directly or indirectly.",
        }

    def reset_demo_dataset(self) -> None:
        """Resets telemetry state (no-op in live production)."""
        pass

