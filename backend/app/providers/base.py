"""
Base Provider Interfaces
Defines strict, typed abstractions for:
1. ConversationProvider (NLU / Dialogue Reasoning)
2. SpeechToTextProvider (Audio -> Text)
3. TextToSpeechProvider (Text -> Audio)

Allows pluggable providers (Deterministic, Gnani AI, BrowserNative, Mock)
without coupling API, business logic, or frontend layers.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.models.conversation import ChatResponse, TTSResponse, STTResponse


class BaseConversationProvider(ABC):
    """
    Abstract interface for conversation and NLU providers.
    """

    @abstractmethod
    async def process_message(
        self,
        message: str,
        language: str = "en-US",
        session_id: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Processes a user message and returns a structured ChatResponse.
        """
        pass


class BaseTextToSpeechProvider(ABC):
    """
    Abstract interface for Text-to-Speech synthesis providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of this TTS provider (e.g. 'gnani', 'mock', 'browser')."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        voice_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, str]:
        """
        Synthesizes text into audio data.
        Returns a tuple of (audio_bytes, mime_type), e.g. (b"...", "audio/wav").
        Raises an exception if synthesis fails.
        """
        pass


class BaseSpeechToTextProvider(ABC):
    """
    Abstract interface for Speech-to-Text transcription providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of this STT provider (e.g. 'gnani', 'mock', 'browser')."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi-IN",
        audio_format: str = "wav",
    ) -> STTResponse:
        """
        Transcribes audio data into text.
        Returns a structured STTResponse.
        Raises an exception if transcription fails.
        """
        pass
