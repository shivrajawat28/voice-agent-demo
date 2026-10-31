# FertoBot Voice Agent Demo — Backend Foundation (Phase 6)

Lightweight FastAPI backend with pluggable voice provider architecture (ConversationProvider, SpeechToTextProvider, TextToSpeechProvider), verified Gnani AI (Vachana) adapter, and diagnostic mock test tone provider.

## Architecture

- **Framework**: FastAPI (Python 3.10+)
- **Pluggable Provider Architecture**:
  - `BaseConversationProvider`: `DeterministicProvider` (offline, predictable bilingual responses for English and Hindi)
  - `BaseTextToSpeechProvider`:
    - `GnaniTTSProvider`: Official Gnani Vachana REST API adapter (`POST https://api.vachana.ai/api/v1/tts/inference`) using `timbre-v3.0` (`Shivani` for Hindi). Requires `GNANI_API_KEY` in `backend/.env`. Raises `GnaniAuthenticationError` (HTTP 503) when credentials are not configured.
    - `MockTTSProvider`: In-memory 16-bit PCM WAV sine wave test-tone generator for offline audio pipeline verification.
  - `BaseSpeechToTextProvider`:
    - `GnaniSTTProvider`: Gnani Vachana transcription adapter (`POST https://api.vachana.ai/api/v1/stt/transcribe`). Real-time streaming documented as `wss://api.vachana.ai/stt/v3/stream` (`NOT IMPLEMENTED / BLOCKED pending streaming infrastructure and credentials`).
    - `MockSTTProvider`: Deterministic transcription fixtures for automated verification.
- **Credential Protection**:
  - Environment variables loaded via `backend/.env` (ignored by `.gitignore`).
  - Strict server-side isolation: API keys are never exposed to the client.
  - All logs, exceptions, and API error responses pass through `redact_sensitive()` to scrub secrets.
- **Validation**: Pydantic v2 schemas (`ChatRequest`, `TTSRequest`, `STTRequest`, `ConfigResponse`, `HealthResponse`).
- **CORS**: Configured for local Vite frontend at `http://localhost:5174`.

## API Endpoints

### 1. `GET /health`
Verifies backend service availability.
- **Response**: `{"status": "ok", "service": "fertobot-voice-agent-backend", "version": "0.2.1"}`

### 2. `GET /api/config`
Reports active voice and dialogue providers, Gnani configured status, and supported languages/voices.

### 3. `POST /api/chat`
Processes conversational speech transcript or text input with isolated session tracking.

### 4. `POST /api/tts`
Synthesizes speech audio from text using the active TTS provider.
- When `mock` is active: returns binary audio (`audio/wav`) with `X-Audio-Type: test-tone`.
- When `gnani` is active without credentials: returns HTTP 503 with `X-TTS-Blocked: true`.
- When `gnani` is active with valid credentials: returns binary speech audio from Gnani Vachana API.

### 5. `POST /api/stt`
Transcribes base64-encoded audio to text.

### 6. `POST /api/provider/tts?provider={gnani|mock|browser}`
Dynamically switches the active Text-to-Speech provider.

## Local Development Startup

```bash
cd "/Users/shivrajawat/iCloud Drive (Archive) - 1/Documents/FertoBot-Voice_Agent/voice-agent-demo/backend"
PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Running Automated Tests

```bash
cd "/Users/shivrajawat/iCloud Drive (Archive) - 1/Documents/FertoBot-Voice_Agent/voice-agent-demo/backend"
PYTHONPATH=. pytest -v
```
