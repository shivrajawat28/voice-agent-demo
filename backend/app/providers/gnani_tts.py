"""
Gnani AI (Vachana) Text-to-Speech Provider Adapter
Interacts with the official Gnani Vachana TTS REST API:
- Endpoint: POST https://api.vachana.ai/api/v1/tts/inference
- Auth Header: X-API-Key-ID: <GNANI_API_KEY>
- Supported Models: timbre-v2.5, timbre-v3.0
- Supported Languages: hi-IN (Hindi), en-IN (Indian English), hi-en (Hinglish), etc.
- Default Voices: Nalini (Hindi), Kaveri (English), Poorvi (Hinglish)
"""
import asyncio
import logging
import re
from typing import Optional, Tuple, Dict, Any
import httpx
from app.providers.base import BaseTextToSpeechProvider
from app import config

logger = logging.getLogger(__name__)


class GnaniTTSException(Exception):
    """Base exception for Gnani TTS provider."""
    pass


class GnaniAuthenticationError(GnaniTTSException):
    """Raised when API key is missing or rejected."""
    pass


class GnaniAPIError(GnaniTTSException):
    """Raised when Gnani API returns an error status code or malformed response."""
    pass


HINDI_NUMBER_WORDS = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच", 6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस", 26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकत्तीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस", 36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चवालीस", 45: "पैंतालीस", 46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन", 56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ", 66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर", 76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्यासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी", 86: "छियासी", 87: "सत्तासी", 88: "अठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पचानवे", 96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे", 100: "सौ"
}

def number_to_hindi_words(num_str: str) -> str:
    """Converts numeric string to natural spoken Devanagari Hindi words."""
    if "." in num_str:
        parts = num_str.split(".", 1)
        try:
            int_val = int(parts[0])
            int_w = HINDI_NUMBER_WORDS.get(int_val, str(int_val))
        except ValueError:
            int_w = parts[0]
        dec_w = " ".join(HINDI_NUMBER_WORDS.get(int(d), d) for d in parts[1] if d.isdigit())
        return f"{int_w} दशमलव {dec_w}" if dec_w else int_w
    else:
        try:
            int_val = int(num_str)
            if int_val in HINDI_NUMBER_WORDS:
                return HINDI_NUMBER_WORDS[int_val]
            if int_val < 1000:
                h = int_val // 100
                r = int_val % 100
                h_name = f"{HINDI_NUMBER_WORDS.get(h, str(h))} सौ"
                return f"{h_name} {HINDI_NUMBER_WORDS.get(r, str(r))}" if r > 0 else h_name
            return num_str
        except ValueError:
            return num_str


class GnaniTTSProvider(BaseTextToSpeechProvider):
    """
    Adapter for Gnani Vachana Text-to-Speech REST API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        default_hindi_voice: Optional[str] = None,
        default_english_voice: Optional[str] = None,
        default_hinglish_voice: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key if api_key is not None else config.GNANI_API_KEY
        self.endpoint = endpoint or config.GNANI_TTS_ENDPOINT
        self.model = model or config.GNANI_TTS_MODEL
        self.default_hindi_voice = default_hindi_voice or config.GNANI_TTS_HINDI_VOICE
        self.default_english_voice = default_english_voice or config.GNANI_TTS_ENGLISH_VOICE
        self.default_hinglish_voice = default_hinglish_voice or config.GNANI_TTS_HINGLISH_VOICE
        self.timeout_seconds = timeout_seconds or config.GNANI_REQUEST_TIMEOUT_SECONDS
        self._http_client = http_client
        self._request_lock = asyncio.Lock()
        self._cache: Dict[str, Tuple[float, bytes, str]] = {}

    @property
    def provider_name(self) -> str:
        return "gnani"

    def is_live_ready(self) -> bool:
        """Returns True only if an API key is present."""
        return bool(self.api_key and len(self.api_key) > 5)

    def select_voice(self, language: str, requested_voice: Optional[str] = None) -> str:
        """Determines best voice for target language."""
        if requested_voice:
            return requested_voice
        lang_lower = language.lower()
        if lang_lower in ("hi-en", "hinglish", "hi_en", "code-mix", "codemix"):
            return self.default_hinglish_voice
        if lang_lower.startswith("hi"):
            return self.default_hindi_voice
        if lang_lower.startswith("en"):
            return self.default_english_voice
        return self.default_hindi_voice

    def format_spoken_text(self, text: str, language: str = "hi-IN", spell_numbers: bool = False) -> str:
        """
        Cleans and optimizes agricultural assistant text for spoken synthesis:
        - Removes markdown formatting (asterisks, headers, bullets, backticks).
        - Removes internal tags (e.g. [REDACTED], (सिमुलेटेड टेलीमेट्री डेटा), (सिमुलेटेड डेटा)).
        - Replaces technical abbreviations with naturally spoken words.
        - Expands units (% -> प्रतिशत / percent, mg/kg -> मिलीग्राम प्रति किलोग्राम / milligrams per kilogram).
        - When spell_numbers is True and language is Hindi, spells out digits in Devanagari words for natural Indian pronunciation.
        """
        if not text:
            return ""

        clean = text
        # Remove bracketed/parenthetical provenance/simulation markers
        clean = re.sub(r"\((सिमुलेटेड[^)]*|simulated[^)]*)\)", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\[(सिमुलेटेड[^\]]*|simulated[^\]]*)\]", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\[REDACTED[^\]]*\]", "", clean, flags=re.IGNORECASE)

        # Strip markdown bold, italics, backticks, bullet dashes, hashes
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
        clean = re.sub(r"\*([^*]+)\*", r"\1", clean)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        clean = re.sub(r"^[ \t]*[#\-\*]+[ \t]*", "", clean, flags=re.MULTILINE)

        lang_lower = language.lower()
        is_indic = lang_lower.startswith("hi") or "hinglish" in lang_lower or "hi-en" in lang_lower

        # Expand technical units
        if is_indic:
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*mg/kg\b", r"\1 मिलीग्राम प्रति किलोग्राम", clean, flags=re.IGNORECASE)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*ppm\b", r"\1 पीपीएम", clean, flags=re.IGNORECASE)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 प्रतिशत", clean)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*°C\b", r"\1 डिग्री सेल्सियस", clean)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*dS/m\b", r"\1 डेसीसाइमेंस प्रति मीटर", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bNPK\b", "एन.पी.के", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bEC\b", "ई.सी", clean)
            clean = clean.replace("DEMO-ZONE-001", "ज़ोन 1")
            clean = clean.replace("DEMO-ZONE-002", "ज़ोन 2")
            clean = clean.replace("DEMO-ZONE-003", "ज़ोन 3")
            clean = clean.replace("DEMO-DEVICE-001", "डिवाइस 1")
            clean = clean.replace("DEMO-DEVICE-002", "डिवाइस 2")
            clean = clean.replace("DEMO-DEVICE-003", "डिवाइस 3")

            if spell_numbers:
                clean = re.sub(r"(\d+(?:\.\d+)?)\s*प्रतिशत", lambda m: f"{number_to_hindi_words(m.group(1))} प्रतिशत", clean)
                clean = re.sub(r"(\d+(?:\.\d+)?)\s*डिग्री\s*सेल्सियस", lambda m: f"{number_to_hindi_words(m.group(1))} डिग्री सेल्सियस", clean)
                clean = re.sub(r"(\d+(?:\.\d+)?)\s*मिलीग्राम", lambda m: f"{number_to_hindi_words(m.group(1))} मिलीग्राम", clean)
                clean = re.sub(r"(\d+(?:\.\d+)?)\s*पीपीएम", lambda m: f"{number_to_hindi_words(m.group(1))} पीपीएम", clean)
                clean = re.sub(r"pH\s*(\d+(?:\.\d+)?)", lambda m: f"पीएच {number_to_hindi_words(m.group(1))}", clean, flags=re.IGNORECASE)
                clean = re.sub(r"पी\.?एच\s*(\d+(?:\.\d+)?)", lambda m: f"पीएच {number_to_hindi_words(m.group(1))}", clean, flags=re.IGNORECASE)
        else:
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*mg/kg\b", r"\1 milligrams per kilogram", clean, flags=re.IGNORECASE)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", clean)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*°C\b", r"\1 degrees Celsius", clean)
            clean = re.sub(r"(\d+(?:\.\d+)?)\s*dS/m\b", r"\1 deciSiemens per meter", clean, flags=re.IGNORECASE)
            clean = clean.replace("DEMO-ZONE-001", "Zone 1")
            clean = clean.replace("DEMO-ZONE-002", "Zone 2")
            clean = clean.replace("DEMO-ZONE-003", "Zone 3")
            clean = clean.replace("DEMO-DEVICE-001", "Device 1")
            clean = clean.replace("DEMO-DEVICE-002", "Device 2")
            clean = clean.replace("DEMO-DEVICE-003", "Device 3")

        # Condense multiple whitespaces/newlines
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean if clean else text.strip()

    def build_payload(
        self,
        text: str,
        language: str = "hi-IN",
        voice_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Constructs the JSON request payload conforming to Gnani Vachana TTS specs."""
        spell_num = language.lower().startswith("hi") and "en" not in language.lower()
        spoken_text = self.format_spoken_text(text, language, spell_numbers=spell_num)
        return {
            "text": spoken_text,
            "model": self.model,
            "language": language,
            "voice": self.select_voice(language, voice_id),
            "speed": max(0.5, min(2.0, float(speed))),
            "audio_config": {
                "sample_rate": 48000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

    def build_headers(self) -> Dict[str, str]:
        """Constructs headers per Gnani documentation."""
        return {
            "X-API-Key-ID": self.api_key or "",
            "Content-Type": "application/json",
            "Accept": "audio/wav, audio/mpeg, application/json, */*",
        }

    async def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        voice_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, str]:
        trimmed_text = text.strip()
        if not trimmed_text:
            raise ValueError("Text to synthesize cannot be empty.")

        # Check if live API key is available
        if not self.is_live_ready():
            raise GnaniAuthenticationError(
                "Gnani API key (GNANI_API_KEY) is not configured in backend/.env. "
                "Live integration is BLOCKED pending user-supplied credentials."
            )

        payload = self.build_payload(trimmed_text, language, voice_id, speed)
        headers = self.build_headers()

        async with self._request_lock:
            # Check in-memory cache for duplicate requests
            cache_key = f"{trimmed_text}::{language}::{voice_id}::{speed}"
            loop = asyncio.get_running_loop()
            now = loop.time()
            if cache_key in self._cache:
                cached_time, cached_bytes, cached_mime = self._cache[cache_key]
                if now - cached_time < 300.0:  # 5 min cache
                    return cached_bytes, cached_mime

            try:
                client = self._http_client or httpx.AsyncClient(timeout=self.timeout_seconds)
                try:
                    response = await client.post(self.endpoint, json=payload, headers=headers)
                    # Handle 429 rate limit with bounded backoff
                    if response.status_code == 429:
                        logger.warning("Gnani TTS rate limit 429 received, backing off 0.5s before bounded retry...")
                        await asyncio.sleep(0.5)
                        response = await client.post(self.endpoint, json=payload, headers=headers)
                finally:
                    if not self._http_client:
                        await client.aclose()

                if response.status_code == 200:
                    raw_content_type = response.headers.get("content-type", "")
                    mime_type = raw_content_type.split(";")[0].strip().lower()

                    # Guard against JSON error wrapped in a 200 OK
                    if "application/json" in mime_type:
                        try:
                            err_json = response.json()
                            err_msg = err_json.get("message") or err_json.get("detail") or "Unknown API error"
                            raise GnaniAPIError(f"Gnani TTS returned JSON error: {config.redact_sensitive(str(err_msg))}")
                        except ValueError:
                            raise GnaniAPIError("Gnani TTS returned unparseable JSON instead of audio.")

                    # Validate payload contains audio bytes
                    if len(response.content) < 44:
                        raise GnaniAPIError("Gnani TTS returned empty or truncated audio payload.")

                    if not mime_type or not mime_type.startswith("audio/"):
                        mime_type = "audio/wav"

                    audio_content = response.content
                    # Normalize unknown length markers (0xffffffff) so browsers can compute duration accurately
                    if len(audio_content) >= 44 and audio_content[:4] == b"RIFF" and audio_content[8:12] == b"WAVE":
                        import struct
                        actual_data_size = len(audio_content) - 44
                        actual_riff_size = len(audio_content) - 8
                        audio_content = (
                            audio_content[:4]
                            + struct.pack("<I", actual_riff_size)
                            + audio_content[8:40]
                            + struct.pack("<I", actual_data_size)
                            + audio_content[44:]
                        )

                    self._cache[cache_key] = (now, audio_content, mime_type)
                    return audio_content, mime_type

                # Error handling with credential protection
                if response.status_code in (401, 403):
                    raise GnaniAuthenticationError(
                        f"Gnani API authentication failed (HTTP {response.status_code}). "
                        "Check GNANI_API_KEY in backend/.env."
                    )
                elif response.status_code == 429:
                    raise GnaniAPIError("Gnani API rate limit exceeded (HTTP 429).")
                else:
                    sanitized_error = config.redact_sensitive(response.text[:200])
                    raise GnaniAPIError(
                        f"Gnani TTS request failed with HTTP {response.status_code}: {sanitized_error}"
                    )

            except (GnaniTTSException, ValueError):
                raise
            except Exception as exc:
                sanitized_msg = config.redact_sensitive(str(exc))
                logger.error(f"Gnani TTS connection error: {sanitized_msg}")
                raise GnaniAPIError(f"Network error connecting to Gnani TTS: {sanitized_msg}") from exc
