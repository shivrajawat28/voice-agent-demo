"""
Deterministic Conversation Provider
Offline, predictable intent matching for repeatable testing and demo verification.
Supports bilingual responses (English and Hindi) for voice clarity testing.
"""
import re
from typing import Optional, Dict
from app.providers.base import BaseConversationProvider
from app.models.conversation import ChatResponse


class DeterministicProvider(BaseConversationProvider):
    def __init__(self):
        # In-memory session store for repeat functionality
        self._last_responses: Dict[str, str] = {}

    async def process_message(
        self,
        message: str,
        language: str = "en-US",
        session_id: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> ChatResponse:
        trimmed = message.strip()
        session_key = session_id or "default"
        is_hindi = language.lower().startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", trimmed)
        )

        # 1. Greeting
        if (
            re.search(
                r"^(hello|hi|hey|greetings|namaste|ram\s*ram|good\s*(morning|afternoon|evening))\b",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(r"\b(hello|hi|hey|namaste)\b", trimmed, re.IGNORECASE)
            or re.search(r"(नमस्ते|नमस्कार|प्रणाम|राम\s*राम)", trimmed)
        ):
            if is_hindi:
                reply = (
                    "नमस्ते! मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ। "
                    "आज मैं आपके खेत की क्या मदद कर सकता हूँ?"
                )
            else:
                reply = (
                    "Hello! I am your FertoBot Voice Assistant running in local demo mode. "
                    "How can I help your farm today?"
                )
            self._last_responses[session_key] = reply
            return ChatResponse(
                success=True,
                reply=reply,
                intent="greeting",
                confidence=1.0,
                repeatable=True,
                metadata={"provider": "deterministic", "language": "hi-IN" if is_hindi else "en-US"},
            )

        # 2. Agent Introduction
        if (
            re.search(
                r"\b(who\s+are\s+you|what\s+is\s+your\s+name|introduce\s+yourself|tell\s+me\s+about\s+yourself)\b",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(r"(आप\s*कौन\s*हैं|तुम्हारा\s*नाम\s*क्या\s*है|अपना\s*परिचय)", trimmed)
        ):
            if is_hindi:
                reply = (
                    "मैं फर्तोबॉट वॉइस एजेंट हूँ, एक एआई कृषि सहायक डेमो। "
                    "मैं किसानों को खेत की टेलीमेट्री और फसल परामर्श में मदद करता हूँ।"
                )
            else:
                reply = (
                    "I am FertoBot Voice Agent, an AI farm assistant demo. "
                    "I help growers check telemetry, explore crop recommendations, and answer farm queries."
                )
            self._last_responses[session_key] = reply
            return ChatResponse(
                success=True,
                reply=reply,
                intent="intro",
                confidence=1.0,
                repeatable=True,
                metadata={"provider": "deterministic", "language": "hi-IN" if is_hindi else "en-US"},
            )

        # 3. Help / Capabilities
        if (
            re.search(
                r"\b(what\s+can\s+you\s+do|help|options|commands|show\s+help|capabilities)\b",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(r"(मदद|सहायता|तुम\s*क्या\s*कर\s*सकते\s*हो)", trimmed)
        ):
            if is_hindi:
                reply = (
                    'आप कह सकते हैं: "नमस्ते", "आप कौन हैं?", "खेत की स्थिति", "दोहराएं", या "अलविदा"। '
                    "यदि माइक्रोफोन उपलब्ध नहीं है तो आप नीचे टेक्स्ट भी लिख सकते हैं।"
                )
            else:
                reply = (
                    'You can say: "Hello", "Who are you?", "Farm status", "Repeat", or "Goodbye". '
                    "You can also test text input if your microphone is unavailable."
                )
            self._last_responses[session_key] = reply
            return ChatResponse(
                success=True,
                reply=reply,
                intent="help",
                confidence=1.0,
                repeatable=True,
                metadata={"provider": "deterministic", "language": "hi-IN" if is_hindi else "en-US"},
            )

        # 4. Repeat
        if (
            re.search(
                r"\b(repeat|say\s+that\s+again|what\s+did\s+you\s+say|repeat\s+last|one\s+more\s+time)\b",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(r"(दोहराएं|फिर\s*से\s*बोलो|दोबारा\s*कहो)", trimmed)
        ):
            last_resp = self._last_responses.get(session_key)
            if last_resp:
                reply = f'दोहरा रहा हूँ: "{last_resp}"' if is_hindi else f'Repeating: "{last_resp}"'
            else:
                reply = (
                    "मैंने अभी तक कुछ नहीं कहा है! शुरू करने के लिए 'नमस्ते' कहें।"
                    if is_hindi
                    else "I haven't said anything yet to repeat! Say 'Hello' or ask 'Who are you?' to begin."
                )
            return ChatResponse(
                success=True,
                reply=reply,
                intent="repeat",
                confidence=1.0,
                repeatable=False,
                metadata={"provider": "deterministic"},
            )

        # 5. Goodbye
        if (
            re.search(
                r"\b(bye|goodbye|see\s+you|exit|quit|stop\s+talking|namaste\s+alvida)\b",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(r"(अलविदा|बाय|शुभकामनाएं)", trimmed)
        ):
            if is_hindi:
                reply = "अलविदा! आपकी फसल समृद्ध रहे। जब भी बात करनी हो, स्टार्ट लिसनिंग पर क्लिक करें।"
            else:
                reply = "Goodbye! May your harvest be bountiful. Click Start Listening whenever you wish to speak again."
            self._last_responses[session_key] = reply
            return ChatResponse(
                success=True,
                reply=reply,
                intent="goodbye",
                confidence=1.0,
                repeatable=True,
                metadata={"provider": "deterministic", "language": "hi-IN" if is_hindi else "en-US"},
            )

        # 6. Optional Domain Preview (Farm Status)
        if (
            re.search(
                r"\b(farm\s+status|field\s+status|farm\s+overview|farm\s+info|soil\s*(moisture|health)|crop\s+status|temperature|check\s+sensor)\b",
                trimmed,
                re.IGNORECASE,
            )
            or re.search(r"(खेत\s*की\s*(स्थिति|जानकारी|हालत|रिपोर्ट)|खेत\s*का\s*(हाल|हालचाल)|मिट्टी|फसल\s*की\s*स्थिति)", trimmed)
        ):
            if is_hindi:
                reply = (
                    "[डेमो टेलीमेट्री] मिट्टी की नमी: 48.2% (अनुकूल)। मिट्टी का तापमान: 24.5°C। "
                    "पानी का टैंक: 82%। सभी 3 सिमुलेटेड सेंसर ऑनलाइन हैं।"
                )
            else:
                reply = (
                    "[DEMO TELEMETRY] Soil Moisture: 48.2% (Optimal). Soil Temp: 24.5°C. "
                    "Water Tank: 82%. All 3 simulated sensors are online."
                )
            self._last_responses[session_key] = reply
            return ChatResponse(
                success=True,
                reply=reply,
                intent="farm_status",
                confidence=1.0,
                repeatable=True,
                metadata={"provider": "deterministic", "optional_preview": True, "language": "hi-IN" if is_hindi else "en-US"},
            )

        # 7. Unknown Fallback
        if is_hindi:
            fallback = (
                "मुझे इस डेमो में यह समझ नहीं आया। 'नमस्ते', 'आप कौन हैं?', 'खेत की स्थिति', "
                "या 'अलविदा' पूछने का प्रयास करें।"
            )
        else:
            fallback = (
                "I didn't quite catch that in this demo. "
                "Try asking: 'Hello', 'Who are you?', 'What can you do?', or 'Goodbye'."
            )
        self._last_responses[session_key] = fallback
        return ChatResponse(
            success=True,
            reply=fallback,
            intent="unknown",
            confidence=0.2,
            repeatable=True,
            metadata={"provider": "deterministic", "language": "hi-IN" if is_hindi else "en-US"},
        )
