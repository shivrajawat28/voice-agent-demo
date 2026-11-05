"""
Sample FastAPI Host Application for FertoBot AI Agronomist
-----------------------------------------------------------
This executable example demonstrates how the official FertoBot platform
can integrate the standalone AI Agronomist module:

1. Install the package:
   pip install -e backend/

2. Run this sample host:
   python sample_host_app.py

3. Open in browser:
   http://127.0.0.1:8000/docs
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import from the self-contained ai_agronomist package
from ai_agronomist import (
    ai_agronomist_router,
    BaseTelemetryProvider,
    set_global_telemetry_provider,
)

# 1. Initialize host platform FastAPI application
app = FastAPI(
    title="Official FertoBot Platform (Sample Host)",
    version="1.0.0",
    description="Host application demonstrating AI Agronomist pluggable integration.",
)

# 2. Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount the AI Agronomist router under /api
# This registers all 31 endpoints, including /api/chat and WebSocket /api/ws/stt
app.include_router(ai_agronomist_router, prefix="/api")


# 4. Optional: Implement custom telemetry adapter for your platform database
class PlatformPostgresTelemetryAdapter(BaseTelemetryProvider):
    """
    Example telemetry adapter querying the official FertoBot database.
    Implement the BaseTelemetryProvider interface to connect live data.
    """
    def get_latest_telemetry(self, zone_id: str = "DEMO-ZONE-001") -> dict:
        # Replace with live database query:
        # e.g., db.session.query(SensorReading).filter_by(zone_id=zone_id).first()
        return {
            "farm_id": "FERTOBOT-FARM-01",
            "zone_id": zone_id,
            "crop": "Wheat",
            "soil_moisture_pct": 32.4,
            "soil_temperature_c": 24.1,
            "ambient_humidity_pct": 58.0,
            "nitrogen_mg_kg": 42.0,
            "phosphorus_mg_kg": 28.5,
            "potassium_mg_kg": 185.0,
            "ph": 6.8,
            "electrical_conductivity_ds_m": 1.2,
            "device_status": "ONLINE",
            "battery_level_pct": 94.0,
            "water_tank_level_pct": 82.0,
            "reading_timestamp_iso": "2026-11-04T12:00:00+05:30",
        }


# Register custom telemetry provider during startup (uncomment to activate):
# set_global_telemetry_provider(PlatformPostgresTelemetryAdapter())


@app.get("/")
async def root():
    return {
        "platform": "FertoBot Official Platform",
        "status": "online",
        "ai_agronomist_docs": "/docs",
        "health_check": "/api/health",
        "chat_endpoint": "/api/chat",
        "streaming_ws": "/api/ws/stt",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
