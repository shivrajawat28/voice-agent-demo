"""
Mock LLM Provider for unit testing and offline development.
Simulates realistic Gemini agricultural reasoning outputs with strict schema compliance.
"""

import re
from typing import Type, TypeVar, Optional, List
from pydantic import BaseModel
from app.providers.llm_base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministically simulates the Google GenAI / Gemini responses
    using offline regex parsing and pre-calibrated agricultural knowledge.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-agronomist-v1"

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
        # Extract user query if embedded in a larger prompt
        query_text = prompt
        m = re.search(r"(?:user question|user query|analyze user query):\s*['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
        if m:
            query_text = m.group(1)

        lower = query_text.lower()
        is_hindi = bool(re.search(r"[\u0900-\u097F]", query_text)) or "hindi" in (system_prompt or "").lower()

        # Topic detection for synthesis
        is_soil_improvement = (
            any(w in lower for w in ["sudhar", "upay", "amendment", "lime", "gypsum"])
            or any(w in query_text for w in ["सुधार", "उपाय", "सुधार उपाय", "जिप्सम", "चूना"])
        ) and (
            any(w in lower for w in ["ph", "soil", "mitti"])
            or any(w in query_text for w in ["पीएच", "मिट्टी", "ph"])
        )
        is_fertilizer_quantity = (
            any(w in lower for w in ["urea", "dap", "यूरिया", "डीएपी"])
            or any(w in lower for w in ["matra", "quantity", "dosage", "dose", "मात्रा", "सही मात्रा"])
            or ("fertilizer" in lower and any(w in lower for w in ["amount", "dose", "rate", "quantity", "sahi"]))
        )
        is_maize = any(w in lower for w in ["maize", "makka", "मक्का", "मक्के", "corn"])
        is_wheat_first_irrigation = (
            any(w in lower for w in ["first irrigation", "pehli sinchai", "पहली सिंचाई", "पहला पानी", "1st irrigation"])
            or (any(w in query_text for w in ["कब करें", "कब दें", "timing", "schedule"]) and any(w in lower for w in ["irrigation", "sinchai", "water", "पानी", "सिंचाई"]))
        )
        is_spray = any(w in lower for w in ["spray", "pesticide"]) or any(w in query_text for w in ["छिड़काव", "स्प्रे", "कीटनाशक"])
        is_symptom = any(w in lower for w in ["yellow", "chlorosis", "leaf", "leaves", "पत्ती", "पीली", "पीला"])
        is_irrigation = any(w in lower for w in ["irrigat", "water", "moisture", "सिंचाई", "पानी"])
        is_weather = any(w in lower for w in ["weather", "rain", "forecast", "temp", "तापमान", "बारिश", "मौसम"])
        is_device_health = any(w in lower for w in ["battery", "device", "probe", "hardware", "online", "kharab", "fault"]) or any(w in query_text for w in ["बैटरी", "डिवाइस", "सेंसर", "ऑनलाइन", "खराब", "खराबी"])
        is_water_tank = any(w in lower for w in ["tank", "reservoir", "storage", "tanki"]) or any(w in query_text for w in ["टंकी", "टैंक"])

        if is_soil_improvement:
            if "unavailable" in lower or "missing" in lower or "उपलब्ध नहीं" in prompt or "अमान्य" in prompt:
                if is_hindi:
                    return (
                        "वर्तमान में इस खेत/ज़ोन के लिए मिट्टी का वैध pH मान उपलब्ध नहीं है। "
                        "बिना अधिकृत प्रयोगशाला परीक्षण के किसी रासायनिक सुधारक (जैसे चूना या जिप्सम) का उपयोग न करें। "
                        "मिट्टी की संरचना व उर्वरता बनाए रखने के लिए गोबर की खाद या कम्पोस्ट का उपयोग एक सामान्य सलाह है, जिसकी निश्चित मात्रा मृदा स्वास्थ्य कार्ड से जांचें।"
                    )
                return (
                    "A valid soil pH reading is currently unavailable for this zone. "
                    "Chemical soil amendments like lime or gypsum must never be applied without a certified laboratory soil test. "
                    "General organic matter additions help maintain soil buffering, with quantitative rates determined by a Soil Health Card."
                )
            if is_hindi:
                return (
                    "मिट्टी का वर्तमान pH मान 6.8 है जो अधिकांश फसलों के लिए आदर्श व तटस्थ (Neutral) स्तर है। "
                    "इस pH पर किसी रासायनिक सुधारक (जैसे जिप्सम या चूना) की आवश्यकता नहीं है। "
                    "मिट्टी की उर्वरता, जैविक कार्बन और संरचना को बनाए रखने के लिए अच्छी सड़ी गोबर की खाद (FYM) या कम्पोस्ट मिलाना एक सामान्य कृषि उपाय है। "
                    "खाद की निश्चित मात्रा मिट्टी में जैविक कार्बन (Organic Carbon), फसल की किस्म और मिट्टी की बनावट पर निर्भर करती है, जिसके लिए मृदा स्वास्थ्य कार्ड की जांच करें। "
                    "रासायनिक सुधारकों (जैसे चूना या जिप्सम) का प्रयोग केवल लैब टेस्ट में गंभीर अम्लता या क्षारीयता पाए जाने पर ही किया जाता है।"
                )
            return (
                "Current soil pH is 6.8, which is in the optimal near-neutral range for crops. "
                "Chemical soil amendments such as lime or gypsum are not required at this pH level. "
                "To maintain soil fertility and buffering capacity, incorporating well-decomposed organic manure or compost is recommended as general guidance. "
                "Quantitative application rates depend on baseline soil organic carbon, soil texture, and crop requirements from a certified Soil Health Card. "
                "Chemical amendments are only applied when verified by laboratory soil testing for acidic or alkaline conditions."
            )

        if is_fertilizer_quantity:
            if is_hindi:
                return (
                    "फसल के लिए बिना मिट्टी परीक्षण और फसल अवस्था जाने यूरिया और डीएपी की निश्चित मात्रा तय करना वैज्ञानिक रूप से सुरक्षित नहीं है। "
                    "सिद्धांततः डीएपी बुवाई के समय बेसल डोज के रूप में जड़ों के विकास के लिए दिया जाता है, जबकि यूरिया को 2 से 3 भागों में बांटकर दिया जाता है ताकि लीचिंग न हो। "
                    "सटीक मात्रा की सिफारिश के लिए कृपया अपनी फसल का नाम, फसल की अवस्था और खेत का क्षेत्रफल बताएं।"
                )
            return (
                "Prescribing a fixed universal dosage of Urea and DAP without establishing crop growth stage and soil test results is agronomically unsafe. "
                "Agronomically, DAP is applied at sowing as a basal dose for early root architecture development, while Urea is split into 2-3 applications to prevent nitrogen leaching. "
                "To provide an accurate recommendation, please specify: which crop are you growing, its current growth stage, and your plot size or soil-test report."
            )

        if is_maize:
            if is_hindi:
                return (
                    "मक्का आपके खेत के पंजीकृत सेंसर ज़ोन में नहीं है (सेंसर ज़ोन गेहूं, कपास, टमाटर और सरसों के हैं)। "
                    "आपके द्वारा बताई गई 40% नमी किसान-प्रदत्त रीडिंग है। केवल नमी के प्रतिशत से सिंचाई का पक्का निर्णय नहीं लिया जा सकता, "
                    "क्योंकि यह मिट्टी की बनावट (हल्की बलुई या भारी दोमट) और फसल की अवस्था पर निर्भर करता है। "
                    "मक्का में मंजर निकलने (tasseling) और सिल्क निकलने (silking) के समय नमी की कमी सर्वाधिक नुकसान पहुंचाती है। "
                    "खेत में जलभराव बिल्कुल न होने दें। सटीक सलाह के लिए कृपया अपनी मिट्टी का प्रकार और मक्का की वर्तमान अवस्था बताएं।"
                )
            return (
                "Maize is not registered in any monitored sensor zone on your farm (farm zones: Zone 1 Wheat, Zone 2 Cotton, Zone 3 Tomato, Zone 4 Mustard). "
                "The 40% soil moisture cited represents farmer-provided input rather than calibrated on-farm telemetry. "
                "A moisture percentage alone cannot dictate irrigation without establishing soil texture, root-zone depth, and growth stage. "
                "Moisture deficits are most critical during flowering stages—tasseling and silking—while ensuring proper furrow drainage as maize cannot tolerate standing water. "
                "Please share your soil texture and crop stage for a specific recommendation."
            )

        if is_wheat_first_irrigation:
            if is_hindi:
                return (
                    "गेहूं में पहली सिंचाई सामान्यतः 'ताज मूल अवस्था' (CRI - Crown Root Initiation) पर की जाती है, जो अनुकूल परिस्थितियों में प्रायः बुवाई के 20 से 25 दिन बाद आती है। "
                    "हालांकि, यह समय बुवाई की गहराई और तापमान के अनुसार बदल सकता है। वैज्ञानिक अध्ययनों के अनुसार क्राउन जड़ें बनते समय गंभीर सूखे से पैदावार में 30 से 40 प्रतिशत तक की कमी का जोखिम हो सकता है। "
                    "फ़र्टोबॉट सेंसर बुवाई की तारीख ट्रैक नहीं करते, लेकिन वर्तमान में आपके गेहूं खेत (Zone 1) में मिट्टी की नमी 48.2% है। "
                    "पौधों के आधार पर ताज जड़ों की जांच करें और यदि ऊपरी मिट्टी सूखी लगे तो हल्की सिंचाई करें।"
                )
            return (
                "In wheat, the first irrigation is typically scheduled at Crown Root Initiation (CRI), which under standard conditions generally occurs around 20 to 25 days after sowing (DAS). "
                "However, exact timing varies with sowing depth, ambient temperature, and variety. Severe moisture deficit during crown root establishment risks potential yield penalties of up to 30% to 40% in literature. "
                "While FertoBot sensors monitor soil moisture (currently 48.2% in Zone 1 Wheat), they do not track calendar sowing dates. "
                "Inspect crown roots at the shoot base: if crown roots have initiated and the topsoil is dry, apply a light to moderate irrigation."
            )

        if is_spray:
            if is_hindi:
                return "वर्तमान मौसम विश्लेषण: हवा की गति 12 km/h है और अगले 24 घंटों में वर्षा की 65% संभावना है। अतः बारिश के कारण रासायनिक छिड़काव अभी स्थगित रखें।"
            return "Weather analysis: Wind speed is 12 km/h with a 65% chance of rainfall in the next 24 hours. Foliar chemical spraying should be postponed due to wash-off risk."

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
            # Check if Zone 3 / Tomato salinity check is needed
            if any(w in query_text.lower() for w in ["zone 3", "ज़ोन 3", "टमाटर", "tomato"]) or "zone-003" in prompt.lower() or "zone 3" in prompt.lower():
                if is_hindi:
                    return (
                        "टमाटर ज़ोन 3 में मिट्टी की नमी 64.5% (अधिक) और विद्युत चालकता (EC) 2.4 dS/m (उच्च लवणता जोखिम) है। "
                        "जड़ों में लवणता और परासरणी तनाव (osmotic stress) से बचाव के लिए अभी सिंचाई तुरंत रोकें।"
                    )
                return (
                    "In Tomato Zone 3, soil moisture is high at 64.5% and electrical conductivity (EC) is elevated at 2.4 dS/m indicating salinity stress. "
                    "Irrigation should be stopped immediately to avoid osmotic stress and root asphyxiation."
                )

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

        if is_device_health:
            if is_hindi:
                return "आपके खेत का फर्तोबॉट डिवाइस DEMO-DEVICE-001 ऑनलाइन है और बैटरी 92% है। सभी हार्डवेयर डिवाइस सही तरीके से काम कर रहे हैं।"
            return "Your FertoBot probe DEMO-DEVICE-001 is online with battery at 92%. All hardware devices are operational."

        if is_water_tank:
            if is_hindi:
                return "पानी के टैंक में वर्तमान जल स्तर 82% है। पानी का भंडारण पर्याप्त है।"
            return "Water tank reservoir level is currently at 82%. Storage is adequate."

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

            # Explicit Intent Resolution
            is_soil_improvement = (
                any(k in query_text for k in ["sudhar", "upay", "amendment", "lime", "gypsum", "सुधार", "उपाय", "जिप्सम", "चूना"])
                and any(k in query_text for k in ["ph", "soil", "mitti", "पीएच", "मिट्टी"])
            )
            is_soil_ph_query = any(k in query_text for k in ["ph", "पीएच"]) and not is_soil_improvement
            is_fertilizer_quantity = (
                any(k in query_text for k in ["urea", "dap", "यूरिया", "डीएपी"])
                or any(k in query_text for k in ["matra", "quantity", "dosage", "dose", "मात्रा", "सही मात्रा"])
                or ("fertilizer" in query_text and any(k in query_text for k in ["amount", "dose", "rate", "quantity", "sahi"]))
            )
            is_fertilizer_recommendation = (
                any(k in query_text for k in ["fertilizer", "khad", "उर्वरक", "खाद"])
                and any(k in query_text for k in ["recommend", "salah", "kaunsi", "which", "सिफारिश"])
                and not is_fertilizer_quantity
            )
            is_irrigation_timing = (
                any(k in query_text for k in ["first irrigation", "pehli sinchai", "पहली सिंचाई", "पहला पानी", "1st irrigation"])
                or (any(k in query_text for k in ["कब करें", "kab kare", "timing", "schedule"]) and any(k in query_text for k in ["irrigation", "sinchai", "water", "पानी", "सिंचाई"]))
            )
            is_irrigation_quantity = any(k in query_text for k in ["how much water", "kitna pani", "कितना पानी", "irrigation depth", "water quantity"])
            is_irrigation_advisory = any(k in query_text for k in ["water", "irrigat", "moisture", "सिंचाई", "पानी", "नमी"]) and not (is_irrigation_timing or is_irrigation_quantity)
            is_symptom = any(k in query_text for k in ["yellow", "leaf", "leaves", "chlorosis", "spot", "disease", "pest", "wilt", "dry", "पत्ती", "पीली", "बीमारी", "कीट"])
            is_weather = any(k in query_text for k in ["weather", "rain", "forecast", "temp", "wind", "humidity", "cloud", "मौसम", "बारिश", "तापमान"])
            is_spray = any(k in query_text for k in ["spray", "pesticide", "छिड़काव", "स्प्रे", "कीटनाशक"])
            is_device_health = any(k in query_text for k in ["battery", "device", "probe", "hardware", "online", "बैटरी", "डिवाइस", "सेंसर"])
            is_water_tank = any(k in query_text for k in ["tank", "reservoir", "storage", "टंकी"])
            is_general_agronomy = any(k in query_text for k in ["rotation", "organic", "testing", "soil test", "suitab", "uga sakte", "फसल चक्र", "जैविक", "परीक्षण"])

            is_farm_status = any(k in query_text for k in ["farm status", "check sensor", "crop status", "telemetry", "खेत की स्थिति"])
            is_agricultural = (
                is_soil_improvement or is_soil_ph_query or is_fertilizer_quantity or is_fertilizer_recommendation
                or is_irrigation_timing or is_irrigation_quantity or is_irrigation_advisory or is_symptom
                or is_weather or is_spray or is_device_health or is_water_tank or is_general_agronomy or is_farm_status
                or any(k in query_text for k in ["farm", "crop", "soil", "harvest", "seed", "field", "खेत", "फसल"])
            )

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

            # Assign strict intent & specialist agent
            if is_soil_improvement:
                assigned_intent = "soil_improvement"
                selected = ["crop_symptom"]
            elif is_fertilizer_quantity:
                assigned_intent = "fertilizer_quantity"
                selected = ["crop_symptom"]
            elif is_fertilizer_recommendation:
                assigned_intent = "fertilizer_recommendation"
                selected = ["crop_symptom"]
            elif is_soil_ph_query:
                assigned_intent = "soil_ph_query"
                selected = ["crop_symptom"]
            elif is_irrigation_timing:
                assigned_intent = "irrigation_timing"
                selected = ["irrigation_advisory"]
            elif is_irrigation_quantity:
                assigned_intent = "irrigation_quantity"
                selected = ["irrigation_advisory"]
            elif is_irrigation_advisory:
                assigned_intent = "irrigation_advisory"
                selected = ["irrigation_advisory", "weather_context"]
            elif is_symptom:
                assigned_intent = "crop_symptom"
                selected = ["crop_symptom"]
            elif is_weather or is_spray:
                assigned_intent = "weather_query"
                selected = ["weather_context"]
            elif is_device_health:
                assigned_intent = "device_health"
                selected = ["device_health"]
            elif is_water_tank:
                assigned_intent = "water_tank_query"
                selected = ["device_health"]
            elif is_general_agronomy:
                assigned_intent = "general_agronomy"
                selected = ["crop_symptom"]
            else:
                assigned_intent = "general_agronomy"
                selected = ["crop_symptom"]

            data = {
                "intent": assigned_intent,
                "selected_agents": selected,
                "reasoning": f"Specialist dispatch: {assigned_intent} -> [{', '.join(selected)}]",
                "confidence": 0.95,
            }
            return schema.model_validate(data)

        # 2. Synthesis Schema
        if "answer" in fields:
            is_hindi = bool(re.search(r"[\u0900-\u097F]", prompt))
            answer = await self.generate_text(prompt, system_prompt)

            # Check if query is fertilizer quantity or missing crop context
            query_match = re.search(r"(?:user question|user query):\s*['\"]([^'\"]+)['\"]", prompt, re.IGNORECASE)
            q_text = query_match.group(1).lower() if query_match else prompt.lower()

            is_fert_dosage = (
                any(k in q_text for k in ["urea", "dap", "यूरिया", "डीएपी"])
                or any(k in q_text for k in ["matra", "quantity", "dosage", "dose", "मात्रा", "सही मात्रा"])
                or "fertilizer_quantity" in prompt.lower()
            )
            has_crop_in_context = any(c in prompt.lower() for c in ["wheat", "cotton", "tomato", "mustard", "गेहूं", "कपास", "टमाटर", "सरसों", "zone-001", "zone-002", "zone-003", "zone-004", "demo-zone-001", "demo-zone-002", "demo-zone-003", "demo-zone-004"])

            if is_fert_dosage:
                needs_clarification = True
                clarification_prompt = (
                    "सटीक सिफारिश के लिए कृपया अपनी फसल का नाम, फसल की अवस्था और खेत का क्षेत्रफल बताएं।"
                    if is_hindi else
                    "Please specify your crop species, current growth stage, and plot acreage for an accurate recommendation."
                )
            elif not has_crop_in_context:
                needs_clarification = True
                clarification_prompt = "कृपया अपनी फसल का नाम बताएं।" if is_hindi else "Please specify your crop type."
            else:
                needs_clarification = False
                clarification_prompt = None

            data = {
                "answer": answer,
                "sources": ["Agronomic Diagnostic Knowledgebase v3.0", "Field Telemetry Sensor Monitor"],
                "warnings": ["Advisory based on current sensor snapshot. Soil conditions may vary by plot depth."],
                "needs_clarification": needs_clarification,
                "clarification_prompt": clarification_prompt,
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
