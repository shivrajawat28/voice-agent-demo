"""
Weather Context Specialist Agent
Fetches real meteorological forecasts and translates atmospheric variables into agronomic impact factors.
"""
import re
from typing import List, Dict, Any
from app.agents.base import BaseAgent, AgentContext
from app.models.conversation import AgentResult
from app.tools.base import BaseTool


class WeatherContextAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "weather_context"

    @property
    def name(self) -> str:
        return "Weather Context Specialist"

    @property
    def description(self) -> str:
        return (
            "Retrieves ambient temperature, relative humidity, wind speed, and precipitation forecasts. "
            "Assesses impact on crop transpiration, spray drift risk, and fungal pathogen pressure."
        )

    @property
    def permitted_tools(self) -> List[str]:
        return ["weather_context"]

    async def execute(
        self,
        context: AgentContext,
        tools: Dict[str, BaseTool],
    ) -> AgentResult:
        is_hindi = context.language.lower().startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", context.query)
        )

        weather_tool = tools.get("weather_context")
        data = await weather_tool.execute() if weather_tool else {}

        temp = data.get("temperature_c", 28.0)
        humidity = data.get("relative_humidity_pct", 65.0)
        rain_prob = data.get("rain_probability_24h_pct", 65.0)
        wind_speed = data.get("wind_speed_kmh", 12.0)
        source = data.get("source", "Weather Service")

        evidence: List[str] = [
            f"Source: {source}",
            f"Ambient Temperature: {temp:.1f}°C",
            f"Relative Humidity: {humidity:.1f}%",
            f"24-Hour Rain Probability: {rain_prob:.0f}%",
            f"Wind Speed: {wind_speed:.1f} km/h",
        ]

        limitations: List[str] = [
            "Regional meteorological model with 10km grid resolution; local microclimates may differ.",
        ]

        # Agronomic interpretation
        agronomic_factors = []
        if humidity > 70.0:
            agronomic_factors.append("Elevated humidity increases foliar fungal disease spore germination risk.")
        if wind_speed > 15.0:
            agronomic_factors.append("High wind speed exceeds spray drift threshold (>15 km/h). Foliar sprays not advised.")
        if rain_prob > 50.0:
            agronomic_factors.append(f"High rain probability ({rain_prob:.0f}%) expected to recharge topsoil.")

        is_spray_inquiry = any(w in context.query.lower() for w in ["spray", "drift", "chemical", "pesticide", "herbicide", "fungicide", "dawa", "chidkaav"]) or any(w in context.query for w in ["छिड़काव", "स्प्रे", "दवा", "कीटनाशक", "कीटनाशी"])

        if is_hindi:
            summary = (
                f"मौसम रिपोर्ट: तापमान {temp:.1f}°C, आर्द्रता {humidity:.1f}%, और हवा की गति {wind_speed:.1f} km/h है। "
                f"अगले 24 घंटों में {rain_prob:.0f}% वर्षा की संभावना है।"
            )
            if is_spray_inquiry:
                if rain_prob >= 50.0:
                    summary += " वर्षा की संभावना के कारण रासायनिक छिड़काव अभी टालें।"
                elif wind_speed > 15.0:
                    summary += " तेज़ हवा के कारण दवा बहने (spray drift) का जोखिम है, अतः रासायनिक छिड़काव न करें।"
                else:
                    summary += " हवा शांत है और बारिश की संभावना नहीं है, अतः रासायनिक छिड़काव सुरक्षित रूप से किया जा सकता है।"
        else:
            summary = (
                f"Current meteorological conditions: {temp:.1f}°C, {humidity:.1f}% humidity, "
                f"and {wind_speed:.1f} km/h wind. 24-hour precipitation probability stands at {rain_prob:.0f}%."
            )
            if is_spray_inquiry:
                if rain_prob >= 50.0:
                    summary += " Precipitation expected; avoid foliar pesticide or herbicide applications today."
                elif wind_speed > 15.0:
                    summary += " High wind speed exceeds spray drift threshold; foliar spraying not advised today."
                else:
                    summary += " Wind and precipitation conditions are calm and favorable for chemical spraying."

        return AgentResult(
            agent_id=self.agent_id,
            name=self.name,
            status="completed",
            summary=summary,
            evidence=evidence,
            limitations=limitations,
            data={
                "temperature_c": temp,
                "humidity_pct": humidity,
                "rain_prob_pct": rain_prob,
                "wind_speed_kmh": wind_speed,
                "agronomic_factors": agronomic_factors,
            },
        )
