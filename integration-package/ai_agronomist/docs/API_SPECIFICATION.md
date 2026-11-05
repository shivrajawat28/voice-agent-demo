# FertoBot AI Agronomist — REST API Specification

This document provides the formal API specification for the FertoBot AI Agronomist module. All endpoints can be mounted directly into an existing FastAPI host application via `ai_agronomist_router`.

## Base Prefix
When mounted with `app.include_router(ai_agronomist_router, prefix="/api")`, all endpoints are accessible under `/api/*`.

---

## Architecture Boundaries: Host Platform vs. AI Agronomist

| Component | Responsibility / Provided By | Notes |
| :--- | :--- | :--- |
| **FastAPI Root Application** | Host Application | The official FertoBot platform instantiates `FastAPI()` and configures server lifecycle. |
| **CORS & Reverse Proxy** | Host Application | Host configures `CORSMiddleware` and reverse proxy headers (Nginx/Render/Cloudflare). |
| **User Authentication / JWT** | Host Application | User identity, farmer account IDs, and tenant isolation are authenticated by the host. |
| **Production Telemetry DB** | Host Application (Optional) | Official PostgreSQL/MongoDB models plugged via `set_global_telemetry_provider()`. |
| **Multi-Agent Orchestration** | **AI Agronomist Module** | Gemini 2.5 Flash Lite brain orchestrating the 4 specialist agronomy agents. |
| **Indic Voice Engine** | **AI Agronomist Module** | GNANI Timbre (Nalini Hindi TTS) + Prisma v3.0 streaming WebSocket STT proxy. |
| **Pump Safety Approval** | **AI Agronomist Module** | Strict advisory-only barrier; generates approval cards with replay protection & 300s expiry. |
| **7-in-1 Soil Intelligence** | **AI Agronomist Module** | Nutrient depletion rates, EC salinity assessment, and sensor quality calibration flags. |

---

## 1. Conversation & Agronomic Reasoning

### `POST /api/chat`
Main conversational and reasoning endpoint. Accepts user text or STT transcript and orchestrates the 4 specialist agents (Crop Symptom, Irrigation Advisory, Weather Context, Device Health) over live farm telemetry.

#### Request Body
```json
{
  "message": "North zone mein nitrogen kitna hai?",
  "language": "hi-IN",
  "session_id": "sess-user-123",
  "zone_id": "DEMO-ZONE-001"
}
```

#### Response Body (Aligned with `ChatResponse` Pydantic Model)
```json
{
  "success": true,
  "reply": "North zone (गेहूं) में नाइट्रोजन 32 मिलीग्राम प्रति किलोग्राम है, जो फसल की इस अवस्था के लिए सामान्य स्तर पर है।",
  "intent": "telemetry_query",
  "confidence": 0.95,
  "repeatable": true,
  "agent_results": [
    {
      "agent_name": "CropSymptomAgent",
      "summary": "Nitrogen level 32 mg/kg is optimal for tillering wheat.",
      "severity": "NORMAL"
    }
  ],
  "execution_trace": [
    {
      "step_id": "step-1a2b3c",
      "agent_id": "fast_path_router",
      "action": "query_zone_telemetry",
      "status": "completed",
      "duration_ms": 1.84
    }
  ],
  "sources": [
    "Simulated 4-Zone Farm Telemetry Overview",
    "FertoBot 7-in-1 Soil Sensor (DEMO-DEVICE-001)"
  ],
  "warnings": null,
  "needs_clarification": false,
  "clarification_prompt": null,
  "sentences": [
    "North zone (गेहूं) में नाइट्रोजन 32 मिलीग्राम प्रति किलोग्राम है, जो फसल की इस अवस्था के लिए सामान्य स्तर पर है।"
  ],
  "provider_status": "gemini",
  "pending_action": null,
  "metadata": {
    "zone_id": "DEMO-ZONE-001",
    "session_id": "sess-user-123",
    "turn_language": "hi-IN",
    "turn_voice": "Nalini"
  }
}
```

### `POST /api/chat/clear`
Clears conversation history, session memory, and turn counter for a specific session.

#### Request Body
```json
{
  "session_id": "sess-user-123"
}
```

#### Response Body
```json
{
  "success": true,
  "session_id": "sess-user-123",
  "message": "Session memory cleared"
}
```

### `GET /api/agents`
Returns active specialist agent metadata and the current LLM provider status.

#### Response Body
```json
{
  "available_agents": [
    {
      "name": "CropSymptomAgent",
      "description": "Diagnoses leaf discoloration, nutrient deficiencies, pest indicators, and crop health."
    },
    {
      "name": "IrrigationAdvisoryAgent",
      "description": "Computes soil moisture depletion, evapotranspiration, and safe irrigation recommendations."
    },
    {
      "name": "WeatherContextAgent",
      "description": "Evaluates rainfall forecasts, temperature ranges, and humidity to contextualize field actions."
    },
    {
      "name": "DeviceHealthAgent",
      "description": "Audits 7-in-1 sensor probe telemetry, battery levels, LoRaWAN signal, and calibration states."
    }
  ],
  "llm_provider": "gemini",
  "llm_status": "active"
}
```

---

## 2. Indic Voice Services (GNANI Timbre & Prisma)

### `POST /api/tts`
Synthesizes speech using the GNANI Timbre Indic voice engine (defaulting to Nalini for Hindi).

#### Query Parameters
- `as_json` (boolean, optional, default: `false`): If `true`, returns a base64-encoded JSON response (`TTSResponse`). If `false`, streams binary audio directly (`audio/wav`).

#### Request Body
```json
{
  "text": "नमस्ते, मैं फेर्टोबोट एआई कृषि विशेषज्ञ हूँ।",
  "language": "hi-IN",
  "voice_id": "Nalini",
  "speed": 1.0
}
```

#### Response Headers (Binary Stream Mode)
- `Content-Type: audio/wav`
- `X-TTS-Provider: gnani`
- `X-Audio-Type: speech`

#### Status Codes
- `200 OK`: Successful synthesis.
- `429 Too Many Requests`: GNANI rate limit encountered; includes `Retry-After: 2`.
- `502 Bad Gateway`: GNANI upstream service unreachable.
- `503 Service Unavailable`: Missing or invalid GNANI credentials (`X-TTS-Blocked: true`).

### `POST /api/stt`
Performs batch Speech-to-Text transcription of an audio payload.

#### Request Body
```json
{
  "audio_base64": "<base64_encoded_pcm_audio>",
  "language": "hi-IN",
  "audio_format": "wav"
}
```

#### Response Body
```json
{
  "text": "खेत में नमी कितनी है",
  "confidence": 0.94,
  "language": "hi-IN",
  "provider": "gnani"
}
```

### `GET /api/tts/metrics`
Returns real-time concurrency metrics, active queue depth, and retry performance.

---

## 3. Safe Pump Control Approval Workflow

The FertoBot AI Agronomist strictly enforces an **autonomous safety barrier**: the agent cannot directly activate water pumps or physical valves. When irrigation is indicated, it generates an approval card requiring explicit human confirmation.

### `POST /api/pump/action`
Initiates a proposed pump action in `AWAITING_USER_APPROVAL` status.

#### Request Body
```json
{
  "zone_id": "DEMO-ZONE-001",
  "action_type": "PUMP_ON",
  "session_id": "sess-user-123",
  "language": "hi-IN"
}
```

#### Response Body
```json
{
  "success": true,
  "action_id": "act-7f89b",
  "state": "AWAITING_USER_APPROVAL",
  "reply": "क्या आप DEMO-ZONE-001 (गेहूं) के लिए पानी का पंप चालू करना चाहते हैं? कृपया नीचे दिए गए बटन से पुष्टि करें।",
  "simulated_pump_running": false,
  "zone_id": "DEMO-ZONE-001",
  "sentences": [
    "क्या आप DEMO-ZONE-001 (गेहूं) के लिए पानी का पंप चालू करना चाहते हैं? कृपया नीचे दिए गए बटन से पुष्टि करें।"
  ]
}
```

### `POST /api/pump/approve`
Farmer explicit approval button click (`हाँ, चालू करें`). Transitions state to `COMPLETED`.

#### Request Body
```json
{
  "action_id": "act-7f89b",
  "session_id": "sess-user-123",
  "language": "hi-IN"
}
```

### `POST /api/pump/reject`
Farmer explicit rejection button click (`नहीं, रद्द करें`). Transitions state to `REJECTED`.

### `POST /api/pump/emergency-stop`
Immediate emergency pump shutdown without requiring secondary confirmation.

### `GET /api/pump/status`
Returns current pump state (`running: true/false`), active approval tickets, and safety lockout status.

---

## 4. Farm Telemetry Endpoints

All telemetry endpoints dynamically query the active `BaseTelemetryProvider` implementation.

- `GET /api/farm/overview`: Overview of all farm zones, summary metrics, and active alerts.
- `GET /api/farm/zones`: List of zones and current active zone ID.
- `GET /api/farm/telemetry/latest?zone_id=DEMO-ZONE-001`: Latest sensor readings for the zone. Returns 404 if zone is unknown.
- `GET /api/farm/telemetry/history?zone_id=DEMO-ZONE-001&parameter=soil_moisture_pct&time_range=7d`: Historical time-series data.
- `GET /api/farm/telemetry/profile?zone_id=DEMO-ZONE-001`: Canonical 7-in-1 sensor profile including quality flags and health score. Returns 404 if zone is unknown.
- `GET /api/farm/telemetry/sodium`: Boundary clarification endpoint confirming FertoBot 7-in-1 probes do not measure sodium.
- `POST /api/farm/active-zone`: Sets the active target zone (supports optional `session_id` for per-user isolation).
