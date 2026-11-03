"""
Mock Text-to-Speech Provider
Generates predictable, valid single-channel 16-bit PCM WAV test tones (sine wave)
specifically for offline testing, CI pipeline verification, and audio element checks.

NOTE: This provider deliberately generates an audio test tone / sine wave, NOT
synthetic human speech. It is used to verify that the browser audio stack,
object URLs, and state transitions work without requiring external networks.
"""
import io
import wave
import math
import struct
from typing import Optional, Tuple
from app.providers.base import BaseTextToSpeechProvider


def generate_synthetic_wav(duration_seconds: float = 1.0, frequency_hz: float = 440.0) -> bytes:
    """
    Generates a valid, playable single-channel 16-bit PCM WAV audio tone in memory.
    Useful for unit tests and local audio player verification.
    """
    sample_rate = 16000
    total_samples = int(sample_rate * duration_seconds)
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Generate a soft sine tone
        frames = bytearray()
        amplitude = 32767.0 * 0.08  # Soft volume
        for i in range(total_samples):
            # Soft attack and decay envelope to prevent audio click
            envelope = min(1.0, i / 800.0) * min(1.0, (total_samples - i) / 800.0)
            sample_val = int(amplitude * envelope * math.sin(2.0 * math.pi * frequency_hz * i / sample_rate))
            frames.extend(struct.pack("<h", sample_val))

        wav_file.writeframes(frames)

    return buf.getvalue()


class MockTTSProvider(BaseTextToSpeechProvider):
    """
    Predictable offline test tone provider. Returns valid synthetic WAV test tone.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    async def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        voice_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, str]:
        # Duration scales slightly with text length (bounded between 0.5s and 2.5s)
        duration = max(0.5, min(2.5, len(text.split()) * 0.25))
        # Use 360Hz for Hindi and 440Hz for English to verify mock differentiation
        freq = 360.0 if language.lower().startswith("hi") else 440.0
        audio_bytes = generate_synthetic_wav(duration_seconds=duration, frequency_hz=freq)
        return audio_bytes, "audio/wav"

    def get_metrics(self) -> dict:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "rate_limit_429_count": 0,
            "server_error_5xx_count": 0,
            "retry_count": 0,
            "exhausted_retries_count": 0,
            "active_concurrency": 0,
            "peak_concurrency": 0,
            "total_queue_wait_ms": 0.0,
            "total_provider_duration_ms": 0.0,
            "cancelled_requests": 0,
            "concurrency_limit": 2,
            "max_retries": 3,
            "provider": "mock",
        }

    def reset_metrics(self) -> None:
        pass
