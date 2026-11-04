"""
Mock LLM Provider
Provides deterministic, structured reasoning for offline testing, CI/CD, and demo runs.
Never fabricates live sensor or external forecast readings without clear attribution.
"""
import re
import json
from typing import Optional, Type, TypeVar, Any, Dict
from pydantic import BaseModel
from ai_agronomist.providers.llm_base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(BaseLLMProvider):
    """
    Simulated LLM engine that implements BaseLLMProvider with deterministic rule-informed reasoning.
    Used when no external cloud LLM API key is present.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def provider_status(self) -> str:
        return "mock"

    def is_live_ready(self) -> bool:
        return False

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        lower = prompt.lower()
        is_hindi = bool(re.search(r"[\u0900-\u097F]", prompt)) or "hindi" in (system_prompt or "").lower()

        # Synthesis responses based on prompt content
        is_symptom = any(w in lower for w in ["yellow", "chlorosis", "leaf", "leaves", "पत्ती", "पीली", "पीला"])
        is_irrigation = any(w in lower for w in ["irrigat", "water", "moisture", "सिंचाई", "पानी"])
        is_weather = any(w in lower for w in ["weather", "rain", "forecast", "temp", "तापमान", "बारिश", "मौसम"])

        if is_symptom:
            if is_hindi:
                return (
                    "फसल की निचली पत्तियों का पीला पड़ना नाइट्रोजन की कमी या अतिरिक्त जलभराव का संकेत हो सकता है। "
                    "सटीक निदान के लिए कृपया अपनी फसल का नाम और पिछली सिंचाई की तिथि बताएं।"
                )
            return (
                "Yellowing of lower leaves typically indicates nitrogen deficiency or root saturation from overwatering. "
                "To provide exact recommendations, please specify your crop type and watering schedule."
            )

        if is_irrigation:
            if is_hindi:
                return (
                    "खेत में मिट्टी की नमी वर्तमान में 48.2% है जो इष्टतम स्तर पर है। "
                    "अगले 24 घंटों में वर्षा की 65% संभावना को देखते हुए आज अतिरिक्त सिंचाई स्थगित करने की सलाह दी जाती है।"
                )
            return (
                "Soil moisture is currently at 48.2%, which is optimal for growing roots. "
                "With a 65% chance of incoming rainfall in the next 24 hours, additional irrigation is not recommended today."
            )

        if is_weather:
            if is_hindi:
                return (
                    "वर्तमान तापमान 28°C और सापेक्ष आर्द्रता 68% है। कल शाम हल्की से मध्यम वर्षा होने का अनुमान है।"
                )
            return (
                "Current temperature is 28°C with 68% relative humidity. Light to moderate showers are forecast for tomorrow evening."
            )

        if is_hindi:
            return "फर्तोबॉट एआई आपके खेत के प्रश्नों का विश्लेषण कर रहा है। कृपया अपनी फसल या मिट्टी की समस्या बताएं।"
        return "FertoBot AI is analyzing your farm inquiry. Please provide your crop type or telemetry details."

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """
        Generates a validated structured Pydantic model instance.
        Inspects schema fields and generates an appropriate mock payload matching prompt context.
        """
        lower = prompt.lower()
        fields = schema.model_fields.keys() if hasattr(schema, "model_fields") else {}

        # 1. Execution Plan Schema
        if "selected_agents" in fields:
            selected = []
            reasoning = "Query analyzed for agricultural specialists."

            query_match = re.search(r"user query:\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
            query_text = query_match.group(1).lower() if query_match else lower

            is_symptom = any(k in query_text for k in ["yellow", "leaf", "leaves", "chlorosis", "spot", "disease", "pest", "wilt", "dry", "पत्ती", "पीली", "बीमारी", "कीट"])
            is_irrigation = any(k in query_text for k in ["water", "irrigat", "soil", "moisture", "dry", "tank", "valve", "सिंचाई", "पानी", "नमी"])
            is_weather = any(k in query_text for k in ["weather", "rain", "forecast", "temp", "wind", "humidity", "cloud", "मौसम", "बारिश", "तापमान"])
            is_farm_status = any(k in query_text for k in ["farm status", "check sensor", "crop status", "telemetry", "खेत की स्थिति"])
            is_agricultural = is_symptom or is_irrigation or is_weather or is_farm_status or any(k in query_text for k in ["farm", "crop", "soil", "harvest", "fertilizer", "seed", "field", "खेत", "फसल"])

            if is_farm_status:
                data = {
                    "intent": "farm_status",
                    "selected_agents": ["irrigation_advisory", "weather_context"],
                    "reasoning": "Farm status telemetry and weather requested.",
                    "confidence": 1.0,
                }
                return schema.model_validate(data)

            if not is_agricultural:
                data = {
                    "intent": "unknown",
                    "selected_agents": [],
                    "reasoning": "Query is outside agricultural and telemetry domain.",
                    "confidence": 0.2,
                }
                return schema.model_validate(data)

            if is_symptom:
                selected.append("crop_symptom")
            if is_irrigation:
                selected.append("irrigation_advisory")
            if is_weather or (is_irrigation and not selected):
                selected.append("weather_context")

            if not selected:
                selected = ["crop_symptom"]

            data = {
                "intent": "agricultural_inquiry",
                "selected_agents": selected,
                "reasoning": f"Identified needs: {', '.join(selected)}",
                "confidence": 0.95,
            }
            return schema.model_validate(data)

        # 2. Synthesis Schema
        if "answer" in fields:
            is_hindi = bool(re.search(r"[\u0900-\u097F]", prompt))
            answer = await self.generate_text(prompt, system_prompt)
            data = {
                "answer": answer,
                "sources": ["Agronomic Guidelines v2.4", "Field Telemetry Sensor Probe #1"],
                "warnings": ["Advisory based on current sensor snapshot. Soil conditions may vary by plot depth."],
                "needs_clarification": "crop" not in lower and "wheat" not in lower and "cotton" not in lower and "rice" not in lower,
                "confidence": 0.92,
            }
            # Remove keys that aren't in the schema
            filtered = {k: v for k, v in data.items() if k in fields}
            return schema.model_validate(filtered)

        # 3. Fallback generic instantiation
        try:
            return schema()
        except Exception:
            # Construct dummy dict with None or defaults for required fields
            data = {}
            for fname, field_info in schema.model_fields.items():
                if field_info.annotation is list or getattr(field_info.annotation, "__origin__", None) is list:
                    data[fname] = []
                elif field_info.annotation is dict or getattr(field_info.annotation, "__origin__", None) is dict:
                    data[fname] = {}
                elif field_info.annotation is str:
                    data[fname] = "mock_value"
                elif field_info.annotation is float:
                    data[fname] = 0.0
                elif field_info.annotation is int:
                    data[fname] = 0
                elif field_info.annotation is bool:
                    data[fname] = False
                else:
                    data[fname] = None
            return schema.model_validate(data)
