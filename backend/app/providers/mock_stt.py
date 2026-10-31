"""
Mock Speech-to-Text Provider
Offline, deterministic speech transcription fixtures for automated testing and client validation.
"""
from typing import Optional
from app.providers.base import BaseSpeechToTextProvider
from app.models.conversation import STTResponse


class MockSTTProvider(BaseSpeechToTextProvider):
    """
    Offline mock transcription provider.
    """

    def __init__(self, fixed_response: Optional[str] = None):
        self._fixed_response = fixed_response

    @property
    def provider_name(self) -> str:
        return "mock"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "hi-IN",
        audio_format: str = "wav",
    ) -> STTResponse:
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty.")

        if self._fixed_response:
            transcribed_text = self._fixed_response
        elif language.lower().startswith("hi"):
            transcribed_text = "नमस्ते, मेरा खेत कैसा है?"
        else:
            transcribed_text = "Hello, what is the current farm status?"

        return STTResponse(
            success=True,
            text=transcribed_text,
            language=language,
            confidence=0.98,
            provider="mock",
        )
