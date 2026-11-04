"""
Voice Service
Central coordinator for Text-to-Speech and Speech-to-Text provider instances,
supporting runtime switching, mock fallback, and client configuration reporting.
"""
from typing import Optional, Tuple, Dict, List, Any
import logging
from ai_agronomist import config
from ai_agronomist.providers.base import BaseTextToSpeechProvider, BaseSpeechToTextProvider
from ai_agronomist.providers.mock_tts import MockTTSProvider
from ai_agronomist.providers.gnani_tts import GnaniTTSProvider
from ai_agronomist.providers.mock_stt import MockSTTProvider
from ai_agronomist.providers.gnani_stt import GnaniSTTProvider
from ai_agronomist.models.conversation import ConfigResponse, STTResponse
from ai_agronomist.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self):
        self._tts_providers: Dict[str, BaseTextToSpeechProvider] = {
            "mock": MockTTSProvider(),
            "gnani": GnaniTTSProvider(),
        }
        self._stt_providers: Dict[str, BaseSpeechToTextProvider] = {
            "mock": MockSTTProvider(),
            "gnani": GnaniSTTProvider(),
        }

        # Initialize active providers based on config
        self._active_tts_name = config.TTS_PROVIDER if config.TTS_PROVIDER in self._tts_providers else "gnani"
        self._active_stt_name = config.STT_PROVIDER if (config.STT_PROVIDER in self._stt_providers or config.STT_PROVIDER == "gnani_prisma_v3") else "browser"

    def get_tts_provider(self) -> Optional[BaseTextToSpeechProvider]:
        if self._active_tts_name == "browser":
            return None
        return self._tts_providers.get(self._active_tts_name, self._tts_providers["mock"])

    def set_tts_provider(self, name: str) -> None:
        name_lower = name.lower()
        if name_lower in self._tts_providers or name_lower == "browser":
            self._active_tts_name = name_lower
        else:
            raise ValueError(f"Unknown TTS provider: {name}. Available: mock, gnani, browser")

    def get_stt_provider(self) -> Optional[BaseSpeechToTextProvider]:
        if self._active_stt_name == "browser":
            return None
        if self._active_stt_name in ("gnani", "gnani_prisma_v3"):
            return self._stt_providers["gnani"]
        return self._stt_providers.get(self._active_stt_name, self._stt_providers["mock"])

    def set_stt_provider(self, name: str) -> None:
        name_lower = name.lower()
        if name_lower in ("gnani", "gnani_prisma_v3"):
            self._active_stt_name = name_lower
        elif name_lower in self._stt_providers or name_lower == "browser":
            self._active_stt_name = name_lower
        else:
            raise ValueError(f"Unknown STT provider: {name}. Available: mock, gnani, gnani_prisma_v3, browser")

    async def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        voice_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, str, str]:
        """
        Synthesizes text using active TTS provider.
        Returns (audio_bytes, mime_type, provider_name).
        """
        provider = self.get_tts_provider()
        if not provider:
            raise ValueError("Backend TTS is set to 'browser'. Client Web Speech API should be used.")
        audio_bytes, mime_type = await provider.synthesize(
            text=text,
            language=language,
            voice_id=voice_id,
            speed=speed,
        )
        return audio_bytes, mime_type, provider.provider_name

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi-IN",
        audio_format: str = "wav",
    ) -> STTResponse:
        """
        Transcribes audio using active STT provider.
        """
        provider = self.get_stt_provider()
        if not provider:
            raise ValueError("Backend STT is set to 'browser'. Client Web Speech API should be used.")
        return await provider.transcribe(
            audio_data=audio_data,
            language=language,
            audio_format=audio_format,
        )

    def get_tts_metrics(self) -> Dict[str, Any]:
        """Returns snapshot of active TTS metrics."""
        gnani_prov = self._tts_providers.get("gnani")
        if gnani_prov and hasattr(gnani_prov, "get_metrics"):
            metrics = gnani_prov.get_metrics()
            metrics["active_tts_provider"] = self._active_tts_name
            return metrics
        provider = self.get_tts_provider()
        if hasattr(provider, "get_metrics"):
            return provider.get_metrics()
        return {"provider": self._active_tts_name, "status": "no_metrics"}

    def reset_tts_metrics(self) -> None:
        """Resets TTS metrics counters."""
        provider = self.get_tts_provider()
        if hasattr(provider, "reset_metrics"):
            provider.reset_metrics()

    def get_config(self) -> ConfigResponse:
        """
        Returns active provider configuration for client synchronization.
        """
        available_voices = {
            "hi-IN": ["Nalini", "Deepak", "Shivani"],
            "en-IN": ["Kaveri", "Pranav", "Pratibha"],
            "hi-en": ["Poorvi"],
            "en-US": ["Kaveri", "Pranav"],
        }
        return ConfigResponse(
            tts_provider=self._active_tts_name,
            stt_provider=self._active_stt_name,
            conversation_provider=config.CONVERSATION_PROVIDER,
            gnani_configured=config.is_gnani_configured(),
            available_voices=available_voices,
            supported_languages=["en-US", "en-IN", "hi-IN", "hi-en"],
            llm_provider=orchestrator.llm_provider.provider_name,
            llm_status=orchestrator.llm_provider.provider_status,
            llm_configured=orchestrator.llm_provider.is_live_ready(),
            available_agents=orchestrator.get_available_agents(),
        )


# Global singleton
voice_service = VoiceService()
