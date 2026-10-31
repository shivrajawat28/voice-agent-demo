"""
Pydantic Data Models for Request, Response, and Health Schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "fertobot-voice-agent-backend"
    version: str = "0.2.0"


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User speech transcript or text message",
    )
    language: Optional[str] = Field(
        default="en-US",
        description="Target interaction language code (e.g. en-US, hi-IN)",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session or client identifier",
    )
    zone_id: Optional[str] = Field(
        default=None,
        description="Optional target farm zone identifier (e.g. DEMO-ZONE-001)",
    )


class ClearSessionRequest(BaseModel):
    session_id: Optional[str] = Field(
        default="default",
        description="Target session identifier to clear memory and greetings",
    )


class AgentResult(BaseModel):
    agent_id: str = Field(..., description="Unique specialist agent identifier")
    name: str = Field(..., description="Human-readable specialist agent name")
    status: str = Field(..., description="Execution status: completed, failed, skipped, inconclusive")
    summary: str = Field(..., description="Summary of specialist findings or guidance")
    evidence: List[str] = Field(default_factory=list, description="Data points, thresholds, or observations used")
    limitations: List[str] = Field(default_factory=list, description="Missing parameters or uncertainty notes")
    data: Dict[str, Any] = Field(default_factory=dict, description="Raw structured data payload")


class ExecutionTraceStep(BaseModel):
    step_id: str = Field(..., description="Unique step identifier")
    agent_id: str = Field(..., description="Agent or component responsible for step")
    action: str = Field(..., description="Action taken, e.g. 'plan', 'tool_call', 'synthesize'")
    status: str = Field(..., description="Step outcome: started, completed, failed, skipped")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    details: Optional[str] = Field(default=None, description="Diagnostic detail or tool name")


class PumpActionPayload(BaseModel):
    action_id: str = Field(..., description="Unique action approval identifier")
    session_id: str = Field(..., description="Target session requesting pump operation")
    zone_id: str = Field(..., description="Target farm zone identifier")
    probe_id: str = Field(..., description="Target probe/device identifier")
    action_type: str = Field(..., description="'PUMP_ON' or 'PUMP_OFF'")
    state: str = Field(
        default="AWAITING_USER_APPROVAL",
        description="Action state: AWAITING_USER_APPROVAL, APPROVED, REJECTED, EXECUTING, COMPLETED, EXPIRED",
    )
    created_at: float = Field(..., description="Unix timestamp of request creation")
    expires_at: float = Field(..., description="Unix timestamp of approval expiry (5 minutes)")
    simulation_mode: bool = Field(default=True, description="Strict safety flag indicating simulated hardware")
    actuation_permitted: bool = Field(default=False, description="Strict safety flag preventing physical relay fire")
    message: Optional[str] = Field(default=None, description="Agronomic or confirmation explanation")


class ChatResponse(BaseModel):
    success: bool = True
    reply: str
    intent: str
    confidence: float = 1.0
    repeatable: bool = True
    agent_results: Optional[List[AgentResult]] = Field(
        default=None,
        description="Structured outputs from specialist agents invoked during query execution",
    )
    execution_trace: Optional[List[ExecutionTraceStep]] = Field(
        default=None,
        description="Step-by-step audit trace of agent planning, tool invocations, and synthesis",
    )
    sources: Optional[List[str]] = Field(
        default=None,
        description="Attributed knowledge or telemetry sources utilized in reasoning",
    )
    warnings: Optional[List[str]] = Field(
        default=None,
        description="Safety, physiological, or data-gap warnings for agricultural decisions",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if critical grower context (e.g. crop type, days since watering) is required",
    )
    clarification_prompt: Optional[str] = Field(
        default=None,
        description="Specific localized clarification question if needs_clarification is True",
    )
    sentences: Optional[List[str]] = Field(
        default=None,
        description="Response partitioned into speakable sentences for progressive streaming and audio synthesis",
    )
    provider_status: str = Field(
        default="mock",
        description="Underlying LLM brain status: 'mock', 'live', or 'deterministic'",
    )
    pending_action: Optional[PumpActionPayload] = Field(
        default=None,
        description="Pending hardware/pump action awaiting explicit user approval",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PumpApprovalRequest(BaseModel):
    action_id: str = Field(..., description="Action ID to approve")
    session_id: str = Field(..., description="Session ID confirming authorization")
    language: Optional[str] = Field(default="hi-IN", description="Language for verbal confirmation")


class PumpRejectionRequest(BaseModel):
    action_id: str = Field(..., description="Action ID to reject/cancel")
    session_id: str = Field(..., description="Session ID confirming cancellation")
    language: Optional[str] = Field(default="hi-IN", description="Language for verbal cancellation")


class PumpActionRequest(BaseModel):
    session_id: Optional[str] = Field(default="default", description="Session ID")
    zone_id: Optional[str] = Field(default=None, description="Target zone ID")
    action_type: str = Field(default="PUMP_ON", description="'PUMP_ON' or 'PUMP_OFF'")
    language: Optional[str] = Field(default="hi-IN", description="Response language")


class PumpEmergencyStopRequest(BaseModel):
    session_id: Optional[str] = Field(default="default", description="Session ID")
    zone_id: Optional[str] = Field(default=None, description="Target zone ID or None for all")
    language: Optional[str] = Field(default="hi-IN", description="Language for response")


class PumpActionResponse(BaseModel):
    success: bool = True
    action_id: Optional[str] = None
    state: str
    reply: str
    simulated_pump_running: bool
    zone_id: str
    sentences: List[str] = Field(default_factory=list)
    safety_notice: str = "Simulation mode active. Physical hardware relay actuation is disabled."



class TTSRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Text content to synthesize into speech audio",
    )
    language: Optional[str] = Field(
        default="hi-IN",
        description="Target language code (e.g. hi-IN, en-IN)",
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="Optional voice identifier (e.g. Shivani, Pratibha)",
    )
    speed: Optional[float] = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech rate multiplier (0.5 to 2.0)",
    )


class TTSResponse(BaseModel):
    success: bool = True
    audio_base64: Optional[str] = None
    audio_format: str = "wav"
    provider: str
    cached: bool = False
    message: Optional[str] = None


class STTRequest(BaseModel):
    audio_base64: str = Field(
        ...,
        min_length=1,
        description="Base64-encoded audio data to transcribe",
    )
    language: Optional[str] = Field(
        default="hi-IN",
        description="Target speech language code (e.g. hi-IN, en-IN)",
    )
    audio_format: Optional[str] = Field(
        default="wav",
        description="Input audio format (wav, mp3, ogg, pcm)",
    )


class STTResponse(BaseModel):
    success: bool = True
    text: str
    language: str
    confidence: float = 1.0
    provider: str


class ConfigResponse(BaseModel):
    tts_provider: str
    stt_provider: str
    conversation_provider: str
    gnani_configured: bool
    available_voices: Dict[str, List[str]]
    supported_languages: List[str]
    llm_provider: str = "mock"
    llm_status: str = "mock"
    llm_configured: bool = False
    available_agents: List[str] = Field(default_factory=list)


class SimulateSensorConditionRequest(BaseModel):
    zone_id: Optional[str] = Field(default="DEMO-ZONE-001", description="Target zone ID")
    condition_type: str = Field(
        ...,
        description="Sensor condition type to simulate (e.g. nitrogen_unavailable, phosphorus_uncalibrated, potassium_stale, moisture_invalid, temp_disconnected, ph_out_of_range, ec_unavailable, multiple_disconnected, device_offline, conflicting_timestamps, multi_zone_variance, partial_report, sodium_inquiry, all_valid)",
    )
