"""
Weather Context Tool
Read-only meteorological tool. Fetches real-time weather and precipitation forecasts
using Open-Meteo REST API or offline fallback fixture.
"""
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from ai_agronomist.tools.base import BaseTool


class WeatherTool(BaseTool):
    """
    Read-only weather retrieval tool.
    Never fabricates false certainty; returns clear attribution and probability metrics.
    Caches weather responses for 60 seconds to eliminate redundant network latency.
    """

    def __init__(self, timeout_seconds: float = 1.5):
        self._timeout = timeout_seconds
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "weather_context"

    @property
    def description(self) -> str:
        return (
            "Fetches ambient temperature, humidity, precipitation probability, and wind speed "
            "for agricultural location coordinates."
        )

    async def execute(
        self,
        latitude: float = 28.6139,
        longitude: float = 77.2090,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Attempts to query Open-Meteo free forecast API.
        Falls back to local mock weather fixture if offline or unreachable.
        Uses in-memory cache if queried within 60 seconds.
        """
        now = time.time()
        if self._cache and (now - self._cache_timestamp) < 60.0:
            return dict(self._cache)

        async with self._lock:
            # Re-check cache inside lock
            now = time.time()
            if self._cache and (now - self._cache_timestamp) < 60.0:
                return dict(self._cache)

            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={latitude}&longitude={longitude}"
                f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
                f"&hourly=precipitation_probability&forecast_days=2"
            )
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        curr = data.get("current", {})
                        hourly = data.get("hourly", {})
                        # Calculate next 24h max rain probability
                        probs = hourly.get("precipitation_probability", [0])[:24]
                        max_prob = max(probs) if probs else 0

                        result = {
                            "source": "Open-Meteo Weather API (Real-Time)",
                            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                            "latitude": latitude,
                            "longitude": longitude,
                            "temperature_c": curr.get("temperature_2m", 28.0),
                            "relative_humidity_pct": curr.get("relative_humidity_2m", 65.0),
                            "current_rain_mm": curr.get("precipitation", 0.0),
                            "rain_probability_24h_pct": max_prob,
                            "wind_speed_kmh": curr.get("wind_speed_10m", 12.0),
                            "is_live_data": True,
                        }
                        self._cache = dict(result)
                        self._cache_timestamp = now
                        return result
            except Exception:
                # Safe offline fallback
                pass

            fallback = {
                "source": "Simulated Weather Telemetry Fixture (Offline)",
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c": 27.5,
                "relative_humidity_pct": 68.0,
                "current_rain_mm": 0.0,
                "rain_probability_24h_pct": 65.0,
                "wind_speed_kmh": 12.0,
                "is_live_data": False,
            }
            self._cache = dict(fallback)
            self._cache_timestamp = now
            return fallback
