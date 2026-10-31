# FertoBot AI Agronomist & Voice Agent

> **Production-Style Staging Release**: Phase 22  
> **Speech AI**: GNANI AI Cloud (Prisma v3.0 Realtime STT WebSocket + Timbre v2.5 Neural TTS)  
> **LLM Orchestration**: Google Gemini Flash Lite Multi-Agent Architecture  
> **Hardware Spec**: 7-in-1 Modbus RS485 Soil Sensor Grounding (Simulated Read-Only Boundary)  
> **Repository Boundary**: Completely independent repository. The official `fertobot` repository is strictly isolated.

---

## 1. Overview

**FertoBot AI Agronomist & Voice Agent** is a full-stack agricultural assistant designed for Indian farmers. It enables real-time spoken Hindi and English conversations, grounded in 7-parameter soil sensor telemetry, crop phenology, meteorological forecasts, and device health monitoring.

### Key Capabilities
- **Natural Voice Interaction**: Real-time Hindi and English speech recognition via GNANI AI Prisma v3.0 and expressive Indian neural voice output via GNANI AI Timbre v2.5 (`Nalini` Hindi voice).
- **Sentence-Level Streaming**: Progressive, synchronized text reveals and audio playback queues.
- **7-in-1 Soil Telemetry Intelligence**: Grounded in physical Modbus RS485 registers (Nitrogen, Phosphorus, Potassium, Moisture, Temperature, pH, and Electrical Conductivity). Rejects unsupported parameters (e.g. Sodium) with explicit agronomic rationale.
- **Multi-Agent Orchestration**: Dynamic query planning routing to 4 specialized agents:
  1. *Crop Symptom & Agronomy Specialist*
  2. *Irrigation Advisory Specialist*
  3. *Weather Context Specialist*
  4. *Device Health Specialist*
- **Safe Pump Control Approval Workflow**: Strict farmer-authorized state machine (`AWAITING_USER_APPROVAL` -> `APPROVED` -> `COMPLETED`) with 5-minute token expiration, single-use replay protection, cross-session isolation, and immediate emergency shutdown.
- **Strict Hardware Safety**: Operates in simulated mode (`simulation_mode = true`, `actuation_permitted = false`). No physical relays, GPIO pins, or Modbus coil commands are actuated.

---

## 2. Architecture & File Structure

```text
voice-agent-demo/
├── Dockerfile                         # Unified multi-stage container (Vite build + FastAPI ASGI)
├── render.yaml                        # Render Blueprint web service configuration
├── vercel.json                        # Vercel deployment configuration
├── .env.example                       # Root template for staging environment variables
├── package.json                       # React/Vite dependencies & test scripts
├── src/                               # Frontend React 18 + TypeScript + Tailwind CSS
│   ├── components/                    # Agronomist dashboard, Voice evaluation, Telemetry UI
│   ├── hooks/                         # useVoiceAgent (speech orchestration, pump approval)
│   ├── services/                      # VoiceController, AudioStreamer, AudioRecorder
│   └── tests/                         # Vitest component & state machine tests (45 tests)
└── backend/
    ├── Dockerfile                     # Standalone backend container
    ├── requirements.txt               # Python dependencies (FastAPI, Uvicorn, WebSockets, httpx)
    ├── .env.example                   # Backend environment template
    ├── app/
    │   ├── main.py                    # ASGI endpoints, WebSocket STT proxy, static serving
    │   ├── config.py                  # Environment parsing & credential redaction
    │   ├── agents/                    # 4 Specialist Agents (Crop, Irrigation, Weather, Device)
    │   ├── models/                    # Pydantic schemas (Conversation, Telemetry, Pump actions)
    │   ├── providers/                 # LLM (Gemini) and Voice (Gnani) integrations
    │   ├── services/                  # Orchestrator, TelemetryService, PumpControlService
    │   └── tools/                     # Read-only agricultural telemetry tools
    └── tests/                         # Pytest test suite (115 tests)
```

---

## 3. Quick Start (Local Development)

### Prerequisites
- Node.js v18+
- Python 3.10+
- Chrome or Chromium-based browser (recommended for microphone input)

### Running Locally

#### 1. Backend (FastAPI + Uvicorn)
```bash
cd backend
cp .env.example .env
# Add your GEMINI_API_KEY and GNANI_API_KEY to .env
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Health Check: `http://127.0.0.1:8000/health`
- Swagger Docs: `http://127.0.0.1:8000/docs`

#### 2. Frontend (React + Vite)
```bash
npm install
npm run dev
```
- Open `http://localhost:5174/`
- Vite automatically proxies `/api` and `/health` requests to `http://127.0.0.1:8000`.

---

## 4. Running Automated Tests

```bash
# 1. Run all Backend tests (115 Pytest tests)
cd backend && pytest -q

# 2. Run all Frontend tests (45 Vitest tests)
npm test -- --run

# 3. TypeScript Compilation & Production Build
npm run build
```

---

## 5. Docker Deployment

Build and run the unified single-port container locally:
```bash
docker build -t fertobot-voice-agent:latest .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key" \
  -e GNANI_API_KEY="your_gnani_api_key" \
  fertobot-voice-agent:latest
```
Visit `http://localhost:8000/` to access the unified frontend and backend.

---

## 6. Security & Safety

- **No Secrets in Bundles**: All API credentials reside exclusively on the backend. No keys are bundled into frontend assets.
- **Credential Redaction**: `redact_sensitive()` strips API keys from logs and error messages.
- **Diagnostic Endpoint Protection**: Simulation endpoints are gated with `TEAM_REVIEW_PASSKEY` via `X-Team-Review-Key`.
- **Hardware Isolation**: Relays are disabled (`actuation_permitted: false`) for demonstration safety.
