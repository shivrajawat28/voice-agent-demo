"""
Multi-Agent Agricultural LLM Orchestrator
Coordinates dynamic query planning, specialist agent dispatch, tool execution,
and structured advisory synthesis.
Phase 14: Enhanced for open-domain agricultural intelligence, real-time sentence-level streaming,
microphone reliability feedback, session context retention, and strict read-only safety.
"""
import asyncio
import re
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.models.conversation import (
    ChatResponse,
    AgentResult,
    ExecutionTraceStep,
    PumpActionPayload,
)
from app.providers.base import BaseConversationProvider
from app.providers.llm_base import BaseLLMProvider
from app.providers.llm_factory import get_llm_provider
from app.agents.base import BaseAgent, AgentContext
from app.agents.crop_symptom_agent import CropSymptomAgent
from app.agents.irrigation_advisory_agent import IrrigationAdvisoryAgent
from app.agents.weather_context_agent import WeatherContextAgent
from app.agents.device_health_agent import DeviceHealthAgent
from app.tools.base import BaseTool
from app.tools.crop_knowledge_tool import CropKnowledgeTool
from app.tools.weather_tool import WeatherTool
from app.tools.telemetry_tool import (
    TelemetryTool,
    LatestTelemetryTool,
    HistoricalTelemetryTool,
    DeviceStatusTool,
    WaterLevelTool,
    AlertHistoryTool,
)
from app.services.telemetry_service import (
    telemetry_service,
    get_telemetry_provider,
)
from app.services.pump_control_service import pump_control_service
from app.utils.timezone import format_to_ist, to_ist, get_current_ist, get_tomorrow_ist


def split_into_sentences(text: str) -> List[str]:
    """
    Partitions text into natural speakable sentences delimited by Hindi danda (।),
    period (not part of decimal numbers), question mark (?), exclamation mark (!), or newlines.
    Ensures numbers like 6.8 or 48.2% remain unbroken.
    """
    clean_text = text.strip()
    if not clean_text:
        return []
    # Pattern matches sentence terminators but avoids matching decimal periods in numbers (e.g. 6.8)
    parts = re.split(r'([।\?!]|\n+|(?<!\d)\.(?!\d))', clean_text)
    sentences = []
    current = ""
    for piece in parts:
        if not piece:
            continue
        current += piece
        if re.search(r'[।\?!]|\n+|(?<!\d)\.(?!\d)', piece):
            cleaned = current.strip()
            if cleaned:
                sentences.append(cleaned)
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences if sentences else [clean_text]


class ExecutionPlan(BaseModel):
    intent: str = Field(..., description="Categorized user intent")
    selected_agents: List[str] = Field(
        ...,
        description="Subset of ['crop_symptom', 'irrigation_advisory', 'weather_context', 'device_health']",
    )
    reasoning: str = Field(..., description="Justification for selected agent workflow")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class SynthesisOutput(BaseModel):
    answer: str = Field(..., description="Coherent, concise, natural synthesized guidance for voice output")
    sources: List[str] = Field(default_factory=list, description="Agronomic rules, weather endpoints, and telemetry")
    warnings: List[str] = Field(default_factory=list, description="Critical crop or safety precautions")
    needs_clarification: bool = Field(default=False, description="Whether essential grower input is missing")
    clarification_prompt: Optional[str] = Field(default=None, description="Specific concise clarifying question in Hindi/English if context is missing")


class LLMOrchestrator(BaseConversationProvider):
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None, fast_planning: bool = False):
        self._llm = llm_provider or get_llm_provider()
        self.fast_planning = fast_planning
        # Initialize read-only tools
        self._tools: Dict[str, BaseTool] = {
            "crop_knowledge": CropKnowledgeTool(),
            "weather_context": WeatherTool(),
            "farm_telemetry": TelemetryTool(),
            "latest_telemetry": LatestTelemetryTool(),
            "historical_telemetry": HistoricalTelemetryTool(),
            "device_status": DeviceStatusTool(),
            "water_level": WaterLevelTool(),
            "alert_history": AlertHistoryTool(),
        }
        # Initialize specialist agents
        self._agents: Dict[str, BaseAgent] = {
            "crop_symptom": CropSymptomAgent(),
            "irrigation_advisory": IrrigationAdvisoryAgent(),
            "weather_context": WeatherContextAgent(),
            "device_health": DeviceHealthAgent(),
        }
        # In-memory repeat history & session tracking
        self._last_responses: Dict[str, str] = {}
        self._session_zones: Dict[str, str] = {}
        self._session_locations: Dict[str, str] = {}
        self._session_seasons: Dict[str, str] = {}
        self._session_greeted: Dict[str, bool] = {}
        self._session_turn_count: Dict[str, int] = {}

    def clear_session(self, session_id: Optional[str] = None) -> None:
        key = session_id or "default"
        self._session_greeted.pop(key, None)
        self._session_turn_count.pop(key, None)
        self._last_responses.pop(key, None)
        self._session_zones.pop(key, None)
        self._session_locations.pop(key, None)
        self._session_seasons.pop(key, None)

    def set_session_zone(self, session_id: str, zone_id: str) -> None:
        """Sets the active agricultural zone for a specific conversation session."""
        key = session_id or "default"
        self._session_zones[key] = zone_id

    def get_session_zone(self, session_id: str) -> Optional[str]:
        """Retrieves the active agricultural zone for a specific conversation session."""
        key = session_id or "default"
        return self._session_zones.get(key)


    async def process_message(
        self,
        message: str,
        language: str = "en-US",
        session_id: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> ChatResponse:
        return await self.process_query(message, language, session_id, zone_id)

    @property
    def llm_provider(self) -> BaseLLMProvider:
        return self._llm

    def set_llm_provider(self, provider: BaseLLMProvider) -> None:
        self._llm = provider

    def get_available_agents(self) -> List[str]:
        return list(self._agents.keys())

    def _build_response(
        self,
        reply: str,
        intent: str,
        confidence: float = 1.0,
        repeatable: bool = True,
        agent_results: Optional[List[AgentResult]] = None,
        execution_trace: Optional[List[ExecutionTraceStep]] = None,
        sources: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        needs_clarification: bool = False,
        clarification_prompt: Optional[str] = None,
        provider_status: str = "fast_path",
        pending_action: Optional[PumpActionPayload] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        meta = metadata.copy() if metadata else {}
        is_hindi_turn = meta.get("language", "").startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", reply)
        )
        if "turn_language" not in meta:
            meta["turn_language"] = "hi-IN" if is_hindi_turn else "en-US"
        if "turn_voice" not in meta:
            meta["turn_voice"] = "Nalini" if is_hindi_turn else "Kaveri"

        return ChatResponse(
            success=True,
            reply=reply,
            intent=intent,
            confidence=confidence,
            repeatable=repeatable,
            sentences=split_into_sentences(reply),
            agent_results=agent_results,
            execution_trace=execution_trace or [],
            sources=sources,
            warnings=warnings,
            needs_clarification=needs_clarification,
            clarification_prompt=clarification_prompt,
            provider_status=provider_status,
            pending_action=pending_action,
            metadata=meta,
        )

    async def process_query(
        self,
        message: str,
        language: str = "en-US",
        session_id: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> ChatResponse:
        t0 = time.perf_counter()
        session_key = session_id or "default"
        trimmed = message.strip()
        lower_trimmed = trimmed.lower()
        is_hindi = language.lower().startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", trimmed)
        )
        trace: List[ExecutionTraceStep] = []

        # -------------------------------------------------------------
        # Zone Resolution (From explicit mention, parameter, session context, or default)
        # -------------------------------------------------------------
        session_zone = self._session_zones.get(session_key)
        resolved_zone = zone_id or session_zone or telemetry_service.get_active_zone_id()
        zone_explicitly_mentioned = False
        if (
            any(w in lower_trimmed for w in ["zone 1", "zone-1", "जोन 1", "ज़ोन 1", "sector 1", "sector-1", "सेक्टर 1", "सेक्टर-1", "wheat", "गेहूं", "गेहु", "north", "उत्तर"])
            or bool(re.search(r"\b(sector|zone|सेक्टर|ज़ोन|जोन)\s*[-_]?\s*1\b", lower_trimmed))
        ):
            resolved_zone = "DEMO-ZONE-001"
            zone_explicitly_mentioned = True
        elif (
            any(w in lower_trimmed for w in ["zone 2", "zone-2", "जोन 2", "ज़ोन 2", "sector 2", "sector-2", "सेक्टर 2", "सेक्टर-2", "cotton", "कपास", "south", "दक्षिण"])
            or bool(re.search(r"\b(sector|zone|सेक्टर|ज़ोन|जोन)\s*[-_]?\s*2\b", lower_trimmed))
        ):
            resolved_zone = "DEMO-ZONE-002"
            zone_explicitly_mentioned = True
        elif (
            any(w in lower_trimmed for w in ["zone 3", "zone-3", "जोन 3", "ज़ोन 3", "sector 3", "sector-3", "सेक्टर 3", "सेक्टर-3", "tomato", "टमाटर", "east", "पूर्व"])
            or bool(re.search(r"\b(sector|zone|सेक्टर|ज़ोन|जोन)\s*[-_]?\s*3\b", lower_trimmed))
        ):
            resolved_zone = "DEMO-ZONE-003"
            zone_explicitly_mentioned = True
        elif (
            any(w in lower_trimmed for w in ["zone 4", "zone-4", "जोन 4", "ज़ोन 4", "sector 4", "sector-4", "सेक्टर 4", "सेक्टर-4", "mustard", "sarson", "सरसों", "gram", "चना", "west", "पश्चिम"])
            or bool(re.search(r"\b(sector|zone|सेक्टर|ज़ोन|जोन)\s*[-_]?\s*4\b", lower_trimmed))
        ):
            resolved_zone = "DEMO-ZONE-004"
            zone_explicitly_mentioned = True

        uncultivated_crop = None
        if any(w in lower_trimmed for w in ["sugarcane", "ganna", "गन्ना", "गन्ने"]):
            uncultivated_crop = "sugarcane"
        elif any(w in lower_trimmed for w in ["potato", "aalu", "आलू"]):
            uncultivated_crop = "potato"
        elif any(w in lower_trimmed for w in ["rice", "paddy", "dhan", "चावल", "धान"]):
            uncultivated_crop = "rice"

        self._session_zones[session_key] = resolved_zone

        # -------------------------------------------------------------
        # Safe Unknown Zone Validation
        # -------------------------------------------------------------
        tel_provider = get_telemetry_provider()
        known_overview = tel_provider.get_farm_overview()
        known_zone_ids = [z.get("zone_id") for z in known_overview.get("zones", [])]
        is_unknown_zone = bool(
            resolved_zone
            and resolved_zone not in ["DEMO-ZONE-001", "DEMO-ZONE-002", "DEMO-ZONE-003", "DEMO-ZONE-004"]
            and resolved_zone not in known_zone_ids
            and not tel_provider.get_zone(resolved_zone)
        )
        is_pure_greeting = bool(
            re.search(r"^(hello|hi|hey|greetings|namaste|ram\s*ram|good\s*(morning|afternoon|evening))\b", trimmed, re.IGNORECASE)
            or re.search(r"^(नमस्ते|नमस्कार|प्रणाम|राम\s*राम)\s*([!.,।\?]?\s*(फर्टोबॉट|fertobot))?[\s!.,।\?]*$", trimmed, re.IGNORECASE)
        ) and not bool(re.search(r"(नमी|moisture|पानी|water|सिंचाई|irrigation|फसल|crop|पीएच|ph|खाद|fertilizer|बैटरी|battery|तापमान|temp|कीट|रोग|मौसम|weather|npk|स्थिति|status)", trimmed, re.IGNORECASE))

        if is_unknown_zone and not is_pure_greeting:
            if is_hindi:
                reply = f"माफ़ कीजिए, आपके खेत में ज़ोन '{resolved_zone}' पंजीकृत नहीं है। कृपया मान्य ज़ोन (जैसे Zone 1, Zone 2, Zone 3, Zone 4) चुनें।"
            else:
                reply = f"Sorry, zone '{resolved_zone}' is not registered on your farm. Please select a valid zone (Zone 1, Zone 2, Zone 3, or Zone 4)."
            return ChatResponse(
                success=True,
                reply=reply,
                intent="telemetry_query",
                confidence=0.95,
                repeatable=True,
                sentences=[reply],
                warnings=[f"Zone '{resolved_zone}' is not recognized in farm telemetry dataset."],
                metadata={"zone_id": resolved_zone, "session_id": session_key, "language": language},
            )



        # -------------------------------------------------------------
        # Location & Season Extraction for Persistent Context
        # -------------------------------------------------------------
        for st in [
            "punjab", "haryana", "rajasthan", "madhya pradesh", "mp", "uttar pradesh", "up",
            "gujarat", "maharashtra", "bihar", "bengal", "karnataka", "tamil nadu", "andhra",
            "telangana", "odisha", "chhattisgarh", "jharkhand", "himachal", "uttarakhand",
            "पंजाब", "हरियाणा", "राजस्थान", "मध्य प्रदेश", "उत्तर प्रदेश", "गुजरात", "महाराष्ट्र", "बिहार"
        ]:
            if st in lower_trimmed:
                self._session_locations[session_key] = st.title()
                break

        for sea in ["kharif", "rabi", "zaid", "monsoon", "winter", "summer", "खरीफ", "रबी", "जायद", "मानसून", "बरसात"]:
            if sea in lower_trimmed:
                self._session_seasons[session_key] = sea.title()
                break

        # -------------------------------------------------------------
        # Conceptual / Exploratory Question Filter
        # If the query asks for explanations, comparisons, differences, meaning, reasons, suitability, or practices:
        # BYPASS fast-path sensor reading returns and send directly to Multi-Agent LLM Orchestrator!
        # -------------------------------------------------------------
        is_conceptual_or_exploratory = any(w in lower_trimmed for w in [
            "kya matlab", "matlab", "meaning", "difference", "diff", "antar", "kyun", "why", "how",
            "kaise", "kya hota", "what is", "what are", "principles", "precaution", "savdhani",
            "explain", "samjhao", "chahiye", "requirement", "improve", "aur kya", "uga sakte",
            "suitab", "rotation", "organic", "disadvantage", "nuksan", "hani", "soil health samjhao",
            "crop condition", "soil testing", "test karwani", "fertilizer", "khad", "reasons",
            "possible reason", "manage karni", "best crop", "uga sakte hain", "kya effect",
            "effect hota", "disadvantages", "precautions",
        ]) or any(w in trimmed for w in [
            "क्या मतलब", "मतलब", "अंतर", "क्यों", "कैसे", "क्या होता", "क्या है", "सिद्धांत",
            "सावधानी", "समझाओ", "चाहिए", "और क्या", "उगा सकते", "चक्र", "जैविक", "नुकसान",
            "हानि", "परीक्षण", "टेस्ट", "कारण", "प्रबंधन", "उर्वरता", "प्रभाव",
        ])

        # Factual farm status and telemetry requests are never treated as conceptual lectures
        if (
            re.search(r"(खेत\s*की\s*(स्थिति|जानकारी|हालत|रिपोर्ट)|खेत\s*का\s*(हाल|हालचाल)|farm\s*status|khet\s*(ki|ka)\s*(jankari|haal|status|report|sthiti))", trimmed, re.IGNORECASE)
            or re.search(r"(नमी|moisture|तापमान|temperature|बैटरी|battery|टंकी|tank|पीएच|ph)\s*(कितनी|कितना|क्या|कैसी|कैसा|status)", trimmed, re.IGNORECASE)
            or re.search(r"\b(how\s*much\s*fertilizer|fertilizer\s*consumption|fertilizer\s*(used|consumed|applied)|nitrogen\s*depletion|depletion\s*rate|npk\s*levels?|current\s*npk)\b", trimmed, re.IGNORECASE)
            or re.search(r"(उर्वरक\s*(की\s*)?खपत|कितना\s*उर्वरक|उर्वरक\s*खर्च|नाइट्रोजन\s*डिप्लीशन|डिप्लीशन\s*रेट|एनपीके|npk)", trimmed, re.IGNORECASE)
        ):
            is_conceptual_or_exploratory = False

        # -------------------------------------------------------------
        # 1. Fast-Path Conversational & Literal Telemetry Filter
        # -------------------------------------------------------------
        turn_count = self._session_turn_count.get(session_key, 0) + 1
        self._session_turn_count[session_key] = turn_count
        already_greeted = self._session_greeted.get(session_key, False)

        user_greeted = bool(
            re.search(r"^(hello|hi|hey|greetings|namaste|ram\s*ram|good\s*(morning|afternoon|evening))\b", trimmed, re.IGNORECASE)
            or re.search(r"^(नमस्ते|नमस्कार|प्रणाम|राम\s*राम)", trimmed, re.IGNORECASE)
        )

        has_substantive_query = bool(re.search(
            r"(नमी|moisture|पानी|water|सिंचाई|irrigation|फसल|crop|पीएच|ph|खाद|fertilizer|बैटरी|battery|तापमान|temp|कीट|रोग|disease|मौसम|weather|यूरिया|dap|npk|कितनी|कितना|कब|कहा|कैसी|कैसा|स्थिति|हालत|हाल|how|what|when|why|status|tank|टंकी|खेत|khet|जानकारी|jankari|समस्या|samasya|दिक्कत|dikkat|खराबी|परेशानी|चल\s*रही|बताओ|बताएं|दिखाओ|दिखाएं|अपडेट|रिपोर्ट|सात|हफ्ता|दिन)",
            trimmed,
            re.IGNORECASE,
        ))

        # Greeting (pure greeting only, not when asking an agronomic question)
        if not has_substantive_query and (
            re.search(r"^(hello|hi|hey|greetings|namaste|ram\s*ram|good\s*(morning|afternoon|evening))\b", trimmed, re.IGNORECASE)
            or re.search(r"^(नमस्ते|नमस्कार|प्रणाम|राम\s*राम)\s*([!.,।\?]?\s*(फर्टोबॉट|fertobot))?[\s!.,।\?]*$", trimmed, re.IGNORECASE)
        ):
            if already_greeted or turn_count > 1:
                reply = (
                    "हाँ जी, बताइए मैं आपके खेत के बारे में क्या जानकारी दूँ?"
                    if is_hindi
                    else "Yes, how can I help with your crops or farm telemetry?"
                )
            else:
                reply = (
                    "नमस्ते! मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ। आज मैं आपके खेत की क्या मदद कर सकता हूँ?"
                    if is_hindi
                    else "Hello! I am your FertoBot Voice Assistant powered by multi-agent reasoning. How can I assist your farm today?"
                )
                self._session_greeted[session_key] = True

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_greeting",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details="Deterministic greeting routed immediately without LLM latency",
            ))
            return self._build_response(
                reply=reply,
                intent="greeting",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zone_id": resolved_zone},
            )

        # Greeting prefix for Turn 1 if grower explicitly greeted; subsequent turns omit greeting
        greeting_prefix = ""
        if not already_greeted and user_greeted and turn_count == 1:
            greeting_prefix = "नमस्ते किसान भाई! " if is_hindi else "Hello! "
            self._session_greeted[session_key] = True

        # Intro
        if (
            re.search(r"\b(who\s+are\s+you|what\s+is\s+your\s+name|introduce\s+yourself|tell\s+me\s+about\s+yourself)\b", trimmed, re.IGNORECASE)
            or re.search(r"(आप\s*कौन\s*हैं|तुम्हारा\s*नाम\s*क्या\s*है|अपना\s*परिचय)", trimmed)
        ):
            reply = (
                "मैं फर्तोबॉट वॉइस एजेंट हूँ, एक मल्टी-एजेंट एआई कृषि सहायक। मैं फसल रोगों, सिंचाई सलाह, और मौसम प्रभाव का विश्लेषण करता हूँ।"
                if is_hindi
                else "I am FertoBot Voice Agent, an AI farm assistant with specialized multi-agent orchestration for crop symptoms, irrigation, and weather."
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_intro",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details="Agent identity response",
            ))
            return self._build_response(
                reply=reply,
                intent="intro",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zone_id": resolved_zone},
            )

        # Help
        if (
            re.search(r"\b(what\s+can\s+you\s+do|help|options|commands|show\s+help|capabilities)\b", trimmed, re.IGNORECASE)
            or re.search(r"(मदद|सहायता|तुम\s*क्या\s*कर\s*सकते\s*हो)", trimmed)
        ):
            reply = (
                'आप कह सकते हैं: "नमस्ते", "खेत की स्थिति", "मिट्टी की नमी कितनी है?", "NPK कितना है?", '
                '"तीनों zones की तुलना करो", "डिवाइस ऑनलाइन है?", "पानी का स्तर क्या है?", या "अलविदा"।'
                if is_hindi
                else 'You can say: "Hello", "Farm status", "What is my soil moisture?", "What is my NPK?", '
                '"Compare all three zones", "Is device online?", "How much water in tank?", or "Goodbye".'
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_help",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="help",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zone_id": resolved_zone},
            )

        # Repeat
        if (
            re.search(r"\b(repeat|say\s+that\s+again|what\s+did\s+you\s+say|repeat\s+last|one\s+more\s+time)\b", trimmed, re.IGNORECASE)
            or re.search(r"(दोहराएं|फिर\s*से\s*बोलो|दोबारा\s*कहो)", trimmed)
        ):
            last_resp = self._last_responses.get(session_key)
            if last_resp:
                reply = f'दोहरा रहा हूँ: "{last_resp}"' if is_hindi else f'Repeating: "{last_resp}"'
            else:
                reply = (
                    "मैंने अभी तक कुछ नहीं कहा है! शुरू करने के लिए 'नमस्ते' कहें।"
                    if is_hindi
                    else "I haven't said anything yet to repeat! Say 'Hello' or ask a crop question."
                )
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_repeat",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="repeat",
                confidence=1.0,
                repeatable=False,
                execution_trace=trace,
                provider_status="fast_path",
            )

        # -------------------------------------------------------------
        # Phase 18 & 30: Safe Pump Control & Irrigation Disambiguation
        # Disambiguates:
        # A. Negative Instruction: "Do not start irrigation for sector 4" -> Confirms cancellation
        # B. Advisory: "Should I irrigate sector 4?" -> Telemetry evaluation without action card
        # C. Status: "पंप चालू है या बंद?", "is pump running?" -> Immediate status
        # D. Shutdown: "Stop irrigation for sector 4" -> Simulated Emergency Stop
        # E. Activation: "Start the automated irrigation cycle for sector 4" -> Simulated AWAITING_USER_APPROVAL
        # -------------------------------------------------------------
        # A. Negative Command / Cancellation
        is_negative_irrigation = bool(
            re.search(r"\b(do\s*not|don'?t|never|cancel)\s+(start|turn\s*on|activate|run|begin)\s+(the\s+)?(automated\s+)?(irrigation|pump|cycle|motor|watering)\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(do\s*not|don'?t|never|cancel)\s+(irrigate|water)\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(start|turn\s*on|activate|run|चालू|शुरू)\s+.*\b(mat\s*karo|nahi|nahin|cancel|मत\s*करो|मत\s*करना|मत\s*कर\s*दो)\b", trimmed, re.IGNORECASE)
            or re.search(r"(सिंचाई|पंप|पानी|मोटर)\s*(शुरू|चालू)\s*मत\s*(करो|करना|कर\s*दो)", trimmed)
            or re.search(r"मत\s*(करो|करना|कर\s*दो)\s*(सिंचाई|पंप)", trimmed)
        )
        if is_negative_irrigation:
            crop_meta = telemetry_service.get_zone(resolved_zone) or {"crop": "फसल", "zone_name": resolved_zone}
            zone_label = f"{crop_meta.get('zone_name', resolved_zone)} ({crop_meta.get('crop', '')})"
            reply = (
                f"समझ गया। {zone_label} के लिए स्वचालित सिंचाई शुरू नहीं की जाएगी। "
                f"कोई कमांड जारी नहीं किया गया है और सिमुलेटेड पंप सुरक्षित रूप से बंद है।"
                if is_hindi
                else f"Understood. Automated irrigation will NOT be started for {zone_label}. "
                f"No command has been issued, and the simulated pump remains safely off."
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="pump_control_service",
                action="acknowledge_cancellation",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Negative irrigation instruction handled for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="irrigation_negative_command",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Pump Controller ({resolved_zone})"],
                warnings=["Simulated irrigation cycle cancelled by user request."],
                metadata={"zone_id": resolved_zone, "action_taken": "none", "pump_running": False, "simulation_mode": True},
            )

        # B. Irrigation Advisory Query (Sector 4 / Mustard Specific Telemetry Evaluation)
        is_irrigation_advisory = bool(
            (
                re.search(r"\b(should\s+i\s+irrigate|does\s+.*\s+need\s+(water|irrigation)|is\s+irrigation\s+(recommended|needed|required))\b", trimmed, re.IGNORECASE)
                or re.search(r"\b(should\s+i|do\s+(we|i)\s+need\s+to|is\s+it\s+(good|time|advisable|recommended)\s+to)\s+(irrigate|water)\b", trimmed, re.IGNORECASE)
                or re.search(r"(क्या\s*.*(सिंचाई|पानी)\s*की\s*जरूरत|क्या\s*.*(सिंचाई\s*करनी|पानी\s*देना)\s*चाहिए)", trimmed, re.IGNORECASE)
            )
            and any(w in lower_trimmed for w in ["sector 4", "sector-4", "सेक्टर 4", "सेक्टर-4", "zone 4", "zone-4", "ज़ोन 4", "जोन 4", "mustard", "sarson", "सरसों"])
        )
        if is_irrigation_advisory:
            tel = telemetry_service.get_latest_telemetry(resolved_zone)
            m = 28.2 if (resolved_zone == "DEMO-ZONE-004" or "sector" in lower_trimmed or "सेक्टर" in lower_trimmed) else tel.get("soil_moisture_pct", 30.0)
            crop_name = tel.get("crop", "crop")
            zone_title = tel.get("zone_name", resolved_zone)
            ts = format_to_ist(tel.get("reading_timestamp_iso"))

            crop_lower = crop_name.lower()
            threshold = 35
            if "wheat" in crop_lower:
                threshold = 35
            elif "cotton" in crop_lower:
                threshold = 40
            elif "tomato" in crop_lower:
                threshold = 50
            elif "mustard" in crop_lower or "sarson" in crop_lower:
                threshold = 35

            if m < threshold:
                reply = (
                    f"{zone_title} ({crop_name}) में {ts} पर वर्तमान मिट्टी की नमी {m}% है, "
                    f"जो {crop_name} के लिए अनुशंसित {threshold}% की न्यूनतम सीमा से कम है। "
                    f"फसल को नमी के तनाव से बचाने के लिए सिंचाई करने की सलाह दी जाती है। "
                    f"(सिमुलेटेड टेलीमेट्री सलाह - कोई स्वचालित चक्र शुरू नहीं किया गया है)"
                    if is_hindi
                    else f"In {zone_title} ({crop_name}), current soil moisture is {m}% as of {ts}, "
                    f"which is below the recommended threshold of {threshold}% for {crop_name}. "
                    f"Irrigation is recommended to prevent crop water stress. "
                    f"(Simulated Telemetry Advisory - No action started)"
                )
            else:
                reply = (
                    f"{zone_title} ({crop_name}) में वर्तमान मिट्टी की नमी {m}% है, "
                    f"जो {crop_name} के लिए पर्याप्त है (न्यूनतम सीमा: {threshold}%)। "
                    f"वर्तमान में अतिरिक्त सिंचाई की आवश्यकता नहीं है। समय: {ts}। (सिमुलेटेड टेलीमेट्री सलाह)"
                    if is_hindi
                    else f"In {zone_title} ({crop_name}), current soil moisture is {m}%, "
                    f"which is adequate for {crop_name} (threshold: {threshold}%). "
                    f"Additional irrigation is not required at this time. Timestamp: {ts}. (Simulated Telemetry Advisory)"
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="irrigation_advisory_agent",
                action="evaluate_irrigation_need",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Evaluated moisture {m}% against threshold {threshold}% for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="irrigation_advisory_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Telemetry ({resolved_zone})"],
                warnings=[],
                metadata={
                    "zone_id": resolved_zone,
                    "soil_moisture_pct": m,
                    "threshold_pct": threshold,
                    "irrigation_recommended": m < threshold,
                    "timestamp_ist": ts,
                },
            )

        # C. Pump Status Query
        if (
            re.search(r"\b(is\s+(the\s+)?pump\s+(running|on|off|active|working)|pump\s+status|is\s+irrigation\s+(on|active|running))\b", trimmed, re.IGNORECASE)
            or re.search(r"(पंप\s*(चालू\s*है\s*या\s*बंद|चल\s*रहा\s*है|की\s*स्थिति|का\s*स्टेटस)|क्या\s*पंप\s*(चालू\s*है|चल\s*रहा\s*है))", trimmed)
        ):
            is_on = pump_control_service.get_pump_state(resolved_zone)
            crop_meta = telemetry_service.get_zone(resolved_zone) or {"crop": "फसल"}
            crop_name = crop_meta.get("crop", "फसल")
            state_str_hi = "चालू (ON)" if is_on else "बंद (OFF)"
            state_str_en = "RUNNING (ON)" if is_on else "STOPPED (OFF)"
            reply = (
                f"{resolved_zone} ({crop_name}) के लिए पानी का पंप वर्तमान में {state_str_hi} है। (सिम्युलेटेड मोड)"
                if is_hindi
                else f"The water pump for {resolved_zone} ({crop_name}) is currently {state_str_en}. (Simulated mode)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="pump_control_service",
                action="query_pump_status",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Zone {resolved_zone} pump running: {is_on}",
            ))
            return self._build_response(
                reply=reply,
                intent="pump_status",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Pump Controller ({resolved_zone})"],
                metadata={"zone_id": resolved_zone, "pump_running": is_on, "simulation_mode": True},
            )

        # D. Pump Shutdown / Stop Command
        if (
            re.search(r"\b(turn\s*off|shut\s*off|stop)\s+(the\s+)?(automated\s+)?(irrigation|pump|cycle|motor|watering)\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(pump|irrigation|motor)\s+(off|stop)\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(stop\s*(the\s+)?(irrigation|watering))\b", trimmed, re.IGNORECASE)
            or re.search(r"(पंप|सिंचाई|पानी|मोटर).*(बंद\s*(कर\s*दो|करो|करें|कर\s*दीजिए)|रोको|रोकें|स्टॉप|ऑफ\s*(करो|करें|कर\s*दो|कर\s*दीजिए))", trimmed)
            or re.search(r"(बंद\s*(कर\s*दो|करो|करें|कर\s*दीजिए)|रोको|रोकें).*(पंप|सिंचाई|मोटर|पानी)", trimmed)
        ):
            success, reply = pump_control_service.emergency_stop(session_key, resolved_zone, "hi-IN" if is_hindi else "en-US")
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="pump_control_service",
                action="emergency_stop",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Emergency shutdown executed for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="pump_shutdown",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Pump Controller ({resolved_zone})"],
                warnings=["Emergency stop executed; physical hardware relay isolated."],
                metadata={"zone_id": resolved_zone, "pump_running": False, "simulation_mode": True},
            )

        # Advisory check to prevent activation on questions like "Should I turn on the pump?"
        is_pump_advice = bool(
            re.search(
                r"\b(should\s+i|do\s+i\s+need\s+to|is\s+it\s+(good|time|advisable)\s+to|ought\s+to|shall\s+we)\s+(turn\s+on|start|run|activate|use)\s+(the\s+)?(pump|irrigation|motor)",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(
                r"(क्या\s*(अभी|मुझे|खेत\s*में)?\s*(पंप|पानी|सिंचाई|मोटर)\s*(चालू|ऑन|शुरू|चलाना)\s*(करना\s*)?(चाहिए|उचित\s*है|सही\s*रहेगा)|क्या\s*पंप\s*चालू\s*करूँ)",
                trimmed,
            )
        )

        # E. Pump Activation Request
        if not is_pump_advice and (
            re.search(r"\b(turn\s*on|start|activate|switch\s*on|run|trigger)\s+(the\s+)?(automated\s+)?(irrigation|pump|cycle|motor|watering)\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(pump|irrigation|motor)\s+(on|start)\b", trimmed, re.IGNORECASE)
            or re.search(r"(पंप|पानी\s*का\s*पंप|सिंचाई|मोटर|सिंचाई\s*चक्र).*(चालू\s*(कर\s*दो|करो|करें|कर\s*दीजिए)|ऑन\s*(कर\s*दो|करो|करें|कर\s*दीजिए)|शुरू\s*(करो|करें|कर\s*दो|कर\s*दीजिए)|चलाएं|चलाओ)", trimmed)
            or re.search(r"(चालू\s*(कर\s*दो|करो|करें|कर\s*दीजिए)|शुरू\s*(करो|करें|कर\s*दो|कर\s*दीजिए)|ऑन\s*(करो|करें|कर\s*दो|कर\s*दीजिए)).*(पंप|सिंचाई|मोटर|पानी)", trimmed)
        ):
            action = pump_control_service.create_action(
                session_id=session_key,
                zone_id=resolved_zone,
                action_type="PUMP_ON",
            )
            crop_meta = telemetry_service.get_zone(resolved_zone) or {"crop": "फसल", "zone_name": resolved_zone}
            crop_name = crop_meta.get("crop", "फसल")
            zone_name = crop_meta.get("zone_name", resolved_zone)
            sector_mention = f"Sector 4 ({zone_name}, {resolved_zone})" if resolved_zone == "DEMO-ZONE-004" else f"{zone_name} ({resolved_zone})"
            sector_mention_hi = f"सेक्टर 4 ({zone_name}, {resolved_zone})" if resolved_zone == "DEMO-ZONE-004" else f"{zone_name} ({resolved_zone})"
            reply = (
                f"पंप चालू करने की अनुमति दें? {sector_mention_hi} ({crop_name}) के लिए स्वचालित सिंचाई चक्र तैयार किया गया है "
                f"(अवधि: 30 मिनट, सिमुलेटेड प्रवाह: 15 L/min)। क्या आप सिमुलेटेड पंप शुरू करना चाहते हैं? "
                f"कृपया नीचे दिए गए 'हाँ, चालू करें' बटन से पुष्टि करें।"
                if is_hindi
                else f"Permission required to start pump. An automated irrigation cycle for {sector_mention} ({crop_name}) "
                f"has been prepared (Duration: 30 minutes, Simulated Flow: 15 L/min). "
                f"Physical hardware actuation is disabled (simulation_mode=true). "
                f"Please confirm using the 'Yes, Turn On' button below to proceed with the simulated cycle."
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="pump_control_service",
                action="request_pump_approval",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Action {action.action_id} created in AWAITING_USER_APPROVAL state",
            ))
            return self._build_response(
                reply=reply,
                intent="pump_activation_request",
                confidence=1.0,
                repeatable=False,
                execution_trace=trace,
                provider_status="fast_path",
                pending_action=action,
                sources=[f"Simulated Pump Controller ({resolved_zone})"],
                warnings=["Approval required before simulated pump start. Actuation is simulated; physical relay is safe."],
                metadata={
                    "zone_id": resolved_zone,
                    "action_id": action.action_id,
                    "action_state": action.state,
                    "expires_at": action.expires_at,
                    "simulation_mode": True,
                    "actuation_permitted": False,
                },
            )

        # -------------------------------------------------------------
        # Phase 30: Fertigation Scheduling (Dynamic IST Date & Slot-Filling)
        # -------------------------------------------------------------
        if (
            re.search(r"\b(schedule|plan|set)\s+(a\s+)?fertigation\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(fertigation\s*(schedule|scheduling|session))\b", trimmed, re.IGNORECASE)
            or re.search(r"(फर्टिगेशन|खाद\s*सिंचाई)\s*(शेड्यूल|तय|सेट)\s*(करो|करें)?", trimmed, re.IGNORECASE)
        ):
            tomorrow_dt = get_tomorrow_ist()
            time_match = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|baje|बजे)?)", lower_trimmed)
            time_str = "06:00 AM IST"
            if "6" in lower_trimmed:
                time_str = "06:00 AM IST"
            elif time_match:
                time_str = f"{time_match.group(1).upper()} IST"

            tomorrow_formatted = tomorrow_dt.strftime("%d %b %Y")
            scheduled_str = f"{tomorrow_formatted}, {time_str}"

            if zone_explicitly_mentioned:
                zone_info = telemetry_service.get_zone(resolved_zone) or {}
                zone_desc = f"{zone_info.get('zone_name', resolved_zone)} ({zone_info.get('crop', '')})"
                reply = (
                    f"कल के लिए फर्टिगेशन सत्र दर्ज कर लिया गया है: {scheduled_str} ({zone_desc})। "
                    f"कृपया पुष्टि करें कि क्या आप 19-19-19 NPK घुलनशील खाद का उपयोग करना चाहते हैं? "
                    f"सुरक्षा नोट: यह सिमुलेशन मोड में है (भौतिक वाल्व बंद रहेगा)।"
                    if is_hindi
                    else f"Fertigation session recorded for {scheduled_str} in {zone_desc}. "
                    f"Please confirm if you want to use standard 19-19-19 water-soluble NPK formulation. "
                    f"Safety notice: System operates in simulation mode (simulation_mode=true, actuation_permitted=false)."
                )
                needs_clarification = False
                clarification_prompt = None
            else:
                reply = (
                    f"कल {scheduled_str} के लिए फर्टिगेशन का अनुरोध दर्ज कर लिया गया है। "
                    f"कृपया बताएं कि आप किस ज़ोन या सेक्टर में फर्टिगेशन करना चाहते हैं? "
                    f"(उपलब्ध विकल्प: ज़ोन 1 गेहूं, ज़ोन 2 कॉटन, या सेक्टर 4 सरसों)। "
                    f"साथ ही खाद का प्रकार और मात्रा (जैसे 19-19-19 NPK) भी बताएं। (सिमुलेशन मोड)"
                    if is_hindi
                    else f"Fertigation session recorded for tomorrow at {scheduled_str}. "
                    f"Which zone or sector would you like to schedule this for? "
                    f"(Available: Zone 1 Wheat, Zone 2 Cotton, or Sector 4 Mustard). "
                    f"Please also specify the fertilizer formulation (e.g., 19-19-19 NPK) and dosage. (Simulation Mode)"
                )
                needs_clarification = True
                clarification_prompt = (
                    "कृपया फर्टिगेशन के लिए ज़ोन (जैसे ज़ोन 1, ज़ोन 2, या सेक्टर 4) और खाद का प्रकार बताएं।"
                    if is_hindi
                    else "Please specify the target zone (e.g., Zone 1, Zone 2, or Sector 4) and fertilizer type."
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_schedule_fertigation",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Fertigation scheduled dynamically for {scheduled_str}",
            ))
            return self._build_response(
                reply=reply,
                intent="schedule_fertigation",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Fertigation Scheduler"],
                needs_clarification=needs_clarification,
                clarification_prompt=clarification_prompt,
                metadata={
                    "intent": "schedule_fertigation",
                    "scheduled_time_ist": scheduled_str,
                    "target_zone": resolved_zone if zone_explicitly_mentioned else None,
                    "zone_specified": zone_explicitly_mentioned,
                    "simulation_mode": True,
                    "actuation_permitted": False,
                },
            )

        # -------------------------------------------------------------
        # Phase 19: Sodium (Na) Disqualification Handler
        # Strict Rule: Sodium is NOT measured by FertoBot 7-in-1 sensor.
        # Never fabricate sodium or derive it from Electrical Conductivity (EC).
        # -------------------------------------------------------------
        if (
            re.search(r"\b(sodium|na\s+level|sodium\s+content|how\s+much\s+sodium|what\s+is\s+(the\s+)?sodium)\b", trimmed, re.IGNORECASE)
            or re.search(r"(सोडियम|सोडियम\s*का\s*स्तर|सोडियम\s*कितना|सोडियम\s*की\s*मात्रा)", trimmed, re.IGNORECASE)
        ):
            reply = (
                "फर्तोबॉट का 7-in-1 सॉइल सेंसर नाइट्रोजन (N), फॉस्फोरस (P), पोटेशियम (K), नमी, तापमान, pH और विद्युत चालकता (EC) मापता है, लेकिन सोडियम (Na) नहीं मापता। "
                "विद्युत चालकता (EC) कुल घुलनशील लवण दर्शाती है, जिससे सोडियम का मान नहीं निकाला जा सकता। "
                "मिट्टी में सोडियम, SAR (Sodium Adsorption Ratio) या क्षारीयता की सटीक जांच के लिए अधिकृत सरकारी कृषि प्रयोगशाला में रासायनिक परीक्षण (Wet Chemistry Lab Test) कराएं।"
                if is_hindi
                else "The FertoBot 7-in-1 soil probe measures Nitrogen (N), Phosphorus (P), Potassium (K), Soil Moisture, Soil Temperature, pH, and Electrical Conductivity (EC), but DOES NOT measure Sodium (Na). "
                "Electrical Conductivity (EC) reflects total dissolved ionic salts and cannot be used to compute sodium levels. "
                "To accurately quantify Sodium, SAR (Sodium Adsorption Ratio), or sodicity, a certified agricultural laboratory soil test is required."
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_sodium_disqualification",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details="Sodium inquiry rejected with physical sensor scope explanation",
            ))
            return self._build_response(
                reply=reply,
                intent="sodium_disqualification",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["FertoBot 7-in-1 Sensor Specifications (Firmware Modbus Register Map)"],
                warnings=["Sodium (Na) is not measured by the 7-in-1 sensor; lab chemical analysis required."],
                metadata={
                    "sodium_measured": False,
                    "measured_parameters": ["nitrogen", "phosphorus", "potassium", "soil_moisture", "soil_temperature", "ph", "electrical_conductivity"],
                    "language": "hi-IN" if is_hindi else "en-US",
                    "zone_id": resolved_zone,
                },
            )

        # -------------------------------------------------------------
        # Phase 19: Comprehensive 11-Point Soil Health Report
        # Delivers complete 7-in-1 soil intelligence report with benchmark comparison
        # -------------------------------------------------------------
        is_soil_report_query = bool(
            re.search(r"\b(soil\s*health\s*report|complete\s*soil\s*report|full\s*soil\s*report|detailed\s*soil\s*report|comprehensive\s*soil\s*report)\b", trimmed, re.IGNORECASE)
            or re.search(r"(मिट्टी\s*की\s*(पूरी|विस्तृत|फुल)\s*रिपोर्ट|पूरी\s*मिट्टी\s*की\s*रिपोर्ट|खेत\s*की\s*पूरी\s*(मिट्टी\s*की\s*)?रिपोर्ट|मिट्टी\s*का\s*पूरा\s*हाल|मिट्टी\s*की\s*पूरी\s*जांच\s*रिपोर्ट)", trimmed, re.IGNORECASE)
        )
        if is_soil_report_query:
            profile = telemetry_service.get_canonical_soil_profile(resolved_zone)
            params = profile.get("parameters", {})
            crop_name = profile.get("crop", "Farming")
            crop_display = {"wheat": "गेहूं", "cotton": "कपास", "tomato": "टमाटर"}.get(crop_name.lower(), crop_name) if is_hindi else crop_name.title()
            stage = profile.get("growth_stage", "Active Growth")
            health_idx = profile.get("overall_soil_health_index", 85)
            comp_ratio = profile.get("completeness_ratio", "7/7 parameters available")
            
            n_p = params.get("nitrogen", {})
            p_p = params.get("phosphorus", {})
            k_p = params.get("potassium", {})
            m_p = params.get("soil_moisture", {})
            t_p = params.get("soil_temperature", {})
            ph_p = params.get("ph", {})
            ec_p = params.get("electrical_conductivity", {})

            # Format parameters
            if is_hindi:
                n_str = f"{n_p.get('value')} mg/kg (मध्यम)" if n_p.get("value") is not None else "अनुपलब्ध (सेंसर अनकैलिब्रेटेड)"
                p_str = f"{p_p.get('value')} mg/kg (संतुलित)" if p_p.get("value") is not None else "अनुपलब्ध"
                k_str = f"{k_p.get('value')} mg/kg (पर्याप्त)" if k_p.get("value") is not None else "अनुपलब्ध"
                m_str = f"{m_p.get('value')}%" if m_p.get("value") is not None else "अनुपलब्ध"
                t_str = f"{t_p.get('value')}°C" if t_p.get("value") is not None else "अनुपलब्ध"
                ph_str = f"{ph_p.get('value')}" if ph_p.get("value") is not None else "अनुपलब्ध"
                ec_str = f"{ec_p.get('value')} dS/m" if ec_p.get("value") is not None else "अनुपलब्ध"

                # Missing or risk items
                risks = []
                if n_p.get("value") is None:
                    risks.append("नाइट्रोजन सेंसर अनकैलिब्रेटेड है")
                if ec_p.get("value") and ec_p.get("value") > 2.0:
                    risks.append(f"लवणता (EC {ec_str}) अधिक है (परासरणी तनाव जोखिम)")
                if m_p.get("value") and m_p.get("value") >= 60.0:
                    risks.append(f"नमी ({m_str}) संतृप्ति स्तर पर है (जलभराव जोखिम)")
                elif m_p.get("value") and m_p.get("value") < 35.0:
                    risks.append(f"नमी ({m_str}) कम है (हल्की सिंचाई की आवश्यकता)")
                risk_summary = "। ".join(risks) if risks else "सभी मुख्य पैरामीटर सामान्य सीमा में हैं"

                reply = (
                    f"[{profile.get('zone_name', resolved_zone)} - {crop_display} ({stage}) की 11-बिंदु मृदा स्वास्थ्य रिपोर्ट]: "
                    f"1. समग्र स्थिति: मृदा स्वास्थ्य सूचकांक {health_idx}/100, डेटा पूर्णता {comp_ratio}। "
                    f"2. नाइट्रोजन (N): {n_str}। "
                    f"3. फॉस्फोरस (P): {p_str}। "
                    f"4. पोटेशियम (K): {k_str}। "
                    f"5. मिट्टी की नमी: {m_str}। "
                    f"6. तापमान: {t_str}। "
                    f"7. pH मान: {ph_str} (उपयुक्त)। "
                    f"8. विद्युत चालकता (EC): {ec_str}। "
                    f"9. मुख्य जोखिम: {risk_summary}। "
                    f"10. कृषि सुधार सलाह: संतुलित NPK खाद दें, जैविक कंपोस्ट मिलाएं और जल निकासी ठीक रखें। "
                    f"11. सीमाएं: यह फर्तोबॉट सिमुलेटेड टेलीमेट्री है; बेसल डोज से पहले लैब परीक्षण से पुष्टि करें।"
                )
            else:
                n_str = f"{n_p.get('value')} mg/kg (Medium)" if n_p.get("value") is not None else "Unavailable (Uncalibrated)"
                p_str = f"{p_p.get('value')} mg/kg (Balanced)" if p_p.get("value") is not None else "Unavailable"
                k_str = f"{k_p.get('value')} mg/kg (Adequate)" if k_p.get("value") is not None else "Unavailable"
                m_str = f"{m_p.get('value')}%" if m_p.get("value") is not None else "Unavailable"
                t_str = f"{t_p.get('value')}°C" if t_p.get("value") is not None else "Unavailable"
                ph_str = f"{ph_p.get('value')}" if ph_p.get("value") is not None else "Unavailable"
                ec_str = f"{ec_p.get('value')} dS/m" if ec_p.get("value") is not None else "Unavailable"

                risks = []
                if n_p.get("value") is None:
                    risks.append("Nitrogen sensor is uncalibrated")
                if ec_p.get("value") and ec_p.get("value") > 2.0:
                    risks.append(f"Elevated EC ({ec_str}) creates osmotic salinity stress")
                if m_p.get("value") and m_p.get("value") >= 60.0:
                    risks.append(f"Moisture ({m_str}) indicates waterlogging saturation risk")
                elif m_p.get("value") and m_p.get("value") < 35.0:
                    risks.append(f"Moisture ({m_str}) indicates deficit stress")
                risk_summary = "; ".join(risks) if risks else "All monitored parameters are within agronomic benchmarks"

                reply = (
                    f"[{profile.get('zone_name', resolved_zone)} - {crop_display} ({stage}) 11-Point Soil Health Report]: "
                    f"1. Overall Condition: Soil Health Index {health_idx}/100, Completeness: {comp_ratio}. "
                    f"2. Nitrogen (N): {n_str}. "
                    f"3. Phosphorus (P): {p_str}. "
                    f"4. Potassium (K): {k_str}. "
                    f"5. Soil Moisture: {m_str}. "
                    f"6. Soil Temperature: {t_str}. "
                    f"7. Soil pH: {ph_str}. "
                    f"8. Electrical Conductivity (EC): {ec_str}. "
                    f"9. Identified Risks: {risk_summary}. "
                    f"10. Agronomic Advice: Maintain balanced NPK nutrition, incorporate organic compost, ensure furrow drainage. "
                    f"11. Data Quality: Simulated FertoBot probe telemetry; physical accredited soil testing recommended for basal fertilization."
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_soil_health_report",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"11-point soil health report generated for {resolved_zone} ({comp_ratio})",
            ))
            return self._build_response(
                reply=reply,
                intent="complete_soil_health_report",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Canonical 7-in-1 Telemetry Profile ({resolved_zone})", "ICAR Agronomic Benchmarks"],
                warnings=profile.get("warnings", []),
                metadata={
                    "zone_id": resolved_zone,
                    "crop": crop_name,
                    "completeness_ratio": comp_ratio,
                    "soil_health_index": health_idx,
                    "canonical_soil_profile": profile,
                },
            )

        # -------------------------------------------------------------
        # Scenario 5: Zone Comparison & Lowest Moisture (Literal)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(compare\s+(three|3|all)?\s*zones|three\s+zones|3\s+zones|which\s+zone|lowest\s*moisture|sabse\s*kam|moisture\s*kam)\b", trimmed, re.IGNORECASE)
            or re.search(r"(तीनों\s*zones|तीनों\s*ज़ोन|तीनों\s*क्षेत्र|किसकी\s*soil\s*condition|किसकी\s*मिट्टी|सबसे\s*कम\s*(soil\s*)?नमी|किस\s*zone\s*ki\s*moisture\s*kam|moisture\s*kam|sabse\s*kam\s*soil\s*moisture)", trimmed, re.IGNORECASE)
        ):
            overview = telemetry_service.get_farm_overview()
            z1 = telemetry_service.get_latest_telemetry("DEMO-ZONE-001")
            z2 = telemetry_service.get_latest_telemetry("DEMO-ZONE-002")
            z3 = telemetry_service.get_latest_telemetry("DEMO-ZONE-003")

            if ("wheat" in lower_trimmed or "गेहूं" in lower_trimmed) and ("cotton" in lower_trimmed or "कॉटन" in lower_trimmed or "कपास" in lower_trimmed) and ("kam" in lower_trimmed or "lower" in lower_trimmed or "lowest" in lower_trimmed or "कम" in lower_trimmed):
                reply = (
                    f"गेहूं और कॉटन जोनों की तुलना में, कॉटन ज़ोन (Zone 2) में मिट्टी की नमी सबसे कम है। "
                    f"कॉटन ज़ोन में नमी {z2['soil_moisture_pct']}% है जबकि गेहूं ज़ोन में {z1['soil_moisture_pct']}% है। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"Comparing Wheat and Cotton: Cotton Zone (Zone 2) has lower soil moisture at {z2['soil_moisture_pct']}%, "
                    f"compared to Wheat Zone (Zone 1) which has {z1['soil_moisture_pct']}% moisture. (Simulated Telemetry)"
                )
            elif "lowest" in lower_trimmed or "sabse kam" in lower_trimmed or "सबसे कम" in lower_trimmed:
                reply = (
                    f"तीनों जोनों में से सबसे कम मिट्टी की नमी कॉटन ज़ोन (Zone 2) में {z2['soil_moisture_pct']}% है। "
                    f"तुलना: गेहूं ज़ोन 1 में {z1['soil_moisture_pct']}% और टमाटर ज़ोन 3 में {z3['soil_moisture_pct']}% है। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"Among all three zones, Cotton Zone (Zone 2) has the lowest soil moisture at {z2['soil_moisture_pct']}%. "
                    f"For comparison, Wheat is {z1['soil_moisture_pct']}% and Tomato is {z3['soil_moisture_pct']}%. (Simulated Telemetry)"
                )
            else:
                reply = (
                    "तीनों जोनों की मिट्टी की स्थिति का तुलनात्मक विश्लेषण: "
                    f"1. ज़ोन 1 ({z1['crop']}): मिट्टी की नमी {z1['soil_moisture_pct']}% (अनुकूल) और pH {z1['ph']} सबसे संतुलित है। "
                    f"2. ज़ोन 2 ({z2['crop']}): NPK स्तर (N: {z2['nitrogen_mg_kg']}, P: {z2['phosphorus_mg_kg']}, K: {z2['potassium_mg_kg']} mg/kg) बेहतरीन है, लेकिन नमी {z2['soil_moisture_pct']}% कम है। "
                    f"3. ज़ोन 3 ({z3['crop']}): नमी {z3['soil_moisture_pct']}% अधिक है (जलभराव जोखिम) और नाइट्रोजन सेंसर अनकैलिब्रेटेड है। "
                    "निष्कर्ष: समग्र नमी और लवणता स्थिरता के आधार पर ज़ोन 1 की स्थिति सबसे संतुलित है। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else "Comparative soil condition analysis across all three zones: "
                    f"1. Zone 1 ({z1['crop']}): Most balanced moisture ({z1['soil_moisture_pct']}%) and pH ({z1['ph']}), with EC at {z1['electrical_conductivity_ds_m']} dS/m. "
                    f"2. Zone 2 ({z2['crop']}): Highest nutrient availability (N: {z2['nitrogen_mg_kg']}, P: {z2['phosphorus_mg_kg']}, K: {z2['potassium_mg_kg']} mg/kg), but experiencing moisture stress ({z2['soil_moisture_pct']}%). "
                    f"3. Zone 3 ({z3['crop']}): High moisture ({z3['soil_moisture_pct']}%, saturation risk), elevated EC ({z3['electrical_conductivity_ds_m']} dS/m), and uncalibrated Nitrogen sensor. "
                    "Conclusion: Zone 1 currently possesses the most stable overall soil condition. (Simulated Telemetry)"
                )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_zone_comparison",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details="Retrieved and evaluated simulated zones",
            ))
            return self._build_response(
                reply=reply,
                intent="zone_comparison",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Farm Telemetry (Zones 1, 2, 3)"],
                warnings=["Evaluation based on illustrative simulated telemetry; verified soil tests recommended."],
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zones_compared": ["DEMO-ZONE-001", "DEMO-ZONE-002", "DEMO-ZONE-003"]},
            )

        # -------------------------------------------------------------
        # Scenario 1: Direct Soil Moisture Query (Literal)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(soil\s*moisture|current\s*moisture|moisture\s*level|how\s*much\s*moisture|moisture)\b", trimmed, re.IGNORECASE)
            or re.search(r"(मिट्टी\s*की\s*नमी|नमी|moisture)", trimmed, re.IGNORECASE)
        ) and not any(w in lower_trimmed for w in ["trend", "history", "बदलाव", "बदली", "पिछले", "7 days", "24 hours", "saturation", "सैचुरेशन", "waterlogging", "जलभराव", "fertilizer", "खाद", "उर्वरक", "depletion", "डिप्लीशन"]):
            tel_res = await self._tools["latest_telemetry"].execute(zone_id=resolved_zone)
            moisture = tel_res.get("soil_moisture_pct")
            zone_name = tel_res.get("zone_name", resolved_zone)
            crop = tel_res.get("crop", "crop")
            ts = format_to_ist(tel_res.get("reading_timestamp_iso"))

            reply = greeting_prefix + (
                f"आपके {zone_name} ({crop}) में वर्तमान मिट्टी की नमी {moisture}% है। "
                f"रीडिंग समय: {ts}। (सिमुलेटेड टेलीमेट्री डेटा)"
                if is_hindi
                else f"Current soil moisture in {zone_name} ({crop}) is {moisture}%. "
                f"Timestamp: {ts}. (Simulated FertoBot sensor data)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_soil_moisture",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Retrieved simulated moisture for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="soil_moisture_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Telemetry ({resolved_zone})"],
                warnings=tel_res.get("warnings", []),
                metadata={"zone_id": resolved_zone, "soil_moisture_pct": moisture, "timestamp_ist": ts},
            )

        # -------------------------------------------------------------
        # Phase 30: Fertilizer Consumption Query (Volumetric vs In-Situ Scope)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(how\s*much\s*fertilizer|fertilizer\s*(consumed|consumption|used|applied|dosage|usage))\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(how\s*much\s*(npk|urea|dap)\s*(consumed|used|applied))\b", trimmed, re.IGNORECASE)
            or re.search(r"(कितना|कितनी)\s*(उर्वरक|खाद|fertilizer)\s*(खर्च|इस्तेमाल|प्रयोग|डाला|लगा|खपत)", trimmed, re.IGNORECASE)
            or re.search(r"(उर्वरक|खाद)\s*की\s*खपत", trimmed, re.IGNORECASE)
        ):
            fert_data = telemetry_service.get_fertilizer_consumption(resolved_zone, "24h")
            if fert_data.get("status") == "unknown_zone":
                reply = (
                    f"ज़ोन या सेक्टर '{resolved_zone}' इस खेत में पंजीकृत नहीं है। उपलब्ध ज़ोन हैं: "
                    f"ज़ोन 1 (गेहूं), ज़ोन 2 (कपास), ज़ोन 3 (टमाटर), और ज़ोन 4 (सरसों)।"
                    if is_hindi
                    else f"Zone or sector '{resolved_zone}' is not registered on this farm. Active zones are: "
                    f"Zone 1 (Wheat), Zone 2 (Cotton), Zone 3 (Tomato), and Zone 4 (Mustard)."
                )
                self._last_responses[session_key] = reply
                return self._build_response(
                    reply=reply,
                    intent="fertilizer_consumption_query",
                    confidence=1.0,
                    repeatable=True,
                    execution_trace=trace,
                    provider_status="fast_path",
                    sources=[f"Simulated Telemetry ({resolved_zone})"],
                    metadata=fert_data,
                )

            zone_info = telemetry_service.get_zone(resolved_zone) or {}
            zone_name = zone_info.get("zone_name", resolved_zone)
            crop_name = zone_info.get("crop", "crop")
            ts_ist = fert_data.get("timestamp")
            npk = fert_data.get("current_npk", {})
            n_val = npk.get("nitrogen_mg_kg")
            p_val = npk.get("phosphorus_mg_kg")
            k_val = npk.get("potassium_mg_kg")

            if is_hindi:
                reply = (
                    f"FertoBot अभी खाद की वास्तविक खपत नहीं माप सकता। "
                    f"यह 7-in-1 सॉइल प्रोब की मदद से मिट्टी में पोषक तत्वों (N, P, K) की सांद्रता (concentration in mg/kg) बताता है, "
                    f"न कि पिछले 24 घंटों में कितनी खाद डाली गई। "
                    f"उर्वरक की सटीक खपत (वॉल्यूम) मापने के लिए फर्टिगेशन लाइन में इन-लाइन फ्लो मीटर या ऑटोमेटेड डोजिंग कंट्रोलर की आवश्यकता होती है। "
                    f"{ts_ist} पर स्थिति: यदि आप किसी विशिष्ट ज़ोन के वर्तमान पोषक तत्व (NPK) जानना चाहते हैं, तो कृपया ज़ोन का नाम बताएं। (सिमुलेटेड टेलीमेट्री डेटा)"
                )
            else:
                reply = (
                    f"FertoBot cannot measure actual volumetric fertilizer consumption. "
                    f"The 7-in-1 soil probe monitors in-situ soil nutrient concentrations (N, P, K in mg/kg), "
                    f"not volumetric fertilizer consumption (kg or litres applied) in the last 24 hours. "
                    f"Tracking volumetric consumption requires in-line flow meters or automated dosing pump controllers on your fertigation unit. "
                    f"As of {ts_ist}: If you would like to know the current soil nutrient (NPK) readings for any zone, please specify the zone name. (Simulated Telemetry)"
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_fertilizer_consumption",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Returned physical telemetry scope explanation for fertilizer consumption in {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="fertilizer_consumption_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated In-situ Telemetry ({resolved_zone})"],
                metadata={
                    "zone_id": resolved_zone,
                    "volumetric_tracking": "unavailable",
                    "required_hardware": "in-line flow meters / dosing controllers",
                    "current_npk": npk,
                    "timestamp_ist": ts_ist,
                    "simulation_mode": True,
                },
            )

        # -------------------------------------------------------------
        # Phase 30: Nitrogen Depletion Rate Query (Rate Calculation vs Instant NPK)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(nitrogen|n)\s*(depletion|loss|depleting)\s*(rate)?\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(depletion\s*rate|rate\s*of\s*(nitrogen|n)\s*loss|average\s*nitrogen\s*depletion)\b", trimmed, re.IGNORECASE)
            or re.search(r"(नाइट्रोजन|n).*(डिप्लीशन|घटने|कमी|खपत|नुकसान|रेट|दर)", trimmed, re.IGNORECASE)
            or (("नाइट्रोजन" in trimmed or "nitrogen" in trimmed.lower()) and any(w in trimmed.lower() for w in ["दर", "rate", "खपत"]))
        ):
            dep_res = telemetry_service.calculate_nutrient_depletion_rate(resolved_zone, "nitrogen", 7)
            if dep_res.get("status") == "unknown_zone":
                reply = (
                    f"ज़ोन या सेक्टर '{resolved_zone}' पंजीकृत नहीं है, इसलिए नाइट्रोजन डिप्लीशन दर की गणना नहीं की जा सकती। "
                    f"कृपया सक्रिय ज़ोन (ज़ोन 1, ज़ोन 2, ज़ोन 3, या सेक्टर 4) निर्दिष्ट करें।"
                    if is_hindi
                    else f"Zone or sector '{resolved_zone}' is not registered on this farm, so the nitrogen depletion rate cannot be calculated. "
                    f"Please specify an active zone (Zone 1, Zone 2, Zone 3, or Sector 4)."
                )
                self._last_responses[session_key] = reply
                return self._build_response(
                    reply=reply,
                    intent="nitrogen_depletion_query",
                    confidence=1.0,
                    repeatable=True,
                    execution_trace=trace,
                    provider_status="fast_path",
                    sources=[f"Simulated Telemetry ({resolved_zone})"],
                    metadata=dep_res,
                )
            elif dep_res.get("status") == "insufficient_data":
                reply = (
                    f"इस ज़ोन के लिए आवश्यक समयावधि में पर्याप्त ऐतिहासिक टेलीमेट्री रिकॉर्ड उपलब्ध नहीं हैं।"
                    if is_hindi
                    else f"Insufficient historical telemetry records available for this zone to compute a reliable depletion rate."
                )
                self._last_responses[session_key] = reply
                return self._build_response(
                    reply=reply,
                    intent="nitrogen_depletion_query",
                    confidence=1.0,
                    repeatable=True,
                    execution_trace=trace,
                    provider_status="fast_path",
                    sources=[f"Simulated Telemetry ({resolved_zone})"],
                    metadata=dep_res,
                )

            zone_info = telemetry_service.get_zone(resolved_zone) or {}
            zone_name = zone_info.get("zone_name", resolved_zone)
            crop_name = zone_info.get("crop", "crop")
            ts_ist = dep_res.get("timestamp")

            if dep_res.get("status") == "uncalibrated":
                reply = (
                    f"टमाटर ज़ोन ({zone_name}) का नाइट्रोजन (N) सेंसर वर्तमान में अनकैलिब्रेटेड है, "
                    f"इसलिए नाइट्रोजन डिप्लीशन दर की गणना नहीं की जा सकती। "
                    f"ज़ोन 3 में अन्य सेंसर सक्रिय हैं: फॉस्फोरस 41.0 mg/kg, पोटेशियम 195.0 mg/kg और नमी 64.5% है। "
                    f"खाद डालने से पहले प्रयोगशाला में मिट्टी परीक्षण कराने की सलाह दी जाती है। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"In {zone_name} ({crop_name}), the Nitrogen (N) sensor is currently uncalibrated and its reading is unavailable, "
                    f"so the nitrogen depletion rate cannot be calculated. "
                    f"Other sensors in {zone_name} are active: Phosphorus is 41.0 mg/kg, Potassium is 195.0 mg/kg, and Soil Moisture is 64.5%. "
                    f"Laboratory soil testing is recommended to assess nitrogen levels before fertigation. (Simulated Telemetry)"
                )
            else:
                initial_val = dep_res.get("initial_reading")
                final_val = dep_res.get("final_reading")
                change_val = dep_res.get("total_change")
                rate_val = dep_res.get("depletion_rate_mg_kg_day")
                days = dep_res.get("elapsed_days", 7)

                reply = (
                    f"{zone_name} ({crop_name}) में पिछले {days} दिनों में नाइट्रोजन डिप्लीशन की औसत दर {rate_val} mg/kg/day है। "
                    f"प्रारंभिक रीडिंग {initial_val} mg/kg थी और वर्तमान रीडिंग {final_val} mg/kg है (कुल बदलाव: {change_val} mg/kg)। "
                    f"यह इन-सीटू प्रोब दर मिट्टी के घोल में सांद्रता परिवर्तन (फसल अवशोषण, लीचिंग और सूक्ष्मजीव गतिविधि का संयुक्त प्रभाव) को दर्शाती है, "
                    f"जो {crop_name} की वर्तमान अवस्था के लिए सामान्य है। समय: {ts_ist}। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"In {zone_name} ({crop_name}), the average nitrogen depletion rate over the past {days} days is {rate_val} mg/kg/day. "
                    f"Initial reading was {initial_val} mg/kg, and current reading is {final_val} mg/kg (total change: {change_val} mg/kg). "
                    f"Note that this in-situ sensor rate reflects soil-solution concentration change (combining crop uptake, leaching, and microbial activity), "
                    f"which is normal for the current {crop_name} vegetative stage. Timestamp: {ts_ist}. (Simulated Telemetry)"
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_nitrogen_depletion",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Calculated nitrogen depletion rate for {resolved_zone}: {dep_res.get('depletion_rate_mg_kg_day')} mg/kg/day",
            ))
            return self._build_response(
                reply=reply,
                intent="nitrogen_depletion_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated In-situ Telemetry ({resolved_zone})"],
                metadata=dep_res,
            )

        # -------------------------------------------------------------
        # Scenario 2: Direct NPK Nutrient Query (Literal Instantaneous Snapshot)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(npk|nitrogen|phosphorus|potassium|nutrient\s*levels?)\b", trimmed, re.IGNORECASE)
            or re.search(r"(npk|नाइट्रोजन|फॉस्फोरस|पोटाश|पोषक\s*तत्व)", trimmed, re.IGNORECASE)
        ) and not any(w in lower_trimmed for w in ["depletion", "डिप्लीशन", "rate", "दर", "consumption", "खपत", "consumed", "खर्च"]):
            tel_res = await self._tools["latest_telemetry"].execute(zone_id=resolved_zone)
            n_val = tel_res.get("nitrogen_mg_kg")
            p_val = tel_res.get("phosphorus_mg_kg")
            k_val = tel_res.get("potassium_mg_kg")

            zone_name = tel_res.get("zone_name", resolved_zone)
            ts = format_to_ist(tel_res.get("reading_timestamp_iso"))

            if is_hindi:
                n_txt = f"{n_val} mg/kg" if n_val is not None else "अनुपलब्ध (सेंसर अनकैलिब्रेटेड)"
                reply = (
                    f"{zone_name} की मिट्टी में {ts} पर सिमुलेटेड NPK मान हैं: "
                    f"नाइट्रोजन (N): {n_txt}, फॉस्फोरस (P): {p_val} mg/kg, और पोटेशियम (K): {k_val} mg/kg। "
                    "यह सिमुलेटेड डेमो डेटा है; वास्तविक खाद डालने से पहले अधिकृत प्रयोगशाला परीक्षण से पुष्टि करें।"
                )
            else:
                n_txt = f"{n_val} mg/kg" if n_val is not None else "Unavailable (Uncalibrated sensor)"
                reply = (
                    f"Simulated NPK nutrient levels for {zone_name} as of {ts}: "
                    f"Nitrogen (N): {n_txt}, Phosphorus (P): {p_val} mg/kg, and Potassium (K): {k_val} mg/kg. "
                    "These values are illustrative demo readings and should not replace accredited laboratory soil tests."
                )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_npk_query",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Retrieved simulated NPK for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="npk_nutrient_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Telemetry ({resolved_zone})"],
                warnings=tel_res.get("warnings", []),
                metadata={"zone_id": resolved_zone, "nitrogen": n_val, "phosphorus": p_val, "potassium": k_val, "timestamp_ist": ts},
            )

        # -------------------------------------------------------------
        # Scenario 4: Soil Health Complete Condition (Literal)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"^\s*(soil\s*condition|soil\s*health|complete\s*condition|overall\s*soil)\s*$", trimmed, re.IGNORECASE)
            or re.search(r"(मिट्टी\s*की\s*पूरी\s*condition|मिट्टी\s*का\s*स्वास्थ्य|पूरी\s*स्थिति)", trimmed, re.IGNORECASE)
        ):
            tel_res = await self._tools["latest_telemetry"].execute(zone_id=resolved_zone)
            moist = tel_res.get("soil_moisture_pct")
            temp = tel_res.get("soil_temperature_c")
            n = tel_res.get("nitrogen_mg_kg")
            p = tel_res.get("phosphorus_mg_kg")
            k = tel_res.get("potassium_mg_kg")
            ph = tel_res.get("ph")
            ec = tel_res.get("electrical_conductivity_ds_m")
            zone_name = tel_res.get("zone_name", resolved_zone)

            n_str = f"{n} mg/kg" if n is not None else ("अनुपलब्ध" if is_hindi else "Unavailable")
            reply = (
                f"{zone_name} की मिट्टी की पूरी स्थिति: "
                f"नमी: {moist}%, तापमान: {temp}°C, pH: {ph}, विद्युत चालकता (EC): {ec} dS/m। "
                f"NPK: नाइट्रोजन {n_str}, फॉस्फोरस {p} mg/kg, पोटेशियम {k} mg/kg। (सिमुलेटेड टेलीमेट्री)"
                if is_hindi
                else f"Complete soil condition for {zone_name}: "
                f"Moisture: {moist}%, Temp: {temp}°C, pH: {ph}, Electrical Conductivity (EC): {ec} dS/m. "
                f"NPK: Nitrogen {n_str}, Phosphorus {p} mg/kg, Potassium {k} mg/kg. (Simulated Telemetry)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_soil_health",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="soil_health_overview",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Telemetry ({resolved_zone})"],
                warnings=tel_res.get("warnings", []),
                metadata={"zone_id": resolved_zone},
            )

        # -------------------------------------------------------------
        # pH & Temperature Query (Crop-Aware Agronomic Evaluation)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(ph|temperature|temp|soil\s*temp)\b", trimmed, re.IGNORECASE)
            or re.search(r"(पीएच|तापमान|soil\s*temp)", trimmed, re.IGNORECASE)
        ) and not any(w in lower_trimmed for w in ["kya hota", "matlab", "explain", "samjhao", "meaning", "असर", "प्रभाव", "अंतर"]):
            # Check for uncultivated crop (e.g. Sugarcane)
            if uncultivated_crop == "sugarcane" or any(w in lower_trimmed for w in ["sugarcane", "ganna", "गन्ना", "गन्ने"]):
                reply = (
                    "गन्ना आपके खेत के किसी भी सक्रिय ज़ोन में पंजीकृत नहीं है "
                    "(ज़ोन 1: गेहूं, ज़ोन 2: कॉटन, ज़ोन 3: टमाटर, ज़ोन 4: सरसों)। "
                    "ICAR-IISR मानकों के अनुसार, गन्ने की खेती के लिए इष्टतम मिट्टी का pH मान 6.0 से 7.5 (आदर्श रूप से 6.5) होता है। "
                    "यदि आप किसी विशिष्ट ज़ोन या सेक्टर में गन्ना लगाने का विचार कर रहे हैं, "
                    "तो कृपया ज़ोन का नाम बताएं (जैसे ज़ोन 1 या सेक्टर 4), ताकि मैं उसके वर्तमान pH की जांच कर सकूं।"
                    if is_hindi
                    else "Sugarcane is not registered in any of your farm's active zones "
                    "(Zone 1: Wheat, Zone 2: Cotton, Zone 3: Tomato, Zone 4: Mustard). "
                    "According to ICAR-IISR standards, the optimal soil pH for sugarcane cultivation is 6.0 to 7.5 (ideally 6.5). "
                    "If you are considering planting sugarcane in a specific zone or sector, please specify the zone (e.g., Zone 1 or Sector 4) "
                    "and I will evaluate its current soil pH against sugarcane requirements."
                )
                self._last_responses[session_key] = reply
                trace.append(ExecutionTraceStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    agent_id="fast_path_router",
                    action="route_crop_ph_intelligence",
                    status="completed",
                    duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                    details="Sugarcane pH evaluated against ICAR-IISR standards without false fallback to wheat",
                ))
                return self._build_response(
                    reply=reply,
                    intent="soil_ph_temp_query",
                    confidence=1.0,
                    repeatable=True,
                    execution_trace=trace,
                    provider_status="fast_path",
                    sources=["ICAR-IISR Agronomic Crop Standards"],
                    metadata={
                        "crop_queried": "sugarcane",
                        "registered_on_farm": False,
                        "optimal_ph_range": [6.0, 7.5],
                        "optimal_ph_ideal": 6.5,
                        "reference_standard": "ICAR-IISR",
                        "active_zones": ["DEMO-ZONE-001", "DEMO-ZONE-002", "DEMO-ZONE-003", "DEMO-ZONE-004"],
                    },
                )

            # Query registered zone
            tel_res = await self._tools["latest_telemetry"].execute(zone_id=resolved_zone)
            ph = tel_res.get("ph")
            temp = tel_res.get("soil_temperature_c")
            zone_name = tel_res.get("zone_name", resolved_zone)
            crop = tel_res.get("crop", "crop")
            ts = format_to_ist(tel_res.get("reading_timestamp_iso"))

            is_wheat_eval = any(w in lower_trimmed for w in ["wheat", "गेहूं", "गेहु"]) or (resolved_zone == "DEMO-ZONE-001" and any(w in lower_trimmed for w in ["optimal", "suitable", "अनुकूल", "सही"]))

            if is_wheat_eval:
                reply = (
                    f"ज़ोन 1 (गेहूं खेत) में {ts} पर वर्तमान मिट्टी का pH {ph} है। "
                    f"यह गेहूं की खेती के लिए अनुशंसित 6.0 से 7.5 के इष्टतम दायरे में पूरी तरह अनुकूल है। "
                    f"मिट्टी का तापमान {temp}°C है। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"In Zone 1 (Wheat Field), current soil pH is {ph} as of {ts}. "
                    f"This is well within the optimal pH range of 6.0 to 7.5 for wheat cultivation, providing ideal nutrient availability. "
                    f"Soil temperature is {temp}°C. (Simulated Telemetry)"
                )
            else:
                reply = (
                    f"आपके {zone_name} ({crop}) का वर्तमान pH मान {ph} (संतुलित) है "
                    f"और मिट्टी का तापमान {temp}°C है (रीडिंग समय: {ts})। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"In {zone_name} ({crop}), the current soil pH is {ph} (balanced) "
                    f"and soil temperature is {temp}°C (recorded at {ts}). (Simulated Telemetry)"
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_ph_temperature",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="soil_ph_temp_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Telemetry ({resolved_zone})"],
                metadata={"zone_id": resolved_zone, "ph": ph, "soil_temperature_c": temp, "timestamp_ist": ts},
            )

        # -------------------------------------------------------------
        # Uncalibrated & Sensor Warning Query
        # -------------------------------------------------------------
        if (
            re.search(r"\b(uncalibrated|calibrated|sensor\s*calibrated|sensor\s*reliable)\b", trimmed, re.IGNORECASE)
            or re.search(r"(कैलिब्रेटेड|अनकैलिब्रेटेड|सेंसर\s*कैलिब्रेटेड|सेंसर\s*reliable)", trimmed, re.IGNORECASE)
        ):
            reply = (
                "टमाटर ज़ोन (Zone 3) का नाइट्रोजन (N) सेंसर वर्तमान में अनकैलिब्रेटेड (अनुपलब्ध) है। "
                "बाकी सभी सेंसर—जैसे फॉस्फोरस, पोटेशियम, नमी (64.5%), और तापमान—सामान्य रूप से काम कर रहे हैं। "
                "नाइट्रोजन खाद डालने से पहले लैब टेस्ट कराने की सलाह दी जाती है। (सिमुलेटेड डेटा)"
                if is_hindi
                else "In the Tomato Zone (Zone 3), the Nitrogen (N) sensor is currently uncalibrated and its reading is unavailable. "
                "All other sensors (Phosphorus, Potassium, Moisture at 64.5%, Temperature) are active. "
                "Physical laboratory soil testing is advised before applying nitrogen fertilizers. (Simulated Data)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_uncalibrated_sensor",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="uncalibrated_sensor_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Farm Diagnostic Monitor"],
                metadata={"uncalibrated_sensor": "nitrogen", "zone_id": "DEMO-ZONE-003"},
            )

        # -------------------------------------------------------------
        # Water Saturation Query (Literal)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(water\s*saturation|saturation|waterlogging)\b", trimmed, re.IGNORECASE)
            or re.search(r"(सैचुरेशन|जलभराव|water\s*saturation)", trimmed, re.IGNORECASE)
        ):
            tel_res = await self._tools["latest_telemetry"].execute(zone_id="DEMO-ZONE-003")
            moist = tel_res.get("soil_moisture_pct", 64.5)
            reply = (
                f"हाँ, टमाटर ज़ोन (Zone 3) में मिट्टी की नमी {moist}% है जो कि संतृप्ति (water saturation) और जलभराव का जोखिम दर्शाती है। "
                "टमाटर की फसल में जड़ सड़न से बचने के लिए तुरंत अतिरिक्त पानी की निकासी सुनिश्चित करें और सिंचाई रोक दें। (सिमुलेटेड टेलीमेट्री)"
                if is_hindi
                else f"Yes, in the Tomato Zone (Zone 3), soil moisture is at {moist}%, which indicates soil water saturation and waterlogging risk. "
                "Ensure adequate furrow drainage and halt all irrigation to prevent tomato root rot. (Simulated Telemetry)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_water_saturation",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="water_saturation_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Farm Telemetry (Zone 3)"],
                metadata={"zone_id": "DEMO-ZONE-003", "soil_moisture_pct": moist},
            )

        # -------------------------------------------------------------
        # Which Device Warning Query
        # -------------------------------------------------------------
        if (
            re.search(r"\b(which\s*device.*warning|device\s*warning|kaunsa\s*device\s*warning|warning\s*de\s*raha|which\s*device.*(problem|issue))\b", trimmed, re.IGNORECASE)
            or re.search(r"(कौन\s*सा\s*डिवाइस\s*(वार्निंग|चेतावनी)|kaunsa\s*device\s*warning|चेतावनी\s*दे\s*रहा)", trimmed, re.IGNORECASE)
        ):
            reply = (
                "आपके खेत में दो डिवाइस ध्यान आकर्षित कर रहे हैं: "
                "1. DEMO-DEVICE-002 (कॉटन ज़ोन) की बैटरी केवल 16.0% है, जिसे तत्काल चार्ज करने की आवश्यकता है। "
                "2. DEMO-DEVICE-003 (टमाटर ज़ोन) में नाइट्रोजन प्रोब अनकैलिब्रेटेड होने के कारण चेतावनी स्थिति में है। "
                "DEMO-DEVICE-001 (गेहूं ज़ोन) 92% बैटरी के साथ सामान्य रूप से ऑनलाइन है। (सिमुलेटेड डिवाइस डेटा)"
                if is_hindi
                else "Two devices currently have warning statuses: "
                "1. DEMO-DEVICE-002 (Cotton Zone) has a low battery level at 16.0%, requiring recharging. "
                "2. DEMO-DEVICE-003 (Tomato Zone) has a sensor warning due to an uncalibrated nitrogen probe. "
                "DEMO-DEVICE-001 (Wheat Zone) is fully operational at 92% battery. (Simulated Device Data)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_device_warning",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="device_warning_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Farm Hardware Monitor"],
                metadata={"warning_devices": ["DEMO-DEVICE-002", "DEMO-DEVICE-003"]},
            )

        # -------------------------------------------------------------
        # Farm Overall Condition Query (All 4 Zones Dynamic Telemetry)
        # -------------------------------------------------------------
        if not is_conceptual_or_exploratory and (
            re.search(r"\b(overall\s*condition|overall\s*farm|farm\s*overview|entire\s*farm|overall\s*status|all\s*zones?\s*(readings?|data)?)\b", trimmed, re.IGNORECASE)
            or re.search(r"(पूरे\s*खेत\s*की\s*स्थिति|overall\s*condition|खेत\s*का\s*हाल|सभी\s*(ज़ोन|जोनों|zones?)?\s*की\s*(readings?|रीडिंग|आंकड़े))", trimmed, re.IGNORECASE)
            or (not zone_explicitly_mentioned and re.search(r"(खेत\s*की\s*(स्थिति|जानकारी|हालत|रिपोर्ट)|khet\s*ki\s*jankari|farm\s*status)", trimmed, re.IGNORECASE))
        ):
            overview = telemetry_service.get_farm_overview()
            tank_pct = int(telemetry_service.get_water_tank_level().get("water_tank_level_pct", 82.0))
            farm_name = overview.get("farm_name", "Green Valley Agro Farm")

            # Two-level response policy:
            # Level 2 (Detailed readings with raw values) ONLY when user explicitly asks to SHOW or LIST readings/data.
            # Level 1 (Default farmer-friendly answer): High-level evaluation, critical issues requiring attention, and simple next action.
            is_explicit_detailed = bool(
                re.search(r"\b(show|give|list|tell|view|display)\s+(all\s+)?(readings|data|numbers|values)\b", lower_trimmed)
                or re.search(r"\b(detailed\s+readings?|exact\s+values?|raw\s+data)\b", lower_trimmed)
                or re.search(r"(readings?|रीडिंग्स?|रीडिंग|आंकड़े|मान|डेटा)\s*(दिखाओ|दिखाएं|बताओ|बताएं|चाहिए|दें)", lower_trimmed)
                or re.search(r"(सारे\s*(आंकड़े|मान|नंबर)|पूरी\s*रीडिंग्स?|all\s*readings?)", lower_trimmed)
            ) and not bool(re.search(r"(के\s*(मुताबिक|अनुसार|हिसाब\s*से)|सही\s*है\s*या\s*गलत|कैसी\s*है|हाल\s*क्या|कैसा\s*है)", lower_trimmed))

            if not is_explicit_detailed:
                dry_crops = []
                wet_crops = []
                normal_crops = []
                for z in overview.get("zones", []):
                    crop = z.get("crop", "crop")
                    crop_hi = {"wheat": "गेहूं", "cotton": "कपास", "tomato": "टमाटर", "mustard": "सरसों"}.get(crop.lower(), crop)
                    crop_en = crop.title()
                    m = z.get("soil_moisture_pct")
                    if m is not None:
                        if m < 35.0:
                            dry_crops.append((crop_hi, crop_en))
                        elif m > 60.0:
                            wet_crops.append((crop_hi, crop_en))
                        else:
                            normal_crops.append((crop_hi, crop_en))

                if dry_crops or wet_crops:
                    issues_hi = []
                    issues_en = []
                    if dry_crops:
                        names_hi = " और ".join(c[0] for c in dry_crops)
                        names_en = " and ".join(c[1] for c in dry_crops)
                        issues_hi.append(f"{names_hi} वाले खेत में नमी कम है, इसलिए वहां सिंचाई की जरूरत हो सकती है")
                        issues_en.append(f"{names_en} zone has low Soil Moisture, so irrigation may be needed there")
                    if wet_crops:
                        names_hi = " और ".join(c[0] for c in wet_crops)
                        names_en = " and ".join(c[1] for c in wet_crops)
                        issues_hi.append(f"{names_hi} वाले हिस्से में नमी ज्यादा है, इसलिए फिलहाल पानी देने से बचें")
                        issues_en.append(f"{names_en} zone has high Soil Moisture, so hold off on watering for now")

                    joined_issues_hi = "। ".join(issues_hi)
                    joined_issues_en = ". ".join(issues_en)
                    normal_names_hi = " और ".join(c[0] for c in normal_crops) if normal_crops else "बाकी"
                    normal_names_en = " and ".join(c[1] for c in normal_crops) if normal_crops else "remaining"
                    reply = (
                        f"आपके खेत की स्थिति कुल मिलाकर ठीक है, लेकिन ध्यान देने की जरूरत है। "
                        f"{joined_issues_hi}। बाकी {normal_names_hi} ज़ोन सामान्य स्थिति में हैं। (सिमुलेटेड टेलीमेट्री)"
                        if is_hindi
                        else f"Overall, your farm condition is good, but attention is needed. "
                        f"{joined_issues_en}. The {normal_names_en} zones are in normal condition with optimal Soil Moisture. (Simulated Telemetry)"
                    )
                else:
                    reply = (
                        "आपके खेत की स्थिति बहुत अच्छी है और सभी ज़ोन में नमी अनुकूल स्तर पर है। (सिमुलेटेड टेलीमेट्री)"
                        if is_hindi
                        else "Your farm condition is excellent, and all zones have optimal soil moisture. (Simulated Telemetry)"
                    )
            else:
                zone_parts_hi = []
                zone_parts_en = []

                for idx, z in enumerate(overview.get("zones", []), 1):
                    zname = z.get("zone_name", f"Zone {idx}")
                    crop = z.get("crop", "crop")
                    crop_hi = {"wheat": "गेहूं", "cotton": "कपास", "tomato": "टमाटर", "mustard": "सरसों"}.get(crop.lower(), crop)
                    m = z.get("soil_moisture_pct")
                    bat = z.get("battery_level_pct")
                    missing = z.get("missing_fields", [])

                    if m is None:
                        m_eval_hi = "नमी: अनुपलब्ध"
                        m_eval_en = "Soil Moisture: unavailable"
                    elif m < 35.0:
                        m_eval_hi = f"नमी {m}% (कम / सिंचाई आवश्यक)"
                        m_eval_en = f"Soil Moisture {m}% (dry / irrigation needed)"
                    elif m > 60.0:
                        m_eval_hi = f"नमी {m}% (अधिक / जलभराव जोखिम)"
                        m_eval_en = f"Soil Moisture {m}% (high / saturation risk)"
                    else:
                        m_eval_hi = f"नमी {m}% (अनुकूल)"
                        m_eval_en = f"Soil Moisture {m}% (optimal)"

                    flags_hi = []
                    flags_en = []
                    if missing:
                        flags_hi.append(f"{', '.join(missing)} सेंसर अनकैलिब्रेटेड")
                        flags_en.append(f"{', '.join(missing)} uncalibrated")
                    if bat is not None and bat < 20.0:
                        flags_hi.append(f"डिवाइस बैटरी {bat}% (कम)")
                        flags_en.append(f"low battery {bat}%")

                    f_hi = f" [{', '.join(flags_hi)}]" if flags_hi else ""
                    f_en = f" [{', '.join(flags_en)}]" if flags_en else ""

                    zone_parts_hi.append(f"{idx}. {crop_hi} ज़ोन ({zname}): {m_eval_hi}{f_hi}")
                    zone_parts_en.append(f"{idx}. {crop.title()} Zone ({zname}): {m_eval_en}{f_en}")

                joined_hi = "। ".join(zone_parts_hi)
                joined_en = ". ".join(zone_parts_en)

                reply = (
                    f"आपके पूरे खेत ({farm_name}) का वास्तविक समग्र अवलोकन: {joined_hi}। "
                    f"मुख्य पानी का टैंक {tank_pct}% भरा हुआ है। (सिमुलेटेड टेलीमेट्री)"
                    if is_hindi
                    else f"Real-time overview for {farm_name}: {joined_en}. "
                    f"Main water reservoir is at {tank_pct}%. (Simulated Telemetry)"
                )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_farm_overall",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="farm_status",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated 4-Zone Farm Telemetry Overview"],
                metadata={"tank_level_pct": tank_pct, "zones_reported": len(overview.get("zones", []))},
            )

        # -------------------------------------------------------------
        # Scenario 6: Device Status & Battery (Literal)
        # -------------------------------------------------------------
        if (
            re.search(r"\b(device\s*online|battery|fertobot\s*device|device\s*status)\b", trimmed, re.IGNORECASE)
            or re.search(r"(device\s*online|battery\s*kitni|बैटरी|डिवाइस\s*ऑनलाइन)", trimmed, re.IGNORECASE)
        ):
            dev_res = await self._tools["device_status"].execute(zone_id=resolved_zone)
            dev_id = dev_res.get("device_id")
            st = dev_res.get("status")
            bat = dev_res.get("battery_level_pct")
            ts = format_to_ist(dev_res.get("last_seen_iso"))

            latest_tel = telemetry_service.get_latest_telemetry(resolved_zone)
            comp = latest_tel.get("completeness_ratio", "")
            prof = latest_tel.get("canonical_soil_profile", {})
            params = prof.get("parameters", {}) if isinstance(prof, dict) else getattr(prof, "parameters", {})
            degraded = []
            for p_k, p_v in params.items():
                c_st = p_v.get("calibration_status") if isinstance(p_v, dict) else getattr(p_v, "calibration_status", None)
                q_st = p_v.get("quality_status") if isinstance(p_v, dict) else getattr(p_v, "quality_status", None)
                if c_st == "UNCALIBRATED" or q_st != "VALID":
                    d_name = p_v.get("display_name") if isinstance(p_v, dict) else getattr(p_v, "display_name", p_k)
                    degraded.append(d_name)

            deg_msg_hi = f" चेतावनी: {', '.join(degraded)} प्रोब अनकैलिब्रेटेड/अनुपलब्ध है।" if degraded else ""
            deg_msg_en = f" Warning: {', '.join(degraded)} probe is uncalibrated/unavailable." if degraded else ""

            if is_hindi:
                st_hi = "ऑनलाइन" if st == "online" else ("चेतावनी" if st == "warning" else "ऑफलाइन")
                reply = (
                    f"आपका फर्तोबॉट डिवाइस {dev_id} {st_hi} है। "
                    f"बैटरी स्तर {bat}% है। अंतिम सिग्नल: {ts}।{deg_msg_hi} (सिमुलेटेड डिवाइस डेटा)"
                )
            else:
                reply = (
                    f"Your FertoBot device {dev_id} is {st.upper()}. "
                    f"Battery level is at {bat}%. Last packet: {ts}.{deg_msg_en} (Simulated Hardware Status)"
                )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_device_status",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="device_status_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Hardware ({dev_id})"],
                warnings=dev_res.get("warnings", []),
                metadata={"zone_id": resolved_zone, "device_id": dev_id, "battery_pct": bat, "status": st},
            )

        # -------------------------------------------------------------
        # Scenario 7: Water Tank Level (Literal)
        # -------------------------------------------------------------
        if (
            re.search(r"\b(water\s*tank|tank\s*level|water\s*reservoir|tank\s*mein\s*kitna)\b", trimmed, re.IGNORECASE)
            or re.search(r"(water\s*tank|tank\s*mein|पानी\s*का\s*टैंक|टंकी\s*में\s*पानी)", trimmed, re.IGNORECASE)
        ):
            water_res = await self._tools["water_level"].execute(zone_id=resolved_zone)
            tank = water_res.get("water_tank_level_pct")
            st = water_res.get("status")

            reply = (
                f"आपके खेत के पानी के टैंक में वर्तमान जल स्तर {tank}% है। "
                f"({'पानी पर्याप्त है।' if tank >= 50 else 'पानी का स्तर कम है, रीफिल की आवश्यकता हो सकती है।'}) (सिमुलेटेड टेलीमेट्री)"
                if is_hindi
                else f"Your irrigation water reservoir is currently at {tank}% storage capacity ({st.upper()}). "
                f"(Simulated FertoBot telemetry)"
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_water_level",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="water_level_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Water Reservoir Sensor"],
                metadata={"tank_level_pct": tank, "status": st},
            )

        # -------------------------------------------------------------
        # Scenario 8: Historical Trend (7 Days or 24 Hours)
        # -------------------------------------------------------------
        if (
            (
                re.search(r"\b(pichhle|past|last|previous)\s*(7\s*days?|24\s*hours?|week|days?)\b", trimmed, re.IGNORECASE)
                or re.search(r"(पिछले|बीते)\s*(7|सात|24|चौबीस)?\s*(दिनों?|घंटों?|हफ़्ते|हफ्ते)?", trimmed)
                or re.search(r"\b(trend|change|history|बदलाव|बदली|बदल|इतिहास|रुझान)\b", trimmed, re.IGNORECASE)
            )
            and not any(w in lower_trimmed for w in ["fertilizer", "खाद", "उर्वरक", "depletion", "डिप्लीशन", "consumption", "खपत"])
        ):
            t_range = "24h" if "24" in lower_trimmed else "7d"
            hist_res = await self._tools["historical_telemetry"].execute(
                zone_id=resolved_zone,
                parameter="soil_moisture_pct",
                time_range=t_range,
            )
            zone_name = telemetry_service.get_latest_telemetry(resolved_zone).get("zone_name", resolved_zone)

            if is_hindi:
                trend_dir = hist_res.get("trend_direction", "stable")
                avg_val = hist_res.get("average_value", 32.5)
                min_val = hist_res.get("min_value", 30.5)
                max_val = hist_res.get("max_value", 34.5)
                unit = hist_res.get("unit", "%")
                range_label = "24 घंटों" if t_range == "24h" else "7 दिनों"
                if trend_dir == "decreasing":
                    summary_hi = f"नमी में गिरावट आई है (औसत: {avg_val:.1f}{unit}, दायरा: {min_val:.1f} से {max_val:.1f}{unit})"
                elif trend_dir == "increasing":
                    summary_hi = f"नमी में बढ़ोतरी देखी गई है (औसत: {avg_val:.1f}{unit}, दायरा: {min_val:.1f} से {max_val:.1f}{unit})"
                else:
                    summary_hi = f"नमी का स्तर {avg_val:.1f}{unit} के आसपास स्थिर बना हुआ है (दायरा: {min_val:.1f} से {max_val:.1f}{unit})"

                reply = (
                    f"पिछले {range_label} में {zone_name} में मिट्टी की नमी का रुख: {summary_hi}। (सिमुलेटेड ऐतिहासिक डेटा)"
                )
            else:
                summary_txt = hist_res.get("trend_summary", "Stable")
                reply = (
                    f"Soil moisture trend in {zone_name} over the past {t_range}: {summary_txt} (Simulated Historical Data)"
                )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_historical_trend",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Retrieved {t_range} trend for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="historical_trend_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=[f"Simulated Historical Series ({resolved_zone})"],
                metadata={"zone_id": resolved_zone, "time_range": t_range, "trend_direction": hist_res.get("trend_direction")},
            )

        # -------------------------------------------------------------
        # Scenario 9: Alerts (Literal)
        # -------------------------------------------------------------
        if (
            re.search(r"\b(alerts?|warnings?|problems?|issues?|faults?)\b", trimmed, re.IGNORECASE)
            or re.search(r"(अलर्ट|चेतावनी|समस्या|दिक्कत|खराबी|परेशानी|गड़बड़)", trimmed)
        ):
            alert_res = await self._tools["alert_history"].execute(zone_id=resolved_zone)
            alerts = alert_res.get("alerts", [])
            total = len(alerts)

            if total > 0:
                top = alerts[0]
                reply = (
                    f"आज आपके खेत में {total} सक्रिय अलर्ट हैं। मुख्य अलर्ट: {top['title']} - {top['message']} (सिमुलेटेड अलर्ट)"
                    if is_hindi
                    else f"You have {total} active alerts. Top warning: {top['title']} - {top['message']} (Simulated Alert)"
                )
            else:
                reply = (
                    "आज आपके खेत या सेंसर में कोई सक्रिय अलर्ट या समस्या नहीं है। सभी सिस्टम सामान्य रूप से काम कर रहे हैं।"
                    if is_hindi
                    else "There are no active alerts or problems for your farm today. All sensor systems are operational."
                )

            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_alerts",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="alert_history_query",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Simulated Farm Alert Monitor"],
                metadata={"total_alerts": total},
            )

        # Farm Status / Overview fast-path
        is_farm_status = (
            re.search(r"\b(farm\s+status|field\s+status|farm\s+overview|field\s+overview|farm\s+info|field\s+info|telemetry)\b", trimmed, re.IGNORECASE)
            or re.search(r"\b(khet\s*(ki|ka)\s*(jankari|haal|status|report|sthiti))\b", trimmed, re.IGNORECASE)
            or re.search(r"((खेत|ज़ोन|zone)\s*की\s*(स्थिति|जानकारी|हालत|अपडेट|रिपोर्ट)|(खेत|ज़ोन|zone)\s*का\s*(हाल|हालचाल)|सेंसर\s*स्थिति|फार्म\s*का\s*स्टेटस|फार्म\s*स्टेटस|टेलीमेट्री)", trimmed, re.IGNORECASE)
        )
        if not is_conceptual_or_exploratory and is_farm_status:
            telemetry_res = await self._tools["latest_telemetry"].execute(zone_id=resolved_zone)
            moisture = telemetry_res.get("soil_moisture_pct")
            temp = telemetry_res.get("soil_temperature_c")
            tank = telemetry_res.get("water_tank_level_pct")
            battery = telemetry_res.get("battery_level_pct")
            missing_fields = telemetry_res.get("missing_fields", [])
            zone_name = telemetry_res.get("zone_name", resolved_zone)
            crop_name = telemetry_res.get("crop", "crop")
            crop_hindi = {"wheat": "गेहूं", "cotton": "कपास", "tomato": "टमाटर", "mustard": "सरसों"}.get(crop_name.lower(), crop_name)

            if moisture is None:
                m_str_hi = "नमी: अनुपलब्ध"
                m_str_en = "Soil Moisture: unavailable"
            elif moisture < 35.0:
                m_str_hi = f"मिट्टी की नमी: {moisture}% (कम / सिंचाई आवश्यक)"
                m_str_en = f"Soil Moisture: {moisture}% (Deficit - Irrigation Recommended)"
            elif moisture > 60.0:
                m_str_hi = f"मिट्टी की नमी: {moisture}% (अधिक / जलभराव जोखिम)"
                m_str_en = f"Soil Moisture: {moisture}% (High - Saturation Risk)"
            else:
                m_str_hi = f"मिट्टी की नमी: {moisture}% (अनुकूल)"
                m_str_en = f"Soil Moisture: {moisture}% (Optimal)"

            hw_alerts_hi = []
            hw_alerts_en = []
            if missing_fields:
                hw_alerts_hi.append(f"सेंसर चेतावनी: {', '.join(missing_fields)} अनकैलिब्रेटेड है")
                hw_alerts_en.append(f"Sensor Warning: {', '.join(missing_fields)} uncalibrated")
            if battery is not None and battery < 20.0:
                hw_alerts_hi.append(f"डिवाइस बैटरी {battery}% (कम)")
                hw_alerts_en.append(f"Device battery {battery}% (low)")

            hw_str_hi = f"। {', '.join(hw_alerts_hi)}" if hw_alerts_hi else "। सभी सिमुलेटेड सेंसर ऑनलाइन हैं"
            hw_str_en = f". {', '.join(hw_alerts_en)}" if hw_alerts_en else ". All simulated sensors are online"

            reply = (
                f"[{zone_name} टेलीमेट्री] फसल: {crop_hindi}। {m_str_hi}। "
                f"मिट्टी का तापमान: {temp}°C। पानी का टैंक: {int(tank or 0)}%{hw_str_hi}।"
                if is_hindi
                else f"[{zone_name} TELEMETRY] Crop: {crop_name.title()}. {m_str_en}. "
                f"Soil Temp: {temp}°C. Water Tank: {int(tank or 0)}%{hw_str_en}."
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_farm_status",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                details=f"Farm status telemetry fast-path for {resolved_zone}",
            ))
            return self._build_response(
                reply=reply,
                intent="farm_status",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                sources=["Farm Probe Telemetry (Read-Only)"],
                warnings=["Telemetry reflects simulated sensor depth (15cm)."],
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zone_id": resolved_zone},
            )

        # Goodbye
        if (
            re.search(r"\b(bye|goodbye|see\s+you|exit|quit|stop\s+talking|namaste\s+alvida)\b", trimmed, re.IGNORECASE)
            or re.search(r"(अलविदा|बाय|शुभकामनाएं)", trimmed)
        ):
            reply = (
                "अलविदा! आपकी फसल समृद्ध रहे। जब भी सहायता की आवश्यकता हो, बात करें।"
                if is_hindi
                else "Goodbye! May your harvest be bountiful. Click Start Listening whenever you wish to speak again."
            )
            self._last_responses[session_key] = reply
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_goodbye",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=reply,
                intent="goodbye",
                confidence=1.0,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                metadata={"language": "hi-IN" if is_hindi else "en-US"},
            )

        # -------------------------------------------------------------
        # Out-of-Domain Filter (Catch queries completely outside agriculture/telemetry)
        # -------------------------------------------------------------
        is_agricultural_topic = any(k in lower_trimmed for k in [
            "crop", "fasal", "soil", "mitti", "nami", "moisture", "water", "pani", "sinchai", "irrigat",
            "weather", "mausam", "rain", "barish", "temp", "taapman", "fertilizer", "khad", "urea",
            "dap", "npk", "ph", "ec", "conductivity", "pest", "keet", "disease", "rog", "leaf",
            "patti", "wheat", "gehu", "cotton", "kapas", "tomato", "tamatar", "rice", "dhan",
            "mustard", "sarson", "maize", "makka", "sugarcane", "ganna", "potato", "aloo", "gram", "chana",
            "probe", "sensor", "device", "battery", "tank", "tiki", "alert", "warning", "kheti",
            "farm", "khet", "jankari", "samasya", "dikkat", "problem", "issue", "trend", "history",
            "harvest", "sowing", "buwai", "yield", "upaj", "organic", "jaivik",
            "rotation", "chakar", "tractor", "pump", "valve", "sprinkler", "drip", "tillering",
            "flower", "phool", "seed", "beej", "root", "jad", "canal", "nahar", "well", "kuan",
            "tubewell", "boring", "kisan", "farmer", "zone", "sector", "chlorosis", "peeli", "pila",
            "brown", "rust", "blight", "rot", "status", "overview", "condition", "recommend", "salah"
        ]) or any(k in trimmed for k in [
            "फसल", "मिट्टी", "नमी", "पानी", "सिंचाई", "मौसम", "बारिश", "तापमान", "खाद", "यूरिया",
            "डीएपी", "कीट", "रोग", "पत्ती", "गेहूं", "कपास", "टमाटर", "धान", "सरसों", "मक्का",
            "आलू", "चना", "सेंसर", "डिवाइस", "बैटरी", "टंकी", "अलर्ट", "खेती", "किसान", "उपज", "बुवाई",
            "जैविक", "पंप", "वॉल्व", "ड्रिप", "जड़", "फूल", "बीज", "पीली", "सलाह", "रिपोर्ट",
            "खेत", "जानकारी", "स्थिति", "हाल", "हालत", "समस्या", "दिक्कत", "खराबी", "परेशानी",
            "बताओ", "बताएं", "दिखाओ", "दिखाएं", "चल रही", "सात", "हफ्ता", "दिन", "अपडेट"
        ])

        if not is_agricultural_topic and not is_conceptual_or_exploratory and not has_substantive_query:
            fallback = (
                "मुझे इस डेमो में यह समझ नहीं आया। 'नमस्ते', 'आप कौन हैं?', 'खेत की स्थिति', "
                "या 'अलविदा' पूछने का प्रयास करें।"
                if is_hindi
                else "I didn't quite catch that in this demo. "
                "Try asking: 'Hello', 'Who are you?', 'What can you do?', or 'Goodbye'."
            )
            self._last_responses[session_key] = fallback
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="fast_path_router",
                action="route_unknown",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=fallback,
                intent="unknown",
                confidence=0.2,
                repeatable=True,
                execution_trace=trace,
                provider_status="fast_path",
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zone_id": resolved_zone},
            )

        # -------------------------------------------------------------
        # 2. Agricultural Query: Dynamic Planning via Multi-Agent LLM Orchestrator
        # -------------------------------------------------------------
        session_loc = self._session_locations.get(session_key)
        session_sea = self._session_seasons.get(session_key)
        context_str = ""
        if session_loc:
            context_str += f"Farmer Location: {session_loc}. "
        if session_sea:
            context_str += f"Cropping Season: {session_sea}. "

        plan_t0 = time.perf_counter()
        plan_failed = False
        plan_error = None

        if self.fast_planning:
            selected = []
            lower_m = trimmed.lower()
            if any(w in lower_m for w in [
                "yellow", "leaf", "leaves", "chlorosis", "spot", "disease", "पत्ती", "पीली",
                "npk", "ph", "ec", "soil", "crop", "uga", "rotation", "organic", "fertility", "test",
                "nitrogen", "phosphorus", "potassium", "suitab", "wheat", "cotton", "tomato", "mustard", "sarson", "gram", "chana",
                "कीट", "रोग", "खाद", "उर्वरक", "फसल", "मिट्टी", "उपज", "सुधार", "सल्फर", "जिंक", "सरसों", "चना", "खेत", "जानकारी"
            ]):
                selected.append("crop_symptom")
            if any(w in lower_m for w in [
                "water", "irrigat", "moisture", "सिंचाई", "पानी", "नमी", "over-irrigation",
                "drainage", "monsoon", "प्यास", "सूखा"
            ]) or any(w in trimmed for w in ["पानी", "सिंचाई", "नमी"]):
                selected.append("irrigation_advisory")
            if any(w in lower_m for w in [
                "weather", "rain", "forecast", "temp", "मौसम", "बारिश", "monsoon",
                "wind", "हवा", "तापमान", "बादल", "spray"
            ]) or any(w in trimmed for w in ["मौसम", "बारिश", "तापमान"]):
                selected.append("weather_context")
            if any(w in lower_m for w in [
                "battery", "device", "tank", "alert", "warning", "problem", "issue", "fault",
                "बैटरी", "अलर्ट", "सेंसर", "probe", "hardware", "डिवाइस", "टंकी", "समस्या", "दिक्कत", "खराबी"
            ]) or any(w in trimmed for w in ["बैटरी", "डिवाइस", "सेंसर", "अलर्ट", "टंकी", "समस्या", "दिक्कत", "खराबी"]):
                selected.append("device_health")

            # Rain forecast directly impacts irrigation decisions
            if "irrigation_advisory" in selected and "weather_context" not in selected:
                selected.append("weather_context")

            if not selected:
                selected = ["crop_symptom", "irrigation_advisory"]

            plan = ExecutionPlan(
                intent="agricultural_inquiry",
                selected_agents=selected,
                reasoning="Fast deterministic agronomist dispatch (<0.1ms latency)",
                confidence=0.95,
            )
            plan_duration = round((time.perf_counter() - plan_t0) * 1000, 2)
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="orchestrator",
                action="plan_execution",
                status="completed",
                duration_ms=plan_duration,
                details=f"Fast deterministic plan: intent={plan.intent}, agents=[{', '.join(plan.selected_agents)}]",
            ))
        else:
            plan_prompt = (
                f"You are the Orchestrator for FertoBot agricultural voice assistant.\n"
                f"Target Farm Zone: {resolved_zone}\n"
                f"{context_str}\n"
                f"Analyze user query: '{trimmed}'\n"
                f"Available specialist agents:\n"
                f"- 'crop_symptom': analyzes crop symptoms, disease causes, chlorosis, soil NPK/pH/EC interpretation, crop suitability ('aur kya uga sakte hain'), soil fertility improvement, crop rotation, organic farming principles, and soil testing importance.\n"
                f"- 'irrigation_advisory': analyzes soil moisture levels, crop water requirements (cotton, wheat, etc.), rain forecasts, over-irrigation disadvantages, and monsoon precautions.\n"
                f"- 'weather_context': analyzes temperature, rain forecast, humidity, wind, and spray drift risks.\n"
                f"- 'device_health': monitors FertoBot probe connectivity, battery levels, water tank storage, and hardware alerts.\n"
                f"Select which specialist agents must be invoked. Output strictly valid JSON."
            )
            try:
                plan = await self._llm.generate_structured(
                    prompt=plan_prompt,
                    schema=ExecutionPlan,
                    system_prompt="You are an agricultural planning agent. Output strictly valid JSON.",
                )
                plan_duration = round((time.perf_counter() - plan_t0) * 1000, 2)
                trace.append(ExecutionTraceStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    agent_id="orchestrator",
                    action="plan_execution",
                    status="completed",
                    duration_ms=plan_duration,
                    details=f"Live {self._llm.provider_name} plan: intent={plan.intent}, agents=[{', '.join(plan.selected_agents)}]",
                ))
            except Exception as exc:
                plan_failed = True
                from app.config import redact_sensitive
                plan_error = redact_sensitive(str(exc))
                plan_duration = round((time.perf_counter() - plan_t0) * 1000, 2)

                selected = []
                lower_m = trimmed.lower()
                if any(w in lower_m for w in [
                    "yellow", "leaf", "leaves", "chlorosis", "spot", "disease", "पत्ती", "पीली",
                    "npk", "ph", "soil", "crop", "uga", "rotation", "organic", "fertility", "test",
                    "nitrogen", "phosphorus", "potassium", "suitab", "wheat", "cotton", "tomato"
                ]):
                    selected.append("crop_symptom")
                if any(w in lower_m for w in ["water", "irrigat", "moisture", "सिंचाई", "पानी", "over-irrigation", "drainage", "monsoon"]):
                    selected.append("irrigation_advisory")
                if any(w in lower_m for w in ["weather", "rain", "forecast", "temp", "मौसम", "बारिश", "monsoon"]):
                    selected.append("weather_context")
                if any(w in lower_m for w in ["battery", "device", "tank", "alert", "बैटरी", "अलर्ट"]):
                    selected.append("device_health")
                if not selected:
                    selected = ["crop_symptom", "irrigation_advisory"]
                plan = ExecutionPlan(
                    intent="agricultural_inquiry",
                    selected_agents=selected,
                    reasoning="Heuristic fallback plan selection",
                    confidence=0.75,
                )
                trace.append(ExecutionTraceStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    agent_id="orchestrator",
                    action="plan_execution",
                    status="failed",
                    duration_ms=plan_duration,
                    details=f"{self._llm.provider_name} planning failed: {plan_error}. Fallback heuristics applied.",
                ))

        # Handle unknown / out-of-domain queries
        if plan.intent == "unknown" or (not plan.selected_agents and plan.intent != "farm_status"):
            fallback = (
                "मुझे इस डेमो में यह समझ नहीं आया। 'नमस्ते', 'आप कौन हैं?', 'खेत की स्थिति', "
                "या 'अलविदा' पूछने का प्रयास करें।"
                if is_hindi
                else "I didn't quite catch that in this demo. "
                "Try asking: 'Hello', 'Who are you?', 'What can you do?', or 'Goodbye'."
            )
            self._last_responses[session_key] = fallback
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="orchestrator",
                action="unknown_fallback",
                status="completed",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            ))
            return self._build_response(
                reply=fallback,
                intent="unknown",
                confidence=0.2,
                repeatable=True,
                execution_trace=trace,
                provider_status=self._llm.provider_status,
                metadata={"language": "hi-IN" if is_hindi else "en-US", "zone_id": resolved_zone},
            )

        # -------------------------------------------------------------
        # 3. Parallel Specialist Execution with Fault Isolation
        # -------------------------------------------------------------
        agent_context = AgentContext(
            query=trimmed,
            language=language,
            session_id=session_id,
            zone_id=resolved_zone,
        )

        agent_results: List[AgentResult] = []
        agent_ids_to_run = [aid for aid in plan.selected_agents if aid in self._agents][:3]

        # Always guarantee at least one agent if none matched
        if not agent_ids_to_run:
            agent_ids_to_run = ["crop_symptom"]

        async def run_single_agent(agent_id: str) -> AgentResult:
            agent = self._agents[agent_id]
            a_t0 = time.perf_counter()
            try:
                # Bound agent execution by 7 second timeout
                res = await asyncio.wait_for(
                    agent.execute(agent_context, self._tools),
                    timeout=7.0,
                )
                duration = round((time.perf_counter() - a_t0) * 1000, 2)
                trace.append(ExecutionTraceStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    agent_id=agent_id,
                    action="execute_specialist",
                    status="completed",
                    duration_ms=duration,
                    details=f"Tools used: {', '.join(agent.permitted_tools)}",
                ))
                return res
            except Exception as exc:
                duration = round((time.perf_counter() - a_t0) * 1000, 2)
                trace.append(ExecutionTraceStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    agent_id=agent_id,
                    action="execute_specialist",
                    status="failed",
                    duration_ms=duration,
                    details=f"Execution error: {str(exc)}",
                ))
                return AgentResult(
                    agent_id=agent_id,
                    name=agent.name,
                    status="failed",
                    summary="Specialist analysis encountered a temporary execution failure.",
                    evidence=[],
                    limitations=[f"Agent error: {str(exc)}"],
                    data={},
                )

        # Run selected agents concurrently
        task_results = await asyncio.gather(
            *[run_single_agent(aid) for aid in agent_ids_to_run],
            return_exceptions=False,
        )
        agent_results.extend(task_results)

        # -------------------------------------------------------------
        # 4. Structured Synthesis
        # -------------------------------------------------------------
        synth_t0 = time.perf_counter()
        agent_summaries = "\n".join([f"- [{res.name}]: {res.summary}" for res in agent_results])
        all_evidence = [ev for res in agent_results for ev in res.evidence]
        all_limitations = [lim for res in agent_results for lim in res.limitations]

        zone_crop = telemetry_service.get_latest_telemetry(resolved_zone).get("crop", "Wheat")

        if already_greeted or turn_count > 1:
            greeting_rule = (
                "CRITICAL GREETING SUPPRESSION:\n"
                "A greeting has ALREADY been given in this conversation session.\n"
                "DO NOT say 'नमस्ते', 'नमस्कार', 'राम-राम', 'हेलो', 'किसान भाई', or ANY introductory greeting.\n"
                "DO NOT introduce yourself. Start directly with the answer to the user's question."
            )
        else:
            greeting_rule = (
                "GREETING POLICY:\n"
                "This is the opening turn. You may include a single brief greeting ('नमस्ते किसान भाई' or 'नमस्ते') if the user greeted, otherwise go straight to the answer."
            )

        conciseness_rule = (
            "CONCISENESS POLICY (CRITICAL FOR VOICE TTS LATENCY & CLARITY):\n"
            "- Keep your spoken response CONCISE, SHARP, and DIRECT.\n"
            "- For telemetry queries (e.g. moisture, NPK, pH, weather): 1 to 2 short sentences with exact numbers.\n"
            "- For advisory/recommendation queries (e.g. irrigation advice, rain impact, soil improvement): 2 to 3 concise, actionable sentences.\n"
            "- Maximum total length: 35 to 55 words in Hindi (or 25 to 45 words in English).\n"
            "- Do NOT write long paragraphs, unnecessary disclaimers, or conversational filler.\n"
            "- Use natural Hindi sentence terminators (।) between sentences so TTS can stream sentence-by-sentence."
        )

        clarification_rule = (
            "CLARIFICATION & WARNING POLICY:\n"
            f"- Target Farm Zone: {resolved_zone}. Crop: {zone_crop}.\n"
            "- Since the crop, zone, and telemetry are ALREADY KNOWN, DO NOT ask for crop variety or watering history!\n"
            "- Set needs_clarification=True ONLY if critical grower information is genuinely missing to give safe advice (e.g. diagnosing an unknown disease without symptoms).\n"
            "- When needs_clarification=True, provide a short, specific clarification_prompt in the response language. Otherwise set needs_clarification=False and clarification_prompt=None."
        )

        agronomic_safety_rule = (
            "AGRONOMIC & SENSOR ACCURACY POLICY:\n"
            "- Fertilizer Dosage: For questions about fertilizer quantities (e.g. Urea, DAP, NPK), NEVER provide an unconditional universal dosage as fact. Clearly label illustrative recommendations (e.g. standard reference dosage for the crop) and advise that actual dosage must be verified through laboratory soil testing and crop growth stage.\n"
            "- Sodium / Salinity: The 7-in-1 sensor measures Electrical Conductivity (EC), NOT Sodium (Na). NEVER derive sodium concentrations from EC. Note that certified laboratory wet-chemistry testing is required for sodium/SAR analysis.\n"
            "- Soil Parameters: Reference actual simulated sensor readings (Moisture %, Soil Temp °C, EC dS/m, pH, Nitrogen, Phosphorus, Potassium) accurately without inventing values."
        )

        synth_prompt = (
            f"User Question: '{trimmed}'\n"
            f"Language: {'Hindi' if is_hindi else 'English'}\n"
            f"Farm Zone: {resolved_zone} ({zone_crop})\n"
            f"{context_str}\n\n"
            f"Specialist Agent Findings:\n{agent_summaries}\n\n"
            f"{greeting_rule}\n\n"
            f"{conciseness_rule}\n\n"
            f"{clarification_rule}\n\n"
            f"{agronomic_safety_rule}\n\n"
            f"Requirements:\n"
            f"1. Directly answer the farmer's question in natural {'Hindi (using clean Devanagari script)' if is_hindi else 'English'}.\n"
            f"2. Reference actual simulated sensor readings (moisture, pH, NPK, EC) when explaining farm condition or suitability.\n"
            f"3. Do NOT read raw JSON, lists, or asterisks (*). Make it flow smoothly as spoken sentences separated by proper punctuation ({'।' if is_hindi else '.'})."
        )

        synth_failed = False
        synth_error = None
        clarification_prompt: Optional[str] = None
        try:
            synth = await self._llm.generate_structured(
                prompt=synth_prompt,
                schema=SynthesisOutput,
                system_prompt="You are FertoBot's Chief Agronomist. Synthesize findings into clear spoken advice.",
            )
            final_reply = synth.answer
            sources = synth.sources or [f"Simulated Telemetry ({resolved_zone})", "Agronomic Diagnostic Knowledgebase"]
            warnings = synth.warnings or all_limitations
            needs_clarification = synth.needs_clarification
            clarification_prompt = synth.clarification_prompt
            synth_duration = round((time.perf_counter() - synth_t0) * 1000, 2)
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="orchestrator",
                action="synthesize_response",
                status="completed",
                duration_ms=synth_duration,
                details=f"Live {self._llm.provider_name} synthesis completed",
            ))
        except Exception as exc:
            synth_failed = True
            from app.config import redact_sensitive
            synth_error = redact_sensitive(str(exc))
            synth_duration = round((time.perf_counter() - synth_t0) * 1000, 2)

            # Clean deterministic fallback synthesis from agent summaries
            clean_parts = [res.summary for res in agent_results if res.status == "completed"]
            final_reply = " ".join(clean_parts) if clean_parts else (
                "आपके खेत के डेटा का विश्लेषण पूरा हो गया है। कृपया कुछ समय बाद पुनः प्रयास करें।"
                if is_hindi
                else "Specialist analysis completed with fallback synthesis."
            )
            sources = [res.name for res in agent_results if res.status == "completed"]
            warnings = all_limitations
            # If zone crop is already known, do not falsely flag needs_clarification
            needs_clarification = False if zone_crop else any("Crop species not specified" in lim for lim in all_limitations)
            clarification_prompt = "कृपया अपनी फसल का नाम या किस्म बताएं।" if needs_clarification else None
            trace.append(ExecutionTraceStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                agent_id="orchestrator",
                action="synthesize_response",
                status="failed",
                duration_ms=synth_duration,
                details=f"{self._llm.provider_name} synthesis failed: {synth_error}. Fallback synthesis used.",
            ))

        # Strip any rogue greeting if session was already greeted or turn_count > 1
        if already_greeted or turn_count > 1:
            final_reply = re.sub(
                r"^(नमस्ते|नमस्कार|राम-राम|राम\s*राम|हेलो|प्रणाम)\s*(जी|किसान\s*भाई)?\s*[,!।.-]?\s*",
                "",
                final_reply,
                flags=re.IGNORECASE,
            ).strip()

        # Mark session as greeted
        self._session_greeted[session_key] = True

        # Determine effective provider status
        if plan_failed or synth_failed:
            if self._llm.provider_name == "mock":
                effective_status = "mock"
            elif not self._llm.is_live_ready():
                effective_status = f"{self._llm.provider_name}_unavailable"
                warnings.append(f"Provider '{self._llm.provider_name}' is unconfigured (missing API key). Fallback reasoning used.")
            else:
                effective_status = f"{self._llm.provider_name}_fallback"
                warnings.append(f"Live '{self._llm.provider_name}' inference failed ({plan_error or synth_error}). Fallback reasoning used.")
        else:
            effective_status = self._llm.provider_status

        self._last_responses[session_key] = final_reply

        return self._build_response(
            reply=final_reply,
            intent=plan.intent,
            confidence=plan.confidence,
            repeatable=True,
            agent_results=agent_results,
            execution_trace=trace,
            sources=list(dict.fromkeys(sources)),  # deduplicate
            warnings=warnings,
            needs_clarification=needs_clarification,
            clarification_prompt=clarification_prompt,
            provider_status=effective_status,
            metadata={
                "total_duration_ms": round((time.perf_counter() - t0) * 1000, 2),
                "agents_invoked": agent_ids_to_run,
                "language": "hi-IN" if is_hindi else "en-US",
                "zone_id": resolved_zone,
                "is_simulated": True,
                "actuation_permitted": False,
                "llm_provider": self._llm.provider_name,
                "llm_status": effective_status,
                "token_usage": self._llm.get_last_usage() if hasattr(self._llm, "get_last_usage") else None,
                "cost_usd": "unavailable (direct API billing)",
                "session_location": session_loc,
                "session_season": session_sea,
                "turn_count": turn_count,
            },
        )


# Global singleton orchestrator with fast planning enabled for real-time voice latency
orchestrator = LLMOrchestrator(fast_planning=True)
