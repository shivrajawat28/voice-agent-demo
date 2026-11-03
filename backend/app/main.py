"""
FastAPI Main Application Entry Point
Exposes:
- GET  /health           : Health check endpoint
- GET  /api/config       : System provider configuration and capabilities
- POST /api/chat         : Dialogue reasoning endpoint
- POST /api/tts          : Text-to-Speech audio synthesis endpoint (returns audio/wav or audio/mpeg)
- POST /api/stt          : Speech-to-Text audio transcription endpoint
- POST /api/provider/tts : Dynamic TTS provider switcher (gnani, mock, browser)
- POST /api/provider/stt : Dynamic STT provider switcher (browser, gnani, mock)
"""
import base64
import os
from pathlib import Path
from typing import Optional
from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Response,
    Query,
    Header,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS, redact_sensitive
from app.models.conversation import (
    HealthResponse,
    ChatRequest,
    ChatResponse,
    ClearSessionRequest,
    TTSRequest,
    TTSResponse,
    STTRequest,
    STTResponse,
    ConfigResponse,
    PumpActionPayload,
    PumpApprovalRequest,
    PumpRejectionRequest,
    PumpActionRequest,
    PumpEmergencyStopRequest,
    PumpActionResponse,
    SimulateSensorConditionRequest,
)
from app.services.conversation_service import conversation_service
from app.services.voice_service import voice_service
from app.services.orchestrator import orchestrator, split_into_sentences
from app.services.gnani_stt_stream import gnani_stt_stream_handler
from app.services.pump_control_service import pump_control_service
from app.providers.llm_factory import get_llm_provider
from app.providers.gnani_tts import GnaniAuthenticationError, GnaniAPIError

app = FastAPI(
    title="FertoBot Voice Agent Backend",
    description="Backend API and Voice Provider Foundation for FertoBot Voice Agent Demo",
    version="0.2.1",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend availability and exact deployed commit SHA."""
    commit_sha = os.getenv("RENDER_GIT_COMMIT", os.getenv("GIT_COMMIT", None))
    if not commit_sha:
        v_file = os.path.join(os.path.dirname(__file__), "version.json")
        if os.path.exists(v_file):
            try:
                with open(v_file, "r") as f:
                    v_data = json.load(f)
                    commit_sha = v_data.get("commit")
            except Exception:
                pass
    return HealthResponse(
        commit=commit_sha,
        environment=os.getenv("ENVIRONMENT", "production"),
    )


@app.get("/api/config", response_model=ConfigResponse, tags=["Configuration"])
async def get_configuration():
    """Returns the active provider configuration and supported languages/voices."""
    return voice_service.get_config()


@app.post("/api/chat", response_model=ChatResponse, tags=["Conversation"])
async def chat_endpoint(request: ChatRequest):
    """
    Structured conversation endpoint.
    Accepts user transcript or text message and returns structured NLU response.
    """
    try:
        response = await conversation_service.handle_message(
            message=request.message,
            language=request.language or "en-US",
            session_id=request.session_id,
            zone_id=request.zone_id,
        )
        return response
    except Exception as exc:
        sanitized = redact_sensitive(str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversation processing error: {sanitized}",
        )


@app.post("/api/chat/clear", tags=["Conversation"])
async def clear_chat_endpoint(request: ClearSessionRequest):
    """
    Clears session memory, greeting state, and turn counters for a conversational session.
    """
    sid = request.session_id or "default"
    conversation_service.clear_session(sid)
    return {"success": True, "session_id": sid, "message": "Session memory cleared"}


@app.post("/api/tts", tags=["Voice"])
async def text_to_speech_endpoint(
    request: TTSRequest,
    as_json: bool = Query(default=False, description="Return base64 JSON payload instead of binary audio stream"),
):
    """
    Synthesizes speech from text using the active backend TTS provider (Gnani AI or Mock).
    Returns binary audio bytes (audio/wav) with X-TTS-Provider and X-Audio-Type headers,
    or base64 JSON if requested.
    """
    try:
        audio_bytes, mime_type, provider_name = await voice_service.synthesize(
            text=request.text,
            language=request.language or "hi-IN",
            voice_id=request.voice_id,
            speed=request.speed or 1.0,
        )

        audio_type = "test-tone" if provider_name == "mock" else "speech"

        if as_json:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            return TTSResponse(
                success=True,
                audio_base64=b64_audio,
                audio_format=mime_type.split("/")[-1],
                provider=provider_name,
            )

        return Response(
            content=audio_bytes,
            media_type=mime_type,
            headers={
                "X-TTS-Provider": provider_name,
                "X-Audio-Type": audio_type,
                "Content-Disposition": 'inline; filename="synthesized_speech.wav"',
                "Cache-Control": "no-cache",
            },
        )
    except GnaniAuthenticationError as gae:
        sanitized = redact_sensitive(str(gae))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=sanitized,
            headers={"X-TTS-Blocked": "true", "X-TTS-Provider": "gnani"},
        )
    except GnaniAPIError as gae:
        sanitized = redact_sensitive(str(gae))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=sanitized,
            headers={"X-TTS-Provider": "gnani"},
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        sanitized = redact_sensitive(str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS synthesis failed: {sanitized}",
        )


@app.post("/api/stt", response_model=STTResponse, tags=["Voice"])
async def speech_to_text_endpoint(request: STTRequest):
    """
    Transcribes audio to text using active backend STT provider.
    """
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 encoding for audio payload.",
        )

    try:
        result = await voice_service.transcribe(
            audio_data=audio_bytes,
            language=request.language or "hi-IN",
            audio_format=request.audio_format or "wav",
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        sanitized = redact_sensitive(str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"STT transcription failed: {sanitized}",
        )


@app.websocket("/api/ws/stt")
@app.websocket("/ws/stt")
async def websocket_stt_proxy(websocket: WebSocket):
    """
    Real-time streaming Speech-to-Text WebSocket endpoint.
    Proxies browser microphone PCM audio to Gnani Prisma v3.0 over WebSocket.
    """
    await gnani_stt_stream_handler.handle_client_websocket(websocket)


@app.post("/api/provider/tts", tags=["Configuration"])
async def set_tts_provider_endpoint(provider: str = Query(..., description="Provider name: gnani, mock, browser")):
    """Switch the active TTS provider dynamically."""
    try:
        voice_service.set_tts_provider(provider)
        return {"status": "ok", "active_tts_provider": provider.lower()}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@app.post("/api/provider/stt", tags=["Configuration"])
async def set_stt_provider_endpoint(provider: str = Query(..., description="Provider name: browser, gnani, mock")):
    """Switch the active STT provider dynamically."""
    try:
        voice_service.set_stt_provider(provider)
        return {"status": "ok", "active_stt_provider": provider.lower()}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@app.post("/api/provider/llm", tags=["Configuration"])
async def set_llm_provider_endpoint(provider: str = Query(..., description="Provider name: mock, gemini, openai")):
    """Switch the active LLM provider dynamically."""
    try:
        new_provider = get_llm_provider(provider)
        orchestrator.set_llm_provider(new_provider)
        return {
            "status": "ok",
            "active_llm_provider": new_provider.provider_name,
            "provider_status": new_provider.provider_status,
            "is_live_ready": new_provider.is_live_ready(),
        }
    except Exception as exc:
        sanitized = redact_sensitive(str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sanitized)


@app.get("/api/agents", tags=["MultiAgent"])
async def list_agents_endpoint():
    """Returns the list of available specialist agents and their metadata."""
    return {
        "available_agents": orchestrator.get_available_agents(),
        "llm_provider": orchestrator.llm_provider.provider_name,
        "llm_status": orchestrator.llm_provider.provider_status,
    }


# ==============================================================================
# Farm Telemetry & Demo Data Management Endpoints (Phase 10)
# ==============================================================================
from app.services.telemetry_service import telemetry_service
from pydantic import BaseModel as PyBaseModel


class SetActiveZoneRequest(PyBaseModel):
    zone_id: str


@app.get("/api/farm/overview", tags=["Farm Telemetry"])
async def get_farm_overview_endpoint():
    """Returns overview of the simulated farm, all 3 zones, and active alerts."""
    return telemetry_service.get_farm_overview()


@app.get("/api/farm/zones", tags=["Farm Telemetry"])
async def get_farm_zones_endpoint():
    """Returns the list of farm zones and the currently active zone identifier."""
    overview = telemetry_service.get_farm_overview()
    return {
        "farm_id": overview["farm_id"],
        "farm_name": overview["farm_name"],
        "active_zone_id": overview["active_zone_id"],
        "zones": [
            {
                "zone_id": z["zone_id"],
                "zone_name": z["zone_name"],
                "crop": z["crop"],
                "growth_stage": z["growth_stage"],
                "device_status": z["device_status"],
                "soil_moisture_pct": z["soil_moisture_pct"],
                "nitrogen_mg_kg": z["nitrogen_mg_kg"],
                "battery_level_pct": z["battery_level_pct"],
            }
            for z in overview["zones"]
        ],
        "data_source": "simulated",
        "is_simulated": True,
    }


@app.get("/api/farm/telemetry/latest", tags=["Farm Telemetry"])
async def get_latest_telemetry_endpoint(zone_id: Optional[str] = Query(default=None)):
    """Returns latest simulated telemetry readings for a specific zone."""
    return telemetry_service.get_latest_telemetry(zone_id=zone_id)


@app.get("/api/farm/telemetry/history", tags=["Farm Telemetry"])
async def get_historical_telemetry_endpoint(
    zone_id: Optional[str] = Query(default=None),
    parameter: str = Query(default="soil_moisture_pct"),
    time_range: str = Query(default="7d"),
):
    """Returns time-series data and trend summary for a parameter (24h or 7d)."""
    return telemetry_service.get_historical_telemetry(
        zone_id=zone_id,
        parameter=parameter,
        time_range=time_range,
    )


@app.get("/api/farm/alerts", tags=["Farm Telemetry"])
async def get_farm_alerts_endpoint(zone_id: Optional[str] = Query(default=None)):
    """Returns simulated active alerts and threshold warnings."""
    return telemetry_service.get_alert_history(zone_id=zone_id)


@app.post("/api/farm/active-zone", tags=["Farm Telemetry"])
async def set_active_zone_endpoint(request: SetActiveZoneRequest):
    """Sets the active farm zone used for context-grounded voice reasoning."""
    success = telemetry_service.set_active_zone_id(request.zone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{request.zone_id}' not found in simulated farm dataset.",
        )
    return {
        "status": "ok",
        "active_zone_id": request.zone_id,
        "message": f"Active farm zone set to {request.zone_id}",
    }


@app.post("/api/farm/reset", tags=["Farm Telemetry"])
async def reset_farm_dataset_endpoint():
    """Resets the simulated farm environment back to default baseline readings."""
    telemetry_service.reset_demo_dataset()
    pump_control_service.reset()
    return {
        "status": "ok",
        "message": "Simulated farm dataset reset to baseline initial values.",
        "active_zone_id": telemetry_service.get_active_zone_id(),
    }


# =========================================================================
# Phase 19: Seven-Parameter Soil Intelligence Endpoints
# =========================================================================

@app.get("/api/farm/telemetry/profile", tags=["Farm Telemetry"])
async def get_canonical_soil_profile_endpoint(zone_id: Optional[str] = Query(default=None)):
    """
    Returns the canonical 7-in-1 soil profile including quality status, calibration status,
    engineering units, crop benchmarks, completeness ratio, and overall health index.
    """
    zid = zone_id or telemetry_service.get_active_zone_id()
    return telemetry_service.get_canonical_soil_profile(zone_id=zid)


@app.get("/api/farm/telemetry/sodium", tags=["Farm Telemetry"])
async def get_sodium_status_endpoint():
    """
    Returns official clarification on Sodium (Na) measurement scope:
    Confirms that FertoBot 7-in-1 sensor does NOT measure sodium and cannot derive sodium from EC.
    """
    return telemetry_service.get_sodium_status()


@app.post("/api/farm/telemetry/simulate-condition", tags=["Farm Telemetry"])
async def simulate_sensor_condition_endpoint(
    request: SimulateSensorConditionRequest,
    x_team_review_key: Optional[str] = Header(default=None, alias="X-Team-Review-Key"),
):
    """
    Simulates one of the 14 sensor edge/failure conditions across the 7-in-1 profile.
    Protected by TEAM_REVIEW_PASSKEY when configured in staging/production environments.
    """
    required_passkey = os.getenv("TEAM_REVIEW_PASSKEY", "").strip()
    if required_passkey and x_team_review_key != required_passkey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Diagnostic simulation controls require a valid X-Team-Review-Key header.",
        )

    zid = request.zone_id or telemetry_service.get_active_zone_id()
    res = telemetry_service.simulate_sensor_condition(zone_id=zid, condition_type=request.condition_type)
    prof = res.get("profile", {})
    return {
        "status": "ok",
        "zone_id": zid,
        "condition_simulated": request.condition_type,
        "completeness_ratio": prof.get("completeness_ratio"),
        "available_parameters_count": prof.get("available_count"),
        "total_parameters_count": prof.get("total_count", 7),
        "warnings": prof.get("warnings", []),
        "profile": prof,
    }


# =========================================================================
# Phase 18: Safe Pump Control Approval Workflow Endpoints
# =========================================================================

@app.post("/api/pump/action", response_model=PumpActionResponse, tags=["Pump Control"])
async def create_pump_action_endpoint(request: PumpActionRequest):
    """
    Initiates a pump control action that transitions to AWAITING_USER_APPROVAL.
    Does NOT actuate the pump until approved via /api/pump/approve.
    """
    action = pump_control_service.create_action(
        session_id=request.session_id or "default",
        zone_id=request.zone_id,
        action_type=request.action_type,
    )
    is_hindi = (request.language or "hi-IN").lower().startswith("hi")
    crop = telemetry_service.get_zone(action.zone_id).get("crop", "फसल") if telemetry_service.get_zone(action.zone_id) else "फसल"
    
    if is_hindi:
        reply = f"क्या आप {action.zone_id} ({crop}) के लिए पानी का पंप चालू करना चाहते हैं? कृपया नीचे दिए गए बटन से पुष्टि करें।"
    else:
        reply = f"Do you want to turn on the water pump for {action.zone_id} ({crop})? Please confirm using the button below."

    return PumpActionResponse(
        success=True,
        action_id=action.action_id,
        state=action.state,
        reply=reply,
        simulated_pump_running=pump_control_service.get_pump_state(action.zone_id),
        zone_id=action.zone_id,
        sentences=split_into_sentences(reply),
    )


@app.post("/api/pump/approve", response_model=PumpActionResponse, tags=["Pump Control"])
async def approve_pump_action_endpoint(request: PumpApprovalRequest):
    """
    Farmer explicit approval ('हाँ, चालू करें').
    Validates expiration, session authorization, and replay protection.
    Transitions state to COMPLETED and sets simulated pump running state.
    Returns localized speech text for GNANI AI TTS.
    """
    success, reply, action = pump_control_service.approve_action(
        action_id=request.action_id,
        session_id=request.session_id,
        language=request.language or "hi-IN",
    )
    if not success or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reply,
        )

    return PumpActionResponse(
        success=True,
        action_id=action.action_id,
        state=action.state,
        reply=reply,
        simulated_pump_running=pump_control_service.get_pump_state(action.zone_id),
        zone_id=action.zone_id,
        sentences=split_into_sentences(reply),
    )


@app.post("/api/pump/reject", response_model=PumpActionResponse, tags=["Pump Control"])
async def reject_pump_action_endpoint(request: PumpRejectionRequest):
    """
    Farmer explicit rejection ('नहीं, रद्द करें').
    Transitions state to REJECTED.
    Returns localized speech text for GNANI AI TTS.
    """
    success, reply, action = pump_control_service.reject_action(
        action_id=request.action_id,
        session_id=request.session_id,
        language=request.language or "hi-IN",
    )
    if not success or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reply,
        )

    return PumpActionResponse(
        success=True,
        action_id=action.action_id,
        state=action.state,
        reply=reply,
        simulated_pump_running=pump_control_service.get_pump_state(action.zone_id),
        zone_id=action.zone_id,
        sentences=split_into_sentences(reply),
    )


@app.post("/api/pump/emergency-stop", response_model=PumpActionResponse, tags=["Pump Control"])
async def emergency_stop_pump_endpoint(request: PumpEmergencyStopRequest):
    """
    Immediate emergency shutdown: turns off simulated pump immediately without secondary approval.
    """
    success, reply = pump_control_service.emergency_stop(
        session_id=request.session_id or "default",
        zone_id=request.zone_id,
        language=request.language or "hi-IN",
    )
    resolved_zone = request.zone_id or telemetry_service.get_active_zone_id()
    return PumpActionResponse(
        success=success,
        action_id=None,
        state="STOPPED",
        reply=reply,
        simulated_pump_running=pump_control_service.get_pump_state(resolved_zone),
        zone_id=resolved_zone,
        sentences=split_into_sentences(reply),
    )


@app.get("/api/pump/status", tags=["Pump Control"])
async def get_pump_status_endpoint(zone_id: Optional[str] = Query(default=None)):
    """
    Returns simulated pump operating states, active approvals, and safety isolation parameters.
    """
    return pump_control_service.get_status(zone_id=zone_id)


# =========================================================================
# Phase 20/21: Staging Single-Service Static Asset Serving
# Mounts built production frontend from dist/ when present
# =========================================================================
candidate_dists = [
    Path(__file__).resolve().parent.parent.parent / "dist",
    Path(__file__).resolve().parent.parent / "dist",
    Path("/dist"),
    Path("./dist"),
]
dist_path = next((p for p in candidate_dists if p.exists() and (p / "index.html").exists()), None)
if dist_path:
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static_frontend")

