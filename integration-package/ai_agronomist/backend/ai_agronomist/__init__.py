"""
FertoBot AI Agronomist - Standalone Integration Package
Autonomous agricultural advisory powered by Google Gemini Multi-Agent Orchestration
and GNANI Indic Voice.
"""
from .api.router import ai_agronomist_router
from .services.telemetry_service import (
    get_telemetry_provider,
    get_global_telemetry_provider,
    set_global_telemetry_provider,
    reset_global_telemetry_provider,
    telemetry_service,
)
from .providers.telemetry_base import BaseTelemetryProvider
from .services.orchestrator import orchestrator
from .services.pump_control_service import pump_control_service

__all__ = [
    "ai_agronomist_router",
    "get_telemetry_provider",
    "get_global_telemetry_provider",
    "set_global_telemetry_provider",
    "reset_global_telemetry_provider",
    "BaseTelemetryProvider",
    "telemetry_service",
    "orchestrator",
    "pump_control_service",
]
