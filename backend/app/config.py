"""
Environment-based Configuration for FertoBot Voice Agent Backend
"""
import os
from pathlib import Path
from typing import List

# Safely attempt to load .env from backend directory, workspace root, or home directory if present
try:
    from dotenv import load_dotenv
    backend_env = Path(__file__).resolve().parent.parent / ".env"
    workspace_env = Path(__file__).resolve().parent.parent.parent / ".env"
    home_env = Path.home() / ".env"

    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env, override=True)
    elif workspace_env.exists():
        load_dotenv(dotenv_path=workspace_env, override=True)
    elif home_env.exists():
        load_dotenv(dotenv_path=home_env, override=True)
except Exception:
    pass

# Server Network Settings
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))

# Allowed CORS origins for local development and staging preview
CORS_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

# Gnani AI Configuration
GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "").strip()
GNANI_API_BASE_URL: str = os.getenv("GNANI_API_BASE_URL", "https://api.vachana.ai").rstrip("/")
GNANI_STT_WS_URL: str = os.getenv("GNANI_STT_WS_URL", "wss://api.vachana.ai/stt/v3/stream").strip()
GNANI_STT_MODEL: str = os.getenv("GNANI_STT_MODEL", "prisma-v3.0").strip()
GNANI_STT_LANGUAGE_CODE: str = os.getenv("GNANI_STT_LANGUAGE_CODE", "indic-auto").strip()

GNANI_TTS_ENDPOINT: str = os.getenv(
    "GNANI_TTS_ENDPOINT", f"{GNANI_API_BASE_URL}/api/v1/tts/inference"
).strip()
GNANI_STT_ENDPOINT: str = os.getenv(
    "GNANI_STT_ENDPOINT", f"{GNANI_API_BASE_URL}/api/v1/stt/transcribe"
).strip()
GNANI_TTS_MODEL: str = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5").strip()
GNANI_TTS_HINDI_VOICE: str = os.getenv(
    "GNANI_TTS_HINDI_VOICE", os.getenv("GNANI_DEFAULT_HINDI_VOICE", "Nalini")
).strip()
GNANI_TTS_ENGLISH_VOICE: str = os.getenv(
    "GNANI_TTS_ENGLISH_VOICE", os.getenv("GNANI_DEFAULT_ENGLISH_VOICE", "Kaveri")
).strip()
GNANI_TTS_HINGLISH_VOICE: str = os.getenv("GNANI_TTS_HINGLISH_VOICE", "Poorvi").strip()
GNANI_DEFAULT_HINDI_VOICE: str = GNANI_TTS_HINDI_VOICE
GNANI_DEFAULT_ENGLISH_VOICE: str = GNANI_TTS_ENGLISH_VOICE
GNANI_TTS_SPEED: float = float(os.getenv("GNANI_TTS_SPEED", "1.0"))
GNANI_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("GNANI_REQUEST_TIMEOUT_SECONDS", "10.0"))
GNANI_TTS_CONCURRENCY_LIMIT: int = int(os.getenv("GNANI_TTS_CONCURRENCY_LIMIT", "2"))
GNANI_TTS_MAX_RETRIES: int = int(os.getenv("GNANI_TTS_MAX_RETRIES", "3"))

# LLM Brain & Multi-Agent Configuration
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
LLM_PROVIDER: str = os.getenv(
    "LLM_PROVIDER",
    "gemini" if bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 5)
    else ("openai" if bool(OPENAI_API_KEY and len(OPENAI_API_KEY) > 5) else "mock")
).lower()
LLM_MODEL: str = os.getenv(
    "LLM_MODEL",
    "gemini-flash-lite-latest" if (LLM_PROVIDER == "gemini" or bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 5))
    else "gpt-4o-mini"
).strip()
LLM_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "12.0"))

# Hardware & Actuation Safety Settings (Render Free Staging Demo)
SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "true").lower() in ("true", "1", "yes")
ACTUATION_PERMITTED: bool = os.getenv("ACTUATION_PERMITTED", "false").lower() in ("true", "1", "yes")

# Provider Configurations
CONVERSATION_PROVIDER: str = os.getenv("CONVERSATION_PROVIDER", "orchestrator").lower()
# Default to browser native TTS when no Gnani API key is configured, avoiding tone-as-speech confusion
TTS_PROVIDER: str = os.getenv(
    "TTS_PROVIDER", "gnani" if bool(GNANI_API_KEY and len(GNANI_API_KEY) > 5) else "browser"
).lower()
STT_PROVIDER: str = os.getenv("STT_PROVIDER", "browser").lower()


def is_gnani_configured() -> bool:
    """Returns True only if a valid, non-empty Gnani API Key is present."""
    return bool(GNANI_API_KEY and len(GNANI_API_KEY) > 5)


def is_llm_configured() -> bool:
    """Returns True only if a valid LLM API key (Gemini or OpenAI) is present."""
    if LLM_PROVIDER == "gemini":
        return bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 5)
    if LLM_PROVIDER == "openai":
        return bool(OPENAI_API_KEY and len(OPENAI_API_KEY) > 5)
    return bool(
        (GEMINI_API_KEY and len(GEMINI_API_KEY) > 5)
        or (OPENAI_API_KEY and len(OPENAI_API_KEY) > 5)
    )


def redact_sensitive(text: str) -> str:
    """
    Sanitizes log messages, error messages, or exception strings to guarantee
    API keys and secrets are never leaked to logs or API responses.
    """
    if not text:
        return ""
    sanitized = text
    if GNANI_API_KEY and len(GNANI_API_KEY) > 3:
        sanitized = sanitized.replace(GNANI_API_KEY, "[REDACTED_API_KEY]")
    if GEMINI_API_KEY and len(GEMINI_API_KEY) > 3:
        sanitized = sanitized.replace(GEMINI_API_KEY, "[REDACTED_API_KEY]")
    if OPENAI_API_KEY and len(OPENAI_API_KEY) > 3:
        sanitized = sanitized.replace(OPENAI_API_KEY, "[REDACTED_API_KEY]")
    # Redact standard authorization patterns
    import re
    sanitized = re.sub(
        r"(X-API-Key-ID:\s*)([^\s,\'\"]+)",
        r"\1[REDACTED_KEY]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"(x-goog-api-key:\s*)([^\s,\'\"]+)",
        r"\1[REDACTED_KEY]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"(key=)([A-Za-z0-9_\-]{15,})",
        r"\1[REDACTED_KEY]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"(Bearer\s+)([A-Za-z0-9_\-\.]{8,})",
        r"\1[REDACTED_TOKEN]",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized
