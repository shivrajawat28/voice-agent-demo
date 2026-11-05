"""
Canonical Seven-Parameter Soil Telemetry Schema (Phase 19)
Models the complete FertoBot 7-in-1 Modbus RS485 soil sensor dataset:
1. Nitrogen (N) [mg/kg / ppm]
2. Phosphorus (P) [mg/kg / ppm]
3. Potassium (K) [mg/kg / ppm]
4. Soil Moisture [%]
5. Soil Temperature [°C]
6. Soil pH [pH scale 0-14]
7. Electrical Conductivity (EC) [dS/m (and raw uS/cm)]

Strict Rule: Sodium (Na) is NOT measured by FertoBot 7-in-1 sensor.
Never invent sodium or derive sodium concentration from EC.
"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field


QualityStatus = Literal["VALID", "SUSPECT", "OUT_OF_RANGE", "STALE", "UNAVAILABLE"]
CalibrationStatus = Literal["CALIBRATED", "UNCALIBRATED", "CALIBRATION_EXPIRED", "UNKNOWN"]
ValidityStatus = Literal["VALID", "INVALID", "DISCONNECTED"]


class SoilParameterReading(BaseModel):
    parameter_name: str = Field(..., description="Canonical parameter key (e.g. nitrogen, soil_moisture)")
    display_name: str = Field(..., description="Human-readable English name (e.g. Nitrogen (N))")
    display_name_hi: str = Field(..., description="Human-readable Hindi name (e.g. नाइट्रोजन (N))")
    value: Optional[float] = Field(default=None, description="Current calibrated engineering value")
    raw_value: Optional[float] = Field(default=None, description="Raw sensor Modbus register value")
    unit: str = Field(..., description="Engineering measurement unit (e.g. mg/kg, %, °C, pH, dS/m)")
    raw_unit: Optional[str] = Field(default=None, description="Raw hardware unit (e.g. uS/cm for EC)")
    timestamp_iso: str = Field(..., description="ISO 8601 reading timestamp")
    sensor_id: str = Field(..., description="Physical/simulated sensor channel ID")
    device_id: str = Field(..., description="Probe/Hardware board identifier")
    farm_id: str = Field(default="DEMO-FARM-001", description="Farm identifier")
    zone_id: str = Field(..., description="Target agricultural zone identifier")
    data_source: str = Field(default="SIMULATED", description="'SIMULATED' or 'LIVE'")
    quality_status: QualityStatus = Field(default="VALID", description="Data quality classification")
    calibration_status: CalibrationStatus = Field(default="CALIBRATED", description="Calibration assurance status")
    validity_status: ValidityStatus = Field(default="VALID", description="Physical validity / connection state")
    agricultural_relevance: str = Field(..., description="Agronomic function and plant physiology relevance")
    crop_reference_range: Optional[str] = Field(default=None, description="Crop-specific reference benchmark")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class CanonicalSoilProfile(BaseModel):
    farm_id: str = Field(default="DEMO-FARM-001")
    farm_name: str = Field(default="Green Valley Agro Farm (Malwa Region)")
    farmer_name: str = Field(default="Ramesh Patel")
    zone_id: str = Field(..., description="Target zone identifier (e.g. DEMO-ZONE-001)")
    zone_name: str = Field(..., description="Human-readable zone title")
    crop: str = Field(..., description="Cultivated crop name")
    variety: Optional[str] = Field(default=None, description="Crop cultivar / variety")
    growth_stage: str = Field(..., description="Current crop phenological stage")
    soil_type: str = Field(..., description="Soil textural classification")
    device_id: str = Field(..., description="Associated probe device ID")
    device_status: str = Field(default="online", description="Hardware connectivity status")
    battery_level_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    water_tank_level_pct: float = Field(default=80.0, ge=0.0, le=100.0)
    last_seen_iso: str = Field(..., description="Timestamp of last probe contact")
    parameters: Dict[str, SoilParameterReading] = Field(
        ...,
        description="Dictionary mapping each of the 7 parameter names to its detailed reading",
    )
    completeness_ratio: str = Field(..., description="Availability ratio (e.g. '7/7 parameters available')")
    available_count: int = Field(..., ge=0, le=7, description="Number of valid/available parameters")
    total_count: int = Field(default=7, description="Total documented parameters (strictly 7)")
    missing_parameters: List[str] = Field(default_factory=list, description="Parameters with null/missing values")
    uncalibrated_parameters: List[str] = Field(default_factory=list, description="Parameters with uncalibrated status")
    stale_parameters: List[str] = Field(default_factory=list, description="Parameters with stale data (>24h old)")
    out_of_range_parameters: List[str] = Field(default_factory=list, description="Parameters outside physical limits")
    overall_soil_health_index: str = Field(
        default="Balanced",
        description="Overall synthesis: Balanced, Nutrient-Stressed, Moisture-Deficit, Waterlogged, Saline",
    )
    data_source: str = Field(default="SIMULATED", description="Data provenance")
    is_simulated: bool = Field(default=True, description="Safety flag indicating simulated hardware")
    actuation_permitted: bool = Field(default=False, description="Strict safety boundary flag")
    warnings: List[str] = Field(default_factory=list, description="Safety or agronomic precautions")
    confidence_limitations: List[str] = Field(default_factory=list, description="Data quality caveats")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ZoneTelemetry(BaseModel):
    farm_id: str
    farm_name: str
    farmer_name: str
    zone_id: str
    zone_name: str
    crop: str
    variety: Optional[str] = None
    growth_stage: str
    soil_type: str
    device_id: str
    device_status: str
    battery_level_pct: float
    water_tank_level_pct: float
    last_seen_iso: str
    soil_moisture_pct: Optional[float] = None
    nitrogen_mg_kg: Optional[float] = None
    phosphorus_mg_kg: Optional[float] = None
    potassium_mg_kg: Optional[float] = None
    soil_temperature_c: Optional[float] = None
    ph: Optional[float] = None
    electrical_conductivity_ds_m: Optional[float] = None
    data_source: str = "simulated"
    is_simulated: bool = True
    actuation_permitted: bool = False
    reading_timestamp_iso: str
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class HistoricalDataPoint(BaseModel):
    timestamp_iso: str
    value: float
    unit: str


class ParameterTrend(BaseModel):
    zone_id: str
    parameter: str
    unit: str
    time_range: str
    points: List[Dict[str, Any]]
    min_value: float
    max_value: float
    average_value: float
    trend_direction: str
    trend_summary: str
    data_source: str = "simulated"
    is_simulated: bool = True


class FarmAlert(BaseModel):
    alert_id: str
    farm_id: str
    zone_id: str
    device_id: str
    severity: str
    category: str
    title: str
    message: str
    timestamp_iso: str
    resolved: bool = False
    data_source: str = "simulated"
    is_simulated: bool = True


class FarmSummary(BaseModel):
    farm_id: str
    farm_name: str
    farmer_name: str
    location: str
    active_zone_id: str
    zones: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    data_source: str = "simulated"
    is_simulated: bool = True
    actuation_permitted: bool = False
