/**
 * FertoBot Voice Agent Demo — Type Definitions
 * Phase 6: Voice Reliability, Mock Fix, Gnani Verification & Real Speech Validation
 */

export type AgentState = 'idle' | 'listening' | 'finalizing' | 'processing' | 'speaking' | 'error';

export type StateEvent =
  | 'START_LISTENING'
  | 'FINALIZE_START'
  | 'TRANSCRIPTION_RECEIVED'
  | 'TEXT_SUBMITTED'
  | 'SPEAK_START'
  | 'SPEAK_END'
  | 'FAIL'
  | 'CANCEL_OR_RESET';

export type IntentType =
  | 'greeting'
  | 'intro'
  | 'help'
  | 'repeat'
  | 'goodbye'
  | 'farm_status'
  | 'agricultural_inquiry'
  | 'symptom_inquiry'
  | 'irrigation_inquiry'
  | 'unknown';

export type TTSProviderType = 'browser' | 'gnani' | 'mock';
export type STTProviderType = 'browser' | 'gnani' | 'gnani_prisma_v3' | 'mock';
export type LLMProviderType = 'mock' | 'gemini' | 'openai';

export type TTSRuntimeStatus =
  | 'browser_native'
  | 'gnani_live'
  | 'mock_test_tone'
  | 'gnani_blocked_fallback'
  | 'gnani_error_fallback'
  | 'GNANI_TTS_LIVE'
  | 'GNANI_TTS_BLOCKED'
  | 'GNANI_TTS_ERROR'
  | 'GYANI_TTS_LIVE'
  | 'BROWSER_TTS_ACTIVE'
  | 'GYANI_TTS_BLOCKED'
  | 'GYANI_TTS_ERROR';

export type GyaniAudioPlaybackStatus =
  | 'IDLE'
  | 'GNANI AUDIO IDLE'
  | 'GNANI AUDIO GENERATING'
  | 'GNANI AUDIO READY'
  | 'GNANI AUDIO PLAYING'
  | 'GNANI AUDIO FAILED'
  | 'GYANI AUDIO GENERATING'
  | 'GYANI AUDIO READY'
  | 'GYANI AUDIO PLAYING'
  | 'GYANI AUDIO FAILED';

export type STTRuntimeStatus =
  | 'browser_native'
  | 'gnani_prisma_v3_live'
  | 'gnani_blocked_fallback'
  | 'mock'
  | 'error'
  | 'GNANI_STT_LIVE'
  | 'GNANI_STT_BLOCKED'
  | 'GNANI_STT_ERROR'
  | 'GYANI_STT_LIVE'
  | 'BROWSER_STT_ACTIVE'
  | 'GYANI_STT_BLOCKED'
  | 'GYANI_STT_ERROR';

export interface PumpActionPayload {
  action_id: string;
  session_id: string;
  zone_id: string;
  probe_id: string;
  action_type: 'PUMP_ON' | 'PUMP_OFF';
  state: 'AWAITING_USER_APPROVAL' | 'APPROVED' | 'REJECTED' | 'EXECUTING' | 'COMPLETED' | 'EXPIRED';
  created_at: number;
  expires_at: number;
  simulation_mode: boolean;
  actuation_permitted: boolean;
  message?: string;
}

export interface AgentResult {
  agent_id: string;
  name: string;
  status: string;
  summary: string;
  evidence: string[];
  limitations: string[];
  data?: Record<string, any>;
}

export interface ExecutionTraceStep {
  step_id: string;
  agent_id: string;
  action: string;
  status: string;
  duration_ms: number;
  details?: string;
}

export type StreamingPlaybackState =
  | 'IDLE'
  | 'THINKING'
  | 'STREAMING TEXT'
  | 'GENERATING AUDIO'
  | 'SPEAKING'
  | 'COMPLETED';

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  text: string;
  sentences?: string[];
  timestamp: Date;
  intent?: IntentType;
  agentResults?: AgentResult[];
  executionTrace?: ExecutionTraceStep[];
  sources?: string[];
  warnings?: string[];
  needsClarification?: boolean;
  clarificationPrompt?: string;
  providerStatus?: string;
  pendingAction?: PumpActionPayload;
}

export interface EngineResponse {
  intent: IntentType;
  text: string;
  sentences?: string[];
  confidence: number;
  repeatable: boolean;
  agent_results?: AgentResult[];
  execution_trace?: ExecutionTraceStep[];
  sources?: string[];
  warnings?: string[];
  needs_clarification?: boolean;
  clarification_prompt?: string;
  provider_status?: string;
  pending_action?: PumpActionPayload;
  metadata?: Record<string, any>;
}

export interface VoiceCapabilities {
  speechRecognitionSupported: boolean;
  speechSynthesisSupported: boolean;
  isWebKit: boolean;
  hasHindiVoice?: boolean;
  selectedVoiceName?: string;
}

export type MicPermissionState = 'prompt' | 'granted' | 'denied' | 'unsupported';

export interface BackendConfig {
  tts_provider: TTSProviderType;
  stt_provider: STTProviderType;
  conversation_provider: string;
  gnani_configured: boolean;
  available_voices: Record<string, string[]>;
  supported_languages: string[];
  llm_provider?: string;
  llm_status?: string;
  llm_configured?: boolean;
  available_agents?: string[];
}

export interface SoilParameterReading {
  parameter_name: string;
  display_name: string;
  value: number | null;
  raw_value: number | null;
  unit: string;
  quality_status: 'VALID' | 'SUSPECT' | 'OUT_OF_RANGE' | 'STALE' | 'UNAVAILABLE';
  calibration_status: 'CALIBRATED' | 'UNCALIBRATED';
  timestamp_iso: string;
  sensor_channel_id: string;
  benchmark_range?: {
    min: number;
    max: number;
    optimal_min: number;
    optimal_max: number;
    unit: string;
    description: string;
  };
  agricultural_relevance?: string;
}

export interface CanonicalSoilProfile {
  farm_id: string;
  zone_id: string;
  zone_name: string;
  crop: string;
  growth_stage: string;
  soil_type: string;
  device_id: string;
  device_status: string;
  battery_level_pct: number;
  water_tank_level_pct: number;
  data_source: string;
  is_simulated: boolean;
  timestamp_iso: string;
  completeness_ratio: string;
  available_parameters_count: number;
  total_parameters_count: number;
  overall_soil_health_index: number;
  parameters: Record<string, SoilParameterReading>;
  warnings: string[];
}

export interface FarmZoneTelemetry {
  farm_id: string;
  farm_name: string;
  farmer_name: string;
  zone_id: string;
  zone_name: string;
  crop: string;
  variety?: string;
  growth_stage: string;
  soil_type: string;
  device_id: string;
  device_status: 'online' | 'warning' | 'offline';
  battery_level_pct: number;
  water_tank_level_pct: number;
  last_seen_iso: string;
  soil_moisture_pct: number;
  nitrogen_mg_kg: number | null;
  phosphorus_mg_kg: number | null;
  potassium_mg_kg: number | null;
  soil_temperature_c: number;
  ph: number;
  electrical_conductivity_ds_m: number;
  completeness_ratio?: string;
  canonical_soil_profile?: CanonicalSoilProfile;
  data_source: 'simulated' | 'live';
  is_simulated: boolean;
  reading_timestamp_iso: string;
  missing_fields: string[];
  warnings: string[];
}

export interface FarmAlert {
  alert_id: string;
  zone_id: string;
  device_id: string;
  severity: 'advisory' | 'warning' | 'critical';
  category?: string;
  title: string;
  message: string;
  timestamp_iso: string;
  resolved: boolean;
}

export interface FarmOverview {
  farm_id: string;
  farm_name: string;
  farmer_name: string;
  location: string;
  active_zone_id: string;
  zones: FarmZoneTelemetry[];
  active_alerts: FarmAlert[];
  data_source: 'simulated';
  is_simulated: boolean;
}
