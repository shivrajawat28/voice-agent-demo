"""
Gnani AI (Vachana) Speech-to-Text Provider Adapter
Interacts with Gnani Vachana STT REST / Batch API:
- Endpoint: POST https://api.vachana.ai/api/v1/stt/transcribe
- Auth Header: X-API-Key-ID: <GNANI_API_KEY>
- Supported Models: prisma-v2.5
- Supported Languages: hi-IN, en-IN, etc.

Note on Real-time STT:
Production real-time conversational voice agents utilize Gnani's WebSocket
streaming protocol (wss://api.vachana.ai/stt/v3/stream) with continuous raw PCM
audio frames and server-side VAD. For REST batch mode, audio clips are uploaded
as multipart/form-data or JSON base64.
"""
import logging
from typing import Optional
import httpx
from ai_agronomist.providers.base import BaseSpeechToTextProvider
from ai_agronomist.providers.mock_stt import MockSTTProvider
from ai_agronomist.models.conversation import STTResponse
from ai_agronomist import config

logger = logging.getLogger(__name__)


class GnaniSTTException(Exception):
    """Base exception for Gnani STT provider."""
    pass


class GnaniSTTProvider(BaseSpeechToTextProvider):
    """
    Adapter for Gnani Vachana Speech-to-Text API.
    Supports both batch REST transcription and integrates with Prisma v3.0 streaming.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        allow_mock_fallback: bool = True,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key if api_key is not None else config.GNANI_API_KEY
        self.endpoint = endpoint or config.GNANI_STT_ENDPOINT
        self.model = model or config.GNANI_STT_MODEL
        self.timeout_seconds = timeout_seconds or config.GNANI_REQUEST_TIMEOUT_SECONDS
        self.allow_mock_fallback = allow_mock_fallback
        self._mock_provider = MockSTTProvider() if allow_mock_fallback else None
        self._http_client = http_client

    @property
    def provider_name(self) -> str:
        return "gnani"

    def is_live_ready(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi-IN",
        audio_format: str = "wav",
    ) -> STTResponse:
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty.")

        if not self.is_live_ready():
            if self.allow_mock_fallback and self._mock_provider:
                logger.info("Gnani API key not configured; serving mock STT transcription.")
                return await self._mock_provider.transcribe(
                    audio_data, language=language, audio_format=audio_format
                )
            raise GnaniSTTException(
                "Gnani API key (GNANI_API_KEY) is not configured in backend/.env. "
                "Live STT is BLOCKED pending user-supplied credentials."
            )

        headers = {
            "X-API-Key-ID": self.api_key or "",
            "Accept": "application/json",
        }
        files = {
            "audio": (f"audio.{audio_format}", audio_data, f"audio/{audio_format}"),
        }
        data = {
            "language": language,
            "model": self.model,
        }

        try:
            client = self._http_client or httpx.AsyncClient(timeout=self.timeout_seconds)
            try:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    files=files,
                    data=data,
                )
            finally:
                if not self._http_client:
                    await client.aclose()

            if response.status_code == 200:
                result = response.json()
                text = result.get("transcript") or result.get("text") or ""
                confidence = float(result.get("confidence", 0.95))
                return STTResponse(
                    success=True,
                    text=text,
                    language=language,
                    confidence=confidence,
                    provider="gnani",
                )

            if response.status_code in (401, 403):
                raise GnaniSTTException(
                    f"Gnani STT authentication failed (HTTP {response.status_code}). Check GNANI_API_KEY."
                )
            elif response.status_code == 429:
                raise GnaniSTTException("Gnani STT rate limit exceeded (HTTP 429).")
            elif response.status_code == 504:
                raise GnaniSTTException("Gnani STT upstream gateway timeout (HTTP 504).")

            sanitized_detail = config.redact_sensitive(response.text[:200])
            raise GnaniSTTException(
                f"Gnani STT failed with HTTP {response.status_code}: {sanitized_detail}"
            )
        except GnaniSTTException:
            raise
        except Exception as exc:
            sanitized_msg = config.redact_sensitive(str(exc))
            logger.error(f"Gnani STT connection error: {sanitized_msg}")
            raise GnaniSTTException(f"Network error connecting to Gnani STT: {sanitized_msg}") from exc
