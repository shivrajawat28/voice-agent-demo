/**
 * useVoiceAgent Hook
 *
 * Encapsulates the complete Voice Agent interaction lifecycle:
 * State Machine + Multi-Agent Orchestrator + Voice Controller + Provider Audio Synthesis.
 * Phase 14: Real-time sentence-level streaming playback queue, progressive text synchronization,
 * Web Audio Analyser RMS VU-meter & waveform data, and device selection.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  AgentState,
  ChatMessage,
  EngineResponse,
  VoiceCapabilities,
  MicPermissionState,
  TTSProviderType,
  TTSRuntimeStatus,
  GyaniAudioPlaybackStatus,
  STTProviderType,
  STTRuntimeStatus,
  BackendConfig,
  StreamingPlaybackState,
} from '../types/voiceAgent';
import { AgentStateMachine } from '../services/AgentStateMachine';
import { ConversationEngine } from '../services/ConversationEngine';
import { VoiceController } from '../services/VoiceController';

export interface UseVoiceAgentReturn {
  state: AgentState;
  transcript: ChatMessage[];
  lastError: string | null;
  lastAgentResponse: string | null;
  capabilities: VoiceCapabilities;
  micPermission: MicPermissionState;
  language: string;
  sttProvider: STTProviderType;
  sttRuntimeStatus: STTRuntimeStatus;
  sttStatusMessage: string;
  ttsProvider: TTSProviderType;
  ttsRuntimeStatus: TTSRuntimeStatus;
  ttsStatusMessage: string;
  gyaniAudioStatus: GyaniAudioPlaybackStatus;
  gnaniConfigured: boolean;
  llmProvider: string;
  llmStatus: string;
  llmConfigured: boolean;
  availableAgents: string[];
  activeZoneId: string;
  selectedVoice: string;
  ttsSpeed: number;
  // Phase 14 Audio & Visualizer State
  audioLevel: number;
  waveformData?: Uint8Array;
  isSpeakingDetected: boolean;
  partialTranscript: string | null;
  selectedDeviceId: string | null;
  setSelectedDeviceId: (id: string | null) => void;
  // Phase 14 Streaming Audio State
  currentSpeakingMsgId: string | null;
  currentSpeakingSentenceIndex: number | null;
  playbackState: StreamingPlaybackState;
  revealedSentenceCount: Record<string, number>;
  replayMessage: (msgId: string) => void;
  setSelectedVoice: (voice: string) => void;
  setTTSSpeed: (speed: number) => void;
  setSTTProvider: (provider: STTProviderType) => void;
  setActiveZoneId: (zoneId: string) => void;
  setLLMProvider: (provider: string) => void;
  setTTSProvider: (provider: TTSProviderType) => void;
  setLanguage: (lang: string) => void;
  startListening: () => boolean;
  finishListening: () => void;
  stopOrCancel: () => void;
  submitText: (input: string) => boolean;
  repeatLastResponse: () => void;
  clearTranscript: () => void;
  vocalizeWithBrowserFallback: () => void;
  retryLastTTS: () => Promise<void>;
  approvePumpAction: (actionId: string) => Promise<void>;
  rejectPumpAction: (actionId: string) => Promise<void>;
}

export function useVoiceAgent(initialLanguage: string = 'en-US'): UseVoiceAgentReturn {
  const [agentState, setAgentState] = useState<AgentState>('idle');
  const [transcript, setTranscript] = useState<ChatMessage[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);
  const [micPermission, setMicPermission] = useState<MicPermissionState>('prompt');
  const [language, setLanguageState] = useState<string>(initialLanguage);
  const [sttProvider, setSTTProviderState] = useState<STTProviderType>('browser');
  const [sttRuntimeStatus, setSTTRuntimeStatus] = useState<STTRuntimeStatus>('browser_native');
  const [sttStatusMessage, setSTTStatusMessage] = useState<string>(
    'Browser Native SpeechRecognition active'
  );
  const [ttsProvider, setTTSProviderState] = useState<TTSProviderType>('browser');
  const [ttsRuntimeStatus, setTTSRuntimeStatus] = useState<TTSRuntimeStatus>('browser_native');
  const [ttsStatusMessage, setTTSStatusMessage] = useState<string>(
    'Browser Native SpeechSynthesis active (audible speech)'
  );
  const [gyaniAudioStatus, setGyaniAudioStatus] = useState<GyaniAudioPlaybackStatus>('IDLE');
  const [selectedVoice, setSelectedVoiceState] = useState<string>('Nalini');
  const [ttsSpeed, setTTSSpeedState] = useState<number>(1.0);
  const [gnaniConfigured, setGnaniConfigured] = useState<boolean>(false);
  const [llmProvider, setLlmProviderState] = useState<string>('mock');
  const [llmStatus, setLlmStatusState] = useState<string>('mock');
  const [llmConfigured, setLlmConfiguredState] = useState<boolean>(false);
  const [availableAgents, setAvailableAgentsState] = useState<string[]>([]);
  const [activeZoneId, setActiveZoneIdState] = useState<string>('DEMO-ZONE-001');

  // Phase 14 Audio Analyser & Waveform State
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [waveformData, setWaveformData] = useState<Uint8Array | undefined>(undefined);
  const [isSpeakingDetected, setIsSpeakingDetected] = useState<boolean>(false);
  const [partialTranscript, setPartialTranscript] = useState<string | null>(null);
  const [selectedDeviceId, setSelectedDeviceIdState] = useState<string | null>(null);

  // Phase 14 Sentence-level Streaming Playback State
  const [currentSpeakingMsgId, setCurrentSpeakingMsgId] = useState<string | null>(null);
  const [currentSpeakingSentenceIndex, setCurrentSpeakingSentenceIndex] = useState<number | null>(null);
  const [playbackState, setPlaybackState] = useState<StreamingPlaybackState>('IDLE');
  const [revealedSentenceCount, setRevealedSentenceCount] = useState<Record<string, number>>({});
  const playbackAbortRef = useRef<AbortController | null>(null);

  const sessionIdRef = useRef<string>(
    `sess-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`
  );
  // Phase 26 Speech Utterance and Idempotency Refs
  const activeUtteranceIdRef = useRef<string | null>(null);
  const isProcessingTurnRef = useRef<boolean>(false);

  const stateMachineRef = useRef<AgentStateMachine>(new AgentStateMachine('idle'));
  const conversationEngineRef = useRef<ConversationEngine>(new ConversationEngine());
  const voiceControllerRef = useRef<VoiceController>(new VoiceController());

  const capabilities = VoiceController.getCapabilities();

  // Sync state machine
  useEffect(() => {
    const sm = stateMachineRef.current;
    const unsubscribe = sm.subscribe((newState, err) => {
      setAgentState(newState);
      setLastError(err);
    });
    return () => unsubscribe();
  }, []);

  // Fetch backend config on mount
  useEffect(() => {
    fetch('/api/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((cfg: BackendConfig | null) => {
        if (cfg) {
          setGnaniConfigured(cfg.gnani_configured);
          if (cfg.llm_provider) setLlmProviderState(cfg.llm_provider);
          if (cfg.llm_status) setLlmStatusState(cfg.llm_status);
          if (cfg.llm_configured !== undefined) setLlmConfiguredState(cfg.llm_configured);
          if (cfg.available_agents) setAvailableAgentsState(cfg.available_agents);

          if (cfg.gnani_configured) {
            setTTSProviderState('gnani');
            setTTSRuntimeStatus('gnani_live');
            setTTSStatusMessage('GNANI AI TTS: Live Neural Timbre v2.5 ready');
            setSTTProviderState('gnani_prisma_v3');
            setSTTRuntimeStatus('gnani_prisma_v3_live');
            setSTTStatusMessage('GNANI AI STT: Live WebSocket streaming (Prisma v3.0, indic-auto)');
          } else {
            setTTSProviderState('browser');
            setTTSRuntimeStatus('browser_native');
            setTTSStatusMessage('Browser Native SpeechSynthesis active (recommended for demo)');
          }
        }
      })
      .catch(() => {
        setTTSProviderState('browser');
        setTTSRuntimeStatus('browser_native');
        setTTSStatusMessage('Browser Native SpeechSynthesis active (offline mode)');
      });
  }, []);

  useEffect(() => {
    VoiceController.queryMicPermission().then((status) => {
      setMicPermission(status);
    });

    return () => {
      playbackAbortRef.current?.abort();
      voiceControllerRef.current.cancelAll();
      stateMachineRef.current.cancel();
    };
  }, []);

  const setSelectedDeviceId = useCallback((deviceId: string | null) => {
    setSelectedDeviceIdState(deviceId);
    voiceControllerRef.current.setSelectedDeviceId(deviceId);
  }, []);

  const setLLMProvider = useCallback((newProvider: string) => {
    setLlmProviderState(newProvider);
    fetch(`/api/provider/llm?provider=${newProvider}`, { method: 'POST' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setLlmStatusState(data.provider_status);
          setLlmConfiguredState(data.is_live_ready);
        }
      })
      .catch(() => {});
  }, []);

  const setTTSProvider = useCallback(
    (provider: TTSProviderType) => {
      setTTSProviderState(provider);
      if (provider === 'browser') {
        setTTSRuntimeStatus('browser_native');
        setTTSStatusMessage('Browser Native SpeechSynthesis active (audible speech)');
      } else if (provider === 'mock') {
        setTTSRuntimeStatus('mock_test_tone');
        setTTSStatusMessage('Mock / Test Tone active (diagnostic sine wave tone — no speech)');
      } else if (provider === 'gnani') {
        if (!gnaniConfigured) {
          setTTSRuntimeStatus('gnani_blocked_fallback');
          setTTSStatusMessage(
            'GNANI AI TTS: Blocked (No API key in backend/.env). Browser Native fallback will vocalize speech.'
          );
        } else {
          setTTSRuntimeStatus('gnani_live');
          setTTSStatusMessage(`GNANI AI TTS: Live Neural Timbre v2.5 ready (${selectedVoice})`);
        }
      }
      fetch(`/api/provider/tts?provider=${provider}`, { method: 'POST' }).catch(() => {});
    },
    [gnaniConfigured, selectedVoice]
  );

  const setSTTProvider = useCallback(
    (provider: STTProviderType) => {
      setSTTProviderState(provider);
      if (provider === 'browser') {
        setSTTRuntimeStatus('browser_native');
        setSTTStatusMessage('Browser Native SpeechRecognition active');
      } else if (provider === 'mock') {
        setSTTRuntimeStatus('mock');
        setSTTStatusMessage('Mock STT provider active');
      } else if (provider === 'gnani_prisma_v3' || provider === 'gnani') {
        if (!gnaniConfigured) {
          setSTTRuntimeStatus('gnani_blocked_fallback');
          setSTTStatusMessage('GNANI AI STT unavailable — API credentials required.');
        } else {
          setSTTRuntimeStatus('gnani_prisma_v3_live');
          setSTTStatusMessage('GNANI AI STT: Live WebSocket streaming (Prisma v3.0, indic-auto)');
        }
      }
      fetch(`/api/provider/stt?provider=${provider}`, { method: 'POST' }).catch(() => {});
    },
    [gnaniConfigured]
  );

  // Progressive Sentence-Level Audio Playback Queue
  const playSentenceQueue = useCallback(
    async (sentences: string[], msgId: string, abortSignal: AbortSignal) => {
      const vc = voiceControllerRef.current;
      const sm = stateMachineRef.current;

      setCurrentSpeakingMsgId(msgId);
      setPlaybackState('GENERATING AUDIO');

      if (sm.can('SPEAK_START')) {
        sm.transition('SPEAK_START');
      }

      // Build speakable chunks: if leading sentence is very short (<= 5 words, e.g. greeting),
      // merge with next sentence so initial playback duration (~3.5s) masks subsequent prefetch latency
      // and eliminates the 1-2 second awkward silence.
      interface SpeakableChunk {
        text: string;
        targetRevealedCount: number;
      }
      const chunks: SpeakableChunk[] = [];
      let idx = 0;
      while (idx < sentences.length) {
        const s = sentences[idx].trim();
        if (!s) {
          idx++;
          continue;
        }
        const words = s.split(/\s+/).filter(Boolean);
        if (words.length <= 5 && idx + 1 < sentences.length) {
          chunks.push({
            text: `${s} ${sentences[idx + 1].trim()}`,
            targetRevealedCount: idx + 2,
          });
          idx += 2;
        } else {
          chunks.push({
            text: s,
            targetRevealedCount: idx + 1,
          });
          idx += 1;
        }
      }
      if (chunks.length === 0 && sentences.length > 0) {
        chunks.push({ text: sentences.join(' '), targetRevealedCount: sentences.length });
      }

      // Pre-fetch cache for next sentence audio
      let prefetchPromise: Promise<Blob | null> | null = null;
      let nextPreloadedAudio: { audio: HTMLAudioElement; url: string } | null = null;

      const fetchSentenceTTS = async (textToSpeak: string): Promise<Blob | null> => {
        try {
          const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: textToSpeak,
              language,
              voice_id: selectedVoice,
              speed: ttsSpeed,
            }),
            signal: abortSignal,
          });
          const ct = res.headers.get('content-type') || '';
          if (res.ok && ct.startsWith('audio/')) {
            const blob = await res.blob();
            if (blob.size > 44) return blob;
          }
        } catch (e: any) {
          if (e.name !== 'AbortError') {
            console.warn('Sentence TTS fetch error:', e);
          }
        }
        return null;
      };

      for (let cIdx = 0; cIdx < chunks.length; cIdx++) {
        if (abortSignal.aborted) break;

        const currentChunk = chunks[cIdx];
        setCurrentSpeakingSentenceIndex(cIdx);

        // Case A: Live Gnani Neural TTS
        if (ttsProvider === 'gnani' && gnaniConfigured) {
          setGyaniAudioStatus('GNANI AUDIO GENERATING');
          setPlaybackState('GENERATING AUDIO');

          // Get audio blob (either preloaded, pre-fetched, or fetch now)
          let audioBlob: Blob | null = null;
          const preloadedObj = nextPreloadedAudio;
          nextPreloadedAudio = null;

          if (!preloadedObj) {
            if (prefetchPromise) {
              audioBlob = await prefetchPromise;
              prefetchPromise = null;
            }
            if (!audioBlob && !abortSignal.aborted) {
              audioBlob = await fetchSentenceTTS(currentChunk.text);
            }
          }

          if (abortSignal.aborted) break;

          if (preloadedObj || audioBlob) {
            // Progressive sentence disclosure: reveal this chunk as its audio starts
            setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: currentChunk.targetRevealedCount }));
            setGyaniAudioStatus('GNANI AUDIO PLAYING');
            setPlaybackState('SPEAKING');

            // While current sentence plays, start pre-fetching & pre-loading the NEXT sentence!
            if (cIdx + 1 < chunks.length && !abortSignal.aborted) {
              const nextChunk = chunks[cIdx + 1];
              prefetchPromise = fetchSentenceTTS(nextChunk.text).then((blob) => {
                if (blob && !abortSignal.aborted) {
                  try {
                    nextPreloadedAudio = vc.createPreloadedAudio(blob);
                  } catch {}
                }
                return blob;
              });
            }

            // Play audio and await end
            await new Promise<void>((resolve) => {
              let played = false;
              if (preloadedObj) {
                played = vc.playPreloadedAudio(
                  preloadedObj,
                  () => resolve(),
                  () => resolve(),
                  () => {
                    setGyaniAudioStatus('GNANI AUDIO PLAYING');
                    setPlaybackState('SPEAKING');
                  }
                );
              } else if (audioBlob) {
                played = vc.playAudioBlob(
                  audioBlob,
                  () => resolve(),
                  () => resolve(),
                  () => {
                    setGyaniAudioStatus('GNANI AUDIO PLAYING');
                    setPlaybackState('SPEAKING');
                  }
                );
              }
              if (!played) resolve();
            });
          } else {
            // If TTS fetch failed for this sentence, fall back to browser speech for this sentence
            if (capabilities.speechSynthesisSupported && !abortSignal.aborted) {
              setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: currentChunk.targetRevealedCount }));
              setPlaybackState('SPEAKING');
              await new Promise<void>((resolve) => {
                vc.speak(currentChunk.text, () => resolve());
              });
            }
          }
        }
        // Case B: Mock Test Tone
        else if (ttsProvider === 'mock') {
          setPlaybackState('SPEAKING');
          const mockBlob = await fetchSentenceTTS(currentChunk.text);
          if (mockBlob && !abortSignal.aborted) {
            setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: currentChunk.targetRevealedCount }));
            await new Promise<void>((resolve) => {
              vc.playAudioBlob(mockBlob, () => resolve());
            });
          }
        }
        // Case C: Browser Native SpeechSynthesis
        else {
          setPlaybackState('SPEAKING');
          if (capabilities.speechSynthesisSupported && !abortSignal.aborted) {
            setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: currentChunk.targetRevealedCount }));
            await new Promise<void>((resolve) => {
              vc.speak(currentChunk.text, () => resolve());
            });
          }
        }
      }

      if (!abortSignal.aborted) {
        setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: sentences.length }));
        setGyaniAudioStatus('IDLE');
        setPlaybackState('COMPLETED');
        setCurrentSpeakingSentenceIndex(null);
        setCurrentSpeakingMsgId(null);
        isProcessingTurnRef.current = false;
        if (sm.getState() === 'speaking' || sm.getState() === 'processing') {
          sm.transition('SPEAK_END');
        }
      } else {
        setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: sentences.length }));
        isProcessingTurnRef.current = false;
      }
    },
    [capabilities.speechSynthesisSupported, gnaniConfigured, language, selectedVoice, ttsProvider, ttsSpeed]
  );

  // Dispatch processing of text (from speech or manual input)
  const handleProcessInput = useCallback(
    async (rawText: string) => {
      const sm = stateMachineRef.current;
      const engine = conversationEngineRef.current;

      const trimmed = rawText.trim();
      if (!trimmed) {
        sm.cancel();
        return;
      }

      // Abort any ongoing playback queue
      playbackAbortRef.current?.abort();
      const abortController = new AbortController();
      playbackAbortRef.current = abortController;

      // 1. Append user turn
      const userMsg: ChatMessage = {
        id: `usr-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        role: 'user',
        text: trimmed,
        timestamp: new Date(),
      };
      setTranscript((prev) => [...prev, userMsg]);
      setPlaybackState('THINKING');

      // 2. Query Backend Endpoint with Seamless Offline Local Fallback
      let engineResult: EngineResponse | null = null;
      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: trimmed,
            language,
            session_id: sessionIdRef.current,
            zone_id: activeZoneId,
          }),
        });
        if (response.ok) {
          const data = await response.json();
          engineResult = {
            intent: data.intent,
            text: data.reply,
            sentences: data.sentences,
            confidence: data.confidence,
            repeatable: data.repeatable,
            agent_results: data.agent_results,
            execution_trace: data.execution_trace,
            sources: data.sources,
            warnings: data.warnings,
            needs_clarification: data.needs_clarification,
            clarification_prompt: data.clarification_prompt,
            provider_status: data.provider_status,
            pending_action: data.pending_action,
            metadata: data.metadata,
          };
        }
      } catch {}

      if (!engineResult) {
        engineResult = engine.processInput(trimmed);
      }
      if (!engineResult) {
        sm.cancel();
        setPlaybackState('IDLE');
        return;
      }

      engine.setLastResponse(engineResult.text);

      // Split into sentences if not already partitioned by backend
      const sentenceList =
        engineResult.sentences && engineResult.sentences.length > 0
          ? engineResult.sentences
          : engineResult.text
              .split(/([।\?!]|\n+|(?<!\d)\.(?!\d))/)
              .filter((s) => s && s.trim().length > 0);

      // 3. Append agent response to transcript with sentence chunks
      const agentMsgId = `agt-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
      const agentMsg: ChatMessage = {
        id: agentMsgId,
        role: 'agent',
        text: engineResult.text,
        sentences: sentenceList,
        timestamp: new Date(),
        intent: engineResult.intent,
        agentResults: engineResult.agent_results,
        executionTrace: engineResult.execution_trace,
        sources: engineResult.sources,
        warnings: engineResult.warnings,
        needsClarification: engineResult.needs_clarification,
        clarificationPrompt: engineResult.clarification_prompt,
        providerStatus: engineResult.provider_status,
        pendingAction: engineResult.pending_action,
      };

      setTranscript((prev) => [...prev, agentMsg]);
      // Initialize progressive reveal to 0 sentences until audio starts playing
      setRevealedSentenceCount((prev) => ({ ...prev, [agentMsgId]: 0 }));
      setPlaybackState('STREAMING TEXT');

      // 4. Progressive Sentence-Level Audio Playback
      playSentenceQueue(sentenceList, agentMsgId, abortController.signal);
    },
    [activeZoneId, language, playSentenceQueue]
  );

  // Wire VoiceController callbacks
  useEffect(() => {
    const vc = voiceControllerRef.current;
    const sm = stateMachineRef.current;

    vc.setCallbacks({
      onListeningStart: () => {
        setPartialTranscript(null);
      },
      onListeningEnd: () => {
        setPartialTranscript(null);
        if (sm.getState() === 'listening') {
          sm.cancel();
        } else if (sm.getState() === 'finalizing' && !isProcessingTurnRef.current) {
          sm.cancel();
        }
      },
      onTranscriptionResult: (transcriptText: string, utteranceId?: string) => {
        setPartialTranscript(null);
        if (utteranceId && activeUtteranceIdRef.current && utteranceId !== activeUtteranceIdRef.current) {
          // Stale callback from an older recording session
          return;
        }
        if (isProcessingTurnRef.current) {
          return;
        }
        isProcessingTurnRef.current = true;
        const transition = sm.transition('TRANSCRIPTION_RECEIVED');
        if (transition.success) {
          handleProcessInput(transcriptText);
        } else {
          isProcessingTurnRef.current = false;
        }
      },
      onPartialTranscript: (partialText: string) => {
        setPartialTranscript(partialText);
      },
      onAudioLevel: (level: number, waveform: Uint8Array, isSpeaking: boolean) => {
        setAudioLevel(level);
        setWaveformData(waveform);
        setIsSpeakingDetected(isSpeaking);
      },
      onSpeakingStart: () => {
        if (sm.getState() === 'processing') {
          sm.transition('SPEAK_START');
        }
      },
      onSpeakingEnd: () => {
        isProcessingTurnRef.current = false;
        if (sm.getState() === 'speaking' || sm.getState() === 'processing') {
          sm.transition('SPEAK_END');
        }
      },
      onError: (msg: string, isPermDenied: boolean) => {
        setPartialTranscript(null);
        isProcessingTurnRef.current = false;
        if (isPermDenied) {
          setMicPermission('denied');
        }
        sm.transition('FAIL', msg);
      },
    });
  }, [handleProcessInput]);

  // Public Methods
  const startListening = useCallback((): boolean => {
    const sm = stateMachineRef.current;
    const vc = voiceControllerRef.current;

    if (!sm.can('START_LISTENING')) {
      console.warn(`Cannot start listening while agent is in state: ${sm.getState()}`);
      return false;
    }

    // Cancel any active audio playback
    playbackAbortRef.current?.abort();
    vc.stopSpeaking();
    setPlaybackState('IDLE');
    setCurrentSpeakingMsgId(null);
    setCurrentSpeakingSentenceIndex(null);

    const newUtteranceId = `utt-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    activeUtteranceIdRef.current = newUtteranceId;
    isProcessingTurnRef.current = false;

    const res = sm.transition('START_LISTENING');
    if (!res.success) return false;

    // Route 1: Gnani Prisma v3.0 WebSocket Streaming
    if (sttProvider === 'gnani_prisma_v3' || sttProvider === 'gnani') {
      if (!gnaniConfigured) {
        setSTTRuntimeStatus('gnani_blocked_fallback');
        setSTTStatusMessage(
          'GNANI AI STT unavailable — API credentials required. Listening via Browser Native fallback.'
        );
        const started = vc.startListening(newUtteranceId);
        if (!started) sm.transition('FAIL', 'Failed to activate microphone input.');
        return true;
      }

      setSTTRuntimeStatus('gnani_prisma_v3_live');
      setSTTStatusMessage('GNANI AI STT: Live streaming (Prisma v3.0, indic-auto)...');

      vc.startGnaniStreaming({
        utteranceId: newUtteranceId,
        onError: (err, isAuth) => {
          if (isAuth) {
            setSTTRuntimeStatus('gnani_blocked_fallback');
            setSTTStatusMessage(
              'GNANI AI STT: Credentials rejected/missing. Switched to Browser Native.'
            );
            vc.startListening(newUtteranceId);
          } else {
            setSTTRuntimeStatus('error');
            setSTTStatusMessage(`GNANI AI STT error: ${err}`);
            sm.transition('FAIL', err);
          }
        },
      }).then((started) => {
        if (!started) {
          setSTTRuntimeStatus('gnani_blocked_fallback');
          setSTTStatusMessage('GNANI AI streaming connection failed. Using Browser Native fallback.');
          vc.startListening(newUtteranceId);
        }
      });
      return true;
    }

    // Route 2: Browser Native Web Speech API
    setSTTRuntimeStatus('browser_native');
    setSTTStatusMessage('Listening via Browser Native SpeechRecognition');
    const started = vc.startListening(newUtteranceId);
    if (!started) sm.transition('FAIL', 'Failed to activate microphone input.');

    return true;
  }, [gnaniConfigured, handleProcessInput, sttProvider]);

  const finishListening = useCallback(() => {
    const sm = stateMachineRef.current;
    if (sm.can('FINALIZE_START')) {
      sm.transition('FINALIZE_START');
    }
    voiceControllerRef.current.finishListening();
  }, []);

  const stopOrCancel = useCallback(() => {
    isProcessingTurnRef.current = false;
    playbackAbortRef.current?.abort();
    voiceControllerRef.current.cancelAll();
    stateMachineRef.current.cancel();
    setGyaniAudioStatus('IDLE');
    setPlaybackState('IDLE');
    setCurrentSpeakingMsgId(null);
    setCurrentSpeakingSentenceIndex(null);
    setPartialTranscript(null);
  }, []);

  const submitText = useCallback(
    (input: string): boolean => {
      const sm = stateMachineRef.current;
      const trimmed = input.trim();
      if (!trimmed) return false;

      playbackAbortRef.current?.abort();
      voiceControllerRef.current.stopSpeaking();
      setPlaybackState('IDLE');

      const canProcess = sm.can('TEXT_SUBMITTED');
      if (!canProcess) {
        if (sm.getState() === 'speaking') {
          sm.cancel();
        } else {
          return false;
        }
      }

      const res = sm.transition('TEXT_SUBMITTED');
      if (!res.success) return false;

      handleProcessInput(trimmed);
      return true;
    },
    [handleProcessInput]
  );

  const repeatLastResponse = useCallback(() => {
    submitText('repeat');
  }, [submitText]);

  const clearTranscript = useCallback(() => {
    playbackAbortRef.current?.abort();
    voiceControllerRef.current.stopSpeaking();
    setPlaybackState('IDLE');
    setTranscript([]);
    setRevealedSentenceCount({});
    conversationEngineRef.current.clearHistory();
    // Clear backend conversational memory and greeting history
    fetch('/api/chat/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionIdRef.current }),
    }).catch(() => {});
  }, []);

  const setLanguage = useCallback((newLang: string) => {
    setLanguageState(newLang);
    voiceControllerRef.current.setLanguage(newLang);
  }, []);

  const vocalizeWithBrowserFallback = useCallback(() => {
    const lastAgentMsg = transcript.slice().reverse().find((m) => m.role === 'agent');
    if (lastAgentMsg && lastAgentMsg.text) {
      setTTSRuntimeStatus('BROWSER_TTS_ACTIVE');
      setTTSStatusMessage('Vocalizing via Browser Native SpeechSynthesis (User Fallback Activated)');
      const sm = stateMachineRef.current;
      if (sm.can('SPEAK_START')) sm.transition('SPEAK_START');
      voiceControllerRef.current.speak(lastAgentMsg.text, () => {
        if (sm.can('SPEAK_END')) sm.transition('SPEAK_END');
      });
    }
  }, [transcript]);

  const retryLastTTS = useCallback(async () => {
    const lastAgentMsg = transcript.slice().reverse().find((m) => m.role === 'agent');
    if (!lastAgentMsg || !lastAgentMsg.text) return;

    try {
      setGyaniAudioStatus('GNANI AUDIO GENERATING');
      setTTSStatusMessage('Retrying GNANI AI TTS synthesis...');
      const ttsRes = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: lastAgentMsg.text,
          language,
          voice_id: selectedVoice,
          speed: ttsSpeed,
        }),
      });
      const contentType = ttsRes.headers.get('content-type') || '';
      if (ttsRes.ok && contentType.startsWith('audio/')) {
        const audioBlob = await ttsRes.blob();
        if (audioBlob.size > 44) {
          setGyaniAudioStatus('GNANI AUDIO READY');
          setTTSRuntimeStatus('GNANI_TTS_LIVE');
          setTTSStatusMessage(`GNANI AI TTS: Live neural speech (Timbre v2.5, ${selectedVoice})`);
          const sm = stateMachineRef.current;
          if (sm.can('SPEAK_START')) sm.transition('SPEAK_START');
          voiceControllerRef.current.playAudioBlob(
            audioBlob,
            () => {
              setGyaniAudioStatus('IDLE');
              if (sm.can('SPEAK_END')) sm.transition('SPEAK_END');
            },
            () => {
              setGyaniAudioStatus('GNANI AUDIO FAILED');
              if (sm.can('SPEAK_END')) sm.transition('SPEAK_END');
            },
            () => {
              setGyaniAudioStatus('GNANI AUDIO PLAYING');
            }
          );
          return;
        }
      }
      setGyaniAudioStatus('GNANI AUDIO FAILED');
      let err = `HTTP ${ttsRes.status}`;
      try { err = (await ttsRes.json()).detail || err; } catch {}
      setTTSRuntimeStatus(ttsRes.status === 503 ? 'GNANI_TTS_BLOCKED' : 'GNANI_TTS_ERROR');
      setTTSStatusMessage(`GNANI AI TTS retry failed (${err}). Silent fallback halted.`);
    } catch (e: any) {
      setGyaniAudioStatus('GNANI AUDIO FAILED');
      setTTSRuntimeStatus('GNANI_TTS_ERROR');
      setTTSStatusMessage(`GNANI AI TTS network error: ${e?.message || e}`);
    }
  }, [language, selectedVoice, transcript, ttsSpeed]);

  const approvePumpAction = useCallback(
    async (actionId: string) => {
      try {
        const response = await fetch('/api/pump/approve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_id: actionId,
            session_id: sessionIdRef.current,
            language,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          // Update action state in transcript
          setTranscript((prev) =>
            prev.map((msg) =>
              msg.pendingAction && msg.pendingAction.action_id === actionId
                ? {
                    ...msg,
                    pendingAction: {
                      ...msg.pendingAction,
                      state: 'COMPLETED',
                    },
                  }
                : msg
            )
          );

          // Append confirmation agent message
          const confirmMsgId = `sys-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
          const sentenceList = data.sentences && data.sentences.length > 0 ? data.sentences : [data.reply];
          const confirmMsg: ChatMessage = {
            id: confirmMsgId,
            role: 'agent',
            text: data.reply,
            sentences: sentenceList,
            timestamp: new Date(),
            intent: 'farm_status',
            providerStatus: 'pump_controller',
          };
          setTranscript((prev) => [...prev, confirmMsg]);

          // Vocalize reply via GNANI AI TTS queue (or browser fallback)
          playbackAbortRef.current?.abort();
          const abortController = new AbortController();
          playbackAbortRef.current = abortController;
          playSentenceQueue(sentenceList, confirmMsgId, abortController.signal);
        }
      } catch (err) {
        console.error('Error approving pump action:', err);
      }
    },
    [language, playSentenceQueue]
  );

  const rejectPumpAction = useCallback(
    async (actionId: string) => {
      try {
        const response = await fetch('/api/pump/reject', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_id: actionId,
            session_id: sessionIdRef.current,
            language,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          // Update action state in transcript
          setTranscript((prev) =>
            prev.map((msg) =>
              msg.pendingAction && msg.pendingAction.action_id === actionId
                ? {
                    ...msg,
                    pendingAction: {
                      ...msg.pendingAction,
                      state: 'REJECTED',
                    },
                  }
                : msg
            )
          );

          // Append rejection agent message
          const cancelMsgId = `sys-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
          const sentenceList = data.sentences && data.sentences.length > 0 ? data.sentences : [data.reply];
          const cancelMsg: ChatMessage = {
            id: cancelMsgId,
            role: 'agent',
            text: data.reply,
            sentences: sentenceList,
            timestamp: new Date(),
            intent: 'farm_status',
            providerStatus: 'pump_controller',
          };
          setTranscript((prev) => [...prev, cancelMsg]);

          // Vocalize reply via GNANI AI TTS queue
          playbackAbortRef.current?.abort();
          const abortController = new AbortController();
          playbackAbortRef.current = abortController;
          playSentenceQueue(sentenceList, cancelMsgId, abortController.signal);
        }
      } catch (err) {
        console.error('Error rejecting pump action:', err);
      }
    },
    [language, playSentenceQueue]
  );

  return {
    state: agentState,
    transcript,
    lastError,
    lastAgentResponse: conversationEngineRef.current.getLastResponse(),
    capabilities,
    micPermission,
    language,
    sttProvider,
    sttRuntimeStatus,
    sttStatusMessage,
    ttsProvider,
    ttsRuntimeStatus,
    ttsStatusMessage,
    gyaniAudioStatus,
    gnaniConfigured,
    llmProvider,
    llmStatus,
    llmConfigured,
    availableAgents,
    activeZoneId,
    selectedVoice,
    ttsSpeed,
    // Phase 14 Audio & Visualizer State
    audioLevel,
    waveformData,
    isSpeakingDetected,
    partialTranscript,
    selectedDeviceId,
    setSelectedDeviceId,
    // Phase 14 Streaming Audio State
    currentSpeakingMsgId,
    currentSpeakingSentenceIndex,
    playbackState,
    revealedSentenceCount,
    replayMessage: useCallback(
      (msgId: string) => {
        const targetMsg = transcript.find((m) => m.id === msgId);
        if (!targetMsg || targetMsg.role !== 'agent') return;

        playbackAbortRef.current?.abort();
        const abortController = new AbortController();
        playbackAbortRef.current = abortController;

        const sentenceList =
          targetMsg.sentences && targetMsg.sentences.length > 0
            ? targetMsg.sentences
            : [targetMsg.text];

        setRevealedSentenceCount((prev) => ({ ...prev, [msgId]: sentenceList.length }));
        playSentenceQueue(sentenceList, msgId, abortController.signal);
      },
      [playSentenceQueue, transcript]
    ),
    setSelectedVoice: setSelectedVoiceState,
    setTTSSpeed: setTTSSpeedState,
    setSTTProvider,
    setActiveZoneId: setActiveZoneIdState,
    setLLMProvider,
    setTTSProvider,
    setLanguage,
    startListening,
    finishListening,
    stopOrCancel,
    submitText,
    repeatLastResponse,
    clearTranscript,
    vocalizeWithBrowserFallback,
    retryLastTTS,
    approvePumpAction,
    rejectPumpAction,
  };
}
