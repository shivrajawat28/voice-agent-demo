/**
 * VoiceController
 *
 * Coordinates Web Speech API (SpeechRecognition & SpeechSynthesis) and
 * real-time Gnani STT streaming (Prisma v3.0 WebSocket) with:
 * - Live Web Audio Analyser for real energy VU meter (RMS) & waveform visualization.
 * - Audio input device enumeration and selection.
 * - Real-time interim/partial transcript streaming.
 * - Strict safety guards, single active session enforcement, and memory cleanup.
 */

import { VoiceCapabilities, MicPermissionState } from '../types/voiceAgent';
import { getWebSocketUrl } from '../config/api';

interface IWindowWithSpeech extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

export interface VoiceControllerCallbacks {
  onListeningStart?: () => void;
  onListeningEnd?: () => void;
  onTranscriptionResult?: (text: string, utteranceId?: string) => void;
  onPartialTranscript?: (text: string) => void;
  onAudioLevel?: (level: number, waveform: Uint8Array, isSpeaking: boolean) => void;
  onSpeakingStart?: () => void;
  onSpeakingEnd?: () => void;
  onIdleTimeout?: (message: string) => void;
  onError?: (message: string, isPermissionDenied: boolean) => void;
  onVoicesLoaded?: (voices: SpeechSynthesisVoice[], selectedVoice: SpeechSynthesisVoice | null) => void;
}

export class VoiceController {
  private recognitionInstance: any = null;
  private isListeningActive: boolean = false;
  private isSpeakingActive: boolean = false;
  private isExplicitlyCancelled: boolean = false;
  private language: string = 'en-US';
  private callbacks: VoiceControllerCallbacks = {};

  private availableVoices: SpeechSynthesisVoice[] = [];
  private selectedVoice: SpeechSynthesisVoice | null = null;
  private voicesInitialized: boolean = false;

  private currentAudioElement: HTMLAudioElement | null = null;
  private currentAudioUrl: string | null = null;

  // Real-time Web Audio Analyser & Microphone state
  private audioContext: AudioContext | null = null;
  private analyserNode: AnalyserNode | null = null;
  private micStream: MediaStream | null = null;
  private animFrameId: number | null = null;
  private selectedDeviceId: string | null = null;

  // Real-time Gnani STT streaming fields
  private gnaniWebSocket: WebSocket | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private muteGainNode: GainNode | null = null;
  private preConnectionAudioQueue: ArrayBuffer[] = [];
  private isGnaniStreaming: boolean = false;

  // Phase 26 Speech Session & Utterance Tracking
  private currentUtteranceId: string | null = null;
  private provisionalTranscript: string = '';
  private authoritativeTranscript: string = '';
  private isFinalizingSession: boolean = false;
  private hasDispatchedFinal: boolean = false;
  private finalizeTimer: any = null;

  constructor(callbacks?: VoiceControllerCallbacks) {
    if (callbacks) {
      this.callbacks = callbacks;
    }
    this.initVoices();
  }

  public setCallbacks(callbacks: VoiceControllerCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  public setSelectedDeviceId(deviceId: string | null): void {
    this.selectedDeviceId = deviceId;
  }

  public getSelectedDeviceId(): string | null {
    return this.selectedDeviceId;
  }

  /**
   * Enumerate available physical audio input devices
   */
  public static async getAudioInputDevices(): Promise<MediaDeviceInfo[]> {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) {
      return [];
    }
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter((d) => d.kind === 'audioinput');
    } catch {
      return [];
    }
  }

  /**
   * Starts Web Audio AnalyserNode to feed real-time RMS audio levels and waveforms
   */
  private startAudioAnalyser(stream: MediaStream): void {
    try {
      this.stopAudioAnalyser();

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      const ctx = new AudioCtx();
      this.audioContext = ctx;

      if (!ctx.createAnalyser || !ctx.createMediaStreamSource) return;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      this.analyserNode = analyser;

      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateLevel = () => {
        if (!this.isListeningActive || !this.analyserNode) {
          return;
        }

        analyser.getByteTimeDomainData(dataArray);

        // Compute Root Mean Square (RMS) energy
        let sumSquares = 0;
        for (let i = 0; i < bufferLength; i++) {
          const norm = (dataArray[i] - 128) / 128;
          sumSquares += norm * norm;
        }
        const rms = Math.min(1.0, Math.sqrt(sumSquares / bufferLength) * 3.5);
        const isSpeaking = rms > 0.05;

        this.callbacks.onAudioLevel?.(rms, dataArray, isSpeaking);
        this.animFrameId = requestAnimationFrame(updateLevel);
      };

      this.animFrameId = requestAnimationFrame(updateLevel);
    } catch (e) {
      console.warn('VoiceController: Error starting audio analyser:', e);
    }
  }

  private stopAudioAnalyser(): void {
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.analyserNode) {
      try {
        this.analyserNode.disconnect();
      } catch {}
      this.analyserNode = null;
    }
    if (this.audioContext && !this.isGnaniStreaming) {
      try {
        this.audioContext.close();
      } catch {}
      this.audioContext = null;
    }
    this.callbacks.onAudioLevel?.(0, new Uint8Array(128).fill(128), false);
  }

  /**
   * Initializes speech synthesis voices and handles asynchronous voice availability via 'voiceschanged'
   */
  public initVoices(): void {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      return;
    }

    const load = () => {
      try {
        const voices = window.speechSynthesis.getVoices();
        if (voices && voices.length > 0) {
          this.availableVoices = voices;
          this.voicesInitialized = true;
          this.updateSelectedVoice();
          this.callbacks.onVoicesLoaded?.(this.availableVoices, this.selectedVoice);
        }
      } catch (e) {
        console.warn('VoiceController: Error accessing speechSynthesis voices:', e);
      }
    };

    load();

    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = () => {
        load();
      };
    }
  }

  /**
   * Selects the most natural, suitable installed voice for the target language.
   */
  public updateSelectedVoice(): SpeechSynthesisVoice | null {
    if (this.availableVoices.length === 0) {
      this.selectedVoice = null;
      return null;
    }

    const langLower = this.language.toLowerCase();

    if (langLower.startsWith('hi')) {
      const hindiVoice = this.availableVoices.find((v) => {
        const vLang = v.lang.toLowerCase();
        const vName = v.name.toLowerCase();
        return (
          vLang.startsWith('hi') ||
          vName.includes('hindi') ||
          vName.includes('हिन्दी') ||
          vName.includes('lekha') ||
          vName.includes('swara') ||
          vName.includes('neerja') ||
          vName.includes('madhur')
        );
      });

      if (hindiVoice) {
        this.selectedVoice = hindiVoice;
        return hindiVoice;
      }

      const indianEnglishVoice = this.availableVoices.find((v) => {
        const vLang = v.lang.toLowerCase();
        const vName = v.name.toLowerCase();
        return (
          vLang === 'en-in' ||
          vName.includes('india') ||
          vName.includes('veena') ||
          vName.includes('rishi')
        );
      });

      if (indianEnglishVoice) {
        this.selectedVoice = indianEnglishVoice;
        return indianEnglishVoice;
      }

      this.selectedVoice =
        this.availableVoices.find((v) => v.default) || this.availableVoices[0] || null;
      return this.selectedVoice;
    }

    if (langLower === 'en-in') {
      const inVoice = this.availableVoices.find(
        (v) => v.lang.toLowerCase() === 'en-in' || v.name.toLowerCase().includes('india')
      );
      if (inVoice) {
        this.selectedVoice = inVoice;
        return inVoice;
      }
    }

    const matchingVoice = this.availableVoices.find((v) =>
      v.lang.toLowerCase().startsWith(langLower)
    );
    this.selectedVoice =
      matchingVoice ||
      this.availableVoices.find((v) => v.default) ||
      this.availableVoices[0] ||
      null;

    return this.selectedVoice;
  }

  public static getCapabilities(): VoiceCapabilities {
    if (typeof window === 'undefined') {
      return {
        speechRecognitionSupported: false,
        speechSynthesisSupported: false,
        isWebKit: false,
      };
    }

    const win = window as IWindowWithSpeech;
    const hasRecognition = Boolean(win.SpeechRecognition || win.webkitSpeechRecognition);
    const hasSynthesis = typeof window.speechSynthesis !== 'undefined';
    const isWebKit = Boolean(!win.SpeechRecognition && win.webkitSpeechRecognition);

    let hasHindiVoice = false;
    let selectedVoiceName: string | undefined;

    if (hasSynthesis) {
      try {
        const voices = window.speechSynthesis.getVoices();
        hasHindiVoice = voices.some(
          (v) =>
            v.lang.toLowerCase().startsWith('hi') ||
            v.name.toLowerCase().includes('hindi') ||
            v.name.toLowerCase().includes('हिन्दी')
        );
      } catch {}
    }

    return {
      speechRecognitionSupported: hasRecognition,
      speechSynthesisSupported: hasSynthesis,
      isWebKit,
      hasHindiVoice,
      selectedVoiceName,
    };
  }

  public static async queryMicPermission(): Promise<MicPermissionState> {
    if (typeof navigator === 'undefined' || !navigator.permissions || !navigator.permissions.query) {
      return 'prompt';
    }
    try {
      const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      return result.state as MicPermissionState;
    } catch {
      return 'prompt';
    }
  }

  public setLanguage(lang: string): void {
    this.language = lang;
    if (this.recognitionInstance) {
      this.recognitionInstance.lang = lang;
    }
    this.updateSelectedVoice();
  }

  public getLanguage(): string {
    return this.language;
  }

  public getSelectedVoice(): SpeechSynthesisVoice | null {
    return this.selectedVoice;
  }

  public getAvailableVoices(): SpeechSynthesisVoice[] {
    return this.availableVoices;
  }

  public isVoicesLoaded(): boolean {
    return this.voicesInitialized;
  }

  /**
   * Initiates Speech Recognition synchronously, with background audio analyser & partial results
   */
  public startListening(utteranceId?: string): boolean {
    const caps = VoiceController.getCapabilities();
    if (!caps.speechRecognitionSupported) {
      this.callbacks.onError?.(
        'Speech recognition is not supported in this browser. Please use the text input below.',
        false
      );
      return false;
    }

    if (this.isListeningActive) {
      console.warn('VoiceController: Already listening. Ignoring redundant startListening request.');
      return false;
    }

    this.stopSpeaking();
    this.isExplicitlyCancelled = false;
    this.isFinalizingSession = false;
    this.hasDispatchedFinal = false;
    this.provisionalTranscript = '';
    this.authoritativeTranscript = '';
    const activeUtterance = utteranceId || `utt-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    this.currentUtteranceId = activeUtterance;
    if (this.finalizeTimer) {
      clearTimeout(this.finalizeTimer);
      this.finalizeTimer = null;
    }

    // Optional background mic stream for real-time waveform & RMS energy meter
    if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
      const audioConstraints: MediaStreamConstraints = {
        audio: this.selectedDeviceId
          ? { deviceId: { exact: this.selectedDeviceId } }
          : { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      };
      navigator.mediaDevices
        .getUserMedia(audioConstraints)
        .then((stream) => {
          if (this.isListeningActive) {
            this.micStream = stream;
            this.startAudioAnalyser(stream);
          } else {
            stream.getTracks().forEach((t) => t.stop());
          }
        })
        .catch(() => {});
    }

    const win = window as IWindowWithSpeech;
    const SpeechRecClass = win.SpeechRecognition || win.webkitSpeechRecognition;

    try {
      const recognition = new SpeechRecClass();
      recognition.lang = this.language;
      // Phase 26: continuous = true ensures natural pauses mid-sentence do not abruptly terminate capture
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        this.isListeningActive = true;
        this.callbacks.onListeningStart?.();
      };

      recognition.onresult = (event: any) => {
        if (this.currentUtteranceId !== activeUtterance) return;
        let interimText = '';
        let finalText = '';

        for (let i = 0; i < event.results.length; i++) {
          const res = event.results[i];
          if (res.isFinal) {
            finalText += (res[0]?.transcript || '') + ' ';
          } else {
            interimText += (res[0]?.transcript || '') + ' ';
          }
        }

        const combined = (finalText + interimText).trim();
        if (combined) {
          this.provisionalTranscript = combined;
          this.callbacks.onPartialTranscript?.(combined);
        }

        if (finalText.trim()) {
          this.authoritativeTranscript = finalText.trim();
        }
      };

      recognition.onerror = (event: any) => {
        const error = event.error;
        this.isListeningActive = false;
        this.stopAudioAnalyser();

        if (error === 'aborted' || this.isExplicitlyCancelled) {
          return;
        }

        let userFriendlyMsg = `Speech recognition error (${error}).`;
        let isPermDenied = false;

        if (error === 'not-allowed' || error === 'service-not-allowed') {
          userFriendlyMsg = 'Microphone permission was denied. Please allow microphone access in your browser settings or use text input.';
          isPermDenied = true;
        } else if (error === 'no-speech') {
          userFriendlyMsg = 'No speech detected. Please try speaking again or click Stop.';
        } else if (error === 'network') {
          userFriendlyMsg = 'Speech recognition network error. The browser speech service was unreachable.';
        }

        this.callbacks.onError?.(userFriendlyMsg, isPermDenied);
      };

      recognition.onend = () => {
        this.isListeningActive = false;
        this.stopAudioAnalyser();

        if (this.currentUtteranceId === activeUtterance && !this.isExplicitlyCancelled && !this.hasDispatchedFinal) {
          const textToDispatch = this.authoritativeTranscript || this.provisionalTranscript;
          if (textToDispatch) {
            this.dispatchFinalTranscript(textToDispatch, activeUtterance);
          }
        }

        this.callbacks.onListeningEnd?.();
      };

      this.recognitionInstance = recognition;
      recognition.start();
      return true;
    } catch (err: any) {
      this.isListeningActive = false;
      this.stopAudioAnalyser();
      const msg = err?.message || 'Failed to initialize speech recognition.';
      this.callbacks.onError?.(msg, false);
      return false;
    }
  }

  public static resampleAudio(
    inputSamples: Float32Array,
    sourceSampleRate: number,
    targetSampleRate: number = 16000
  ): Float32Array {
    if (sourceSampleRate === targetSampleRate) {
      return inputSamples;
    }
    const ratio = sourceSampleRate / targetSampleRate;
    const targetLength = Math.round(inputSamples.length / ratio);
    const result = new Float32Array(targetLength);
    for (let i = 0; i < targetLength; i++) {
      const sourceIndex = i * ratio;
      const lower = Math.floor(sourceIndex);
      const upper = Math.min(lower + 1, inputSamples.length - 1);
      const weight = sourceIndex - lower;
      result[i] = inputSamples[lower] * (1 - weight) + inputSamples[upper] * weight;
    }
    return result;
  }

  public static floatTo16BitPCM(floatSamples: Float32Array): ArrayBuffer {
    const buffer = new ArrayBuffer(floatSamples.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < floatSamples.length; i++) {
      const s = Math.max(-1, Math.min(1, floatSamples[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  }

  public async startGnaniStreaming(options: {
    wsUrl?: string;
    utteranceId?: string;
    onTranscript?: (text: string, isFinal: boolean, detectedLang?: string) => void;
    onError?: (error: string, isAuthError: boolean) => void;
    onConnected?: () => void;
  } = {}): Promise<boolean> {
    if (this.isListeningActive || this.isGnaniStreaming) {
      console.info('VoiceController: Resetting active listening session before starting new one.');
      this.cleanupGnaniStreaming();
      this.stopListening();
    }

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      options.onError?.('Microphone access is not supported in this browser.', false);
      return false;
    }

    this.stopSpeaking();
    this.isExplicitlyCancelled = false;
    this.isFinalizingSession = false;
    this.hasDispatchedFinal = false;
    this.provisionalTranscript = '';
    this.authoritativeTranscript = '';
    this.preConnectionAudioQueue = [];
    const activeUtterance = options.utteranceId || `utt-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    this.currentUtteranceId = activeUtterance;
    if (this.finalizeTimer) {
      clearTimeout(this.finalizeTimer);
      this.finalizeTimer = null;
    }

    try {
      const audioConstraints: MediaStreamConstraints = {
        audio: this.selectedDeviceId
          ? { deviceId: { exact: this.selectedDeviceId } }
          : { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      };
      const stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
      this.micStream = stream;

      const targetWsUrl = options.wsUrl || getWebSocketUrl('/api/ws/stt');

      const ws = new WebSocket(targetWsUrl);
      this.gnaniWebSocket = ws;
      this.isListeningActive = true;
      this.isGnaniStreaming = true;
      this.callbacks.onListeningStart?.();

      let pcmSampleBuffer: number[] = [];

      ws.onopen = () => {
        if (this.preConnectionAudioQueue.length > 0) {
          console.info(
            `[VoiceController:${activeUtterance}] STT WebSocket connected. Flushing ${this.preConnectionAudioQueue.length} pre-buffered frames.`
          );
          while (this.preConnectionAudioQueue.length > 0) {
            const queued = this.preConnectionAudioQueue.shift()!;
            ws.send(queued);
          }
        }
        options.onConnected?.();
      };

      ws.onmessage = (event) => {
        if (this.currentUtteranceId !== activeUtterance) {
          // Stale message from previous session!
          return;
        }
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'final_transcript') {
            // Reconcile with provisional transcript if final is only a truncated suffix
            let finalText = (data.text || '').trim();
            if (this.provisionalTranscript && this.provisionalTranscript.length > finalText.length) {
              if (
                this.provisionalTranscript.endsWith(finalText) ||
                this.provisionalTranscript.includes(finalText) ||
                finalText.split(/\s+/).length <= 2
              ) {
                finalText = this.provisionalTranscript;
              }
            }
            options.onTranscript?.(finalText, true, data.detected_language);
            this.authoritativeTranscript = finalText;
            this.provisionalTranscript = finalText;
            if (this.isFinalizingSession) {
              this.dispatchFinalTranscript(finalText, activeUtterance);
              this.cleanupGnaniStreaming();
              this.callbacks.onListeningEnd?.();
            } else {
              this.callbacks.onPartialTranscript?.(finalText);
            }
          } else if (data.type === 'transcript' || data.type === 'interim_transcript') {
            options.onTranscript?.(data.text, false, data.detected_language);
            this.provisionalTranscript = data.text;
            this.callbacks.onPartialTranscript?.(data.text);
          } else if (data.type === 'idle_timeout') {
            console.info(`[VoiceController:${activeUtterance}] STT idle session closed:`, data.message);
            this.cleanupGnaniStreaming();
            this.callbacks.onIdleTimeout?.(data.message || 'No speech detected. Tap the microphone to try again.');
            this.callbacks.onListeningEnd?.();
          } else if (data.type === 'error') {
            const isAuth = data.code === 'AUTH_REQUIRED' || data.code === 401 || data.code === 403;
            options.onError?.(data.message, isAuth);
            this.callbacks.onError?.(data.message, false);
          }
        } catch (e) {
          console.warn('VoiceController STT ws message error:', e);
        }
      };

      ws.onerror = (err) => {
        if (this.currentUtteranceId === activeUtterance) {
          console.warn('VoiceController STT WebSocket error:', err);
          options.onError?.('Gnani STT WebSocket error.', false);
        }
      };

      ws.onclose = () => {
        if (this.currentUtteranceId === activeUtterance) {
          if (this.isFinalizingSession && !this.hasDispatchedFinal) {
            const fallbackText = this.authoritativeTranscript || this.provisionalTranscript;
            if (fallbackText) {
              this.dispatchFinalTranscript(fallbackText, activeUtterance);
            }
          }
          this.cleanupGnaniStreaming();
          this.callbacks.onListeningEnd?.();
        }
      };

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx();
      this.audioContext = audioCtx;

      if (audioCtx.state === 'suspended') {
        try {
          await audioCtx.resume();
        } catch (e) {
          console.warn('VoiceController: Failed to resume AudioContext:', e);
        }
      }

      const sourceNode = audioCtx.createMediaStreamSource(stream);
      this.sourceNode = sourceNode;

      // Attach visualizer analyser if supported
      if (audioCtx.createAnalyser) {
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        this.analyserNode = analyser;
        sourceNode.connect(analyser);

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const updateLevel = () => {
          if (!this.isListeningActive || !this.analyserNode) return;
          analyser.getByteTimeDomainData(dataArray);
          let sumSquares = 0;
          for (let i = 0; i < bufferLength; i++) {
            const norm = (dataArray[i] - 128) / 128;
            sumSquares += norm * norm;
          }
          const rms = Math.min(1.0, Math.sqrt(sumSquares / bufferLength) * 3.5);
          const isSpeaking = rms > 0.04;
          this.callbacks.onAudioLevel?.(rms, dataArray, isSpeaking);
          this.animFrameId = requestAnimationFrame(updateLevel);
        };
        this.animFrameId = requestAnimationFrame(updateLevel);
      }

      // ScriptProcessor for PCM streaming to Gnani proxy
      if (audioCtx.createScriptProcessor) {
        const processor = audioCtx.createScriptProcessor(2048, 1, 1);
        this.scriptProcessor = processor;

        processor.onaudioprocess = (e) => {
          if (!this.isGnaniStreaming) return;

          const inputChannelData = e.inputBuffer.getChannelData(0);
          const resampled = VoiceController.resampleAudio(
            inputChannelData,
            audioCtx.sampleRate,
            16000
          );

          for (let i = 0; i < resampled.length; i++) {
            pcmSampleBuffer.push(resampled[i]);
          }

          while (pcmSampleBuffer.length >= 512) {
            const frameSamples = new Float32Array(pcmSampleBuffer.slice(0, 512));
            pcmSampleBuffer = pcmSampleBuffer.slice(512);
            const pcmBuffer = VoiceController.floatTo16BitPCM(frameSamples);

            if (this.gnaniWebSocket && this.gnaniWebSocket.readyState === WebSocket.OPEN) {
              while (this.preConnectionAudioQueue.length > 0) {
                const queued = this.preConnectionAudioQueue.shift()!;
                this.gnaniWebSocket.send(queued);
              }
              this.gnaniWebSocket.send(pcmBuffer);
            } else if (this.gnaniWebSocket && this.gnaniWebSocket.readyState === WebSocket.CONNECTING) {
              if (this.preConnectionAudioQueue.length < 150) {
                this.preConnectionAudioQueue.push(pcmBuffer);
              }
            }
          }
        };

        // Route through a muted gain node to prevent speaker feedback while keeping processor alive
        const muteGain = audioCtx.createGain ? audioCtx.createGain() : null;
        this.muteGainNode = muteGain;
        if (muteGain) {
          muteGain.gain.value = 0;
          sourceNode.connect(processor);
          processor.connect(muteGain);
          muteGain.connect(audioCtx.destination);
        } else {
          sourceNode.connect(processor);
          processor.connect(audioCtx.destination);
        }
      }

      return true;
    } catch (err: any) {
      console.warn('VoiceController startGnaniStreaming failed:', err);
      this.cleanupGnaniStreaming();
      let errorMsg = 'Failed to access microphone or connect to Gnani STT.';
      if (err?.name === 'NotAllowedError') {
        errorMsg = 'Microphone permission was denied. Please allow microphone access in site settings.';
      } else if (err?.name === 'NotFoundError') {
        errorMsg = 'No microphone device was found on this system.';
      } else if (err?.name === 'NotReadableError') {
        errorMsg = 'Microphone is currently busy or unreadable by the browser.';
      } else if (err?.name === 'OverconstrainedError') {
        errorMsg = 'Selected microphone constraints could not be satisfied.';
      }
      this.callbacks.onError?.(errorMsg, err?.name === 'NotAllowedError');
      options.onError?.(errorMsg, false);
      return false;
    }
  }

  public stopGnaniStreaming(): void {
    // 1. Immediately stop capturing new audio from microphone
    if (this.micStream) {
      try {
        this.micStream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      } catch {}
      this.micStream = null;
    }

    if (this.scriptProcessor) {
      try {
        this.scriptProcessor.disconnect();
      } catch {}
      this.scriptProcessor = null;
    }

    this.stopAudioAnalyser();

    // 2. Send stop action to upstream proxy so it flushes audio & sends VAD silence to Gnani
    if (this.gnaniWebSocket && this.gnaniWebSocket.readyState === WebSocket.OPEN) {
      try {
        this.gnaniWebSocket.send(JSON.stringify({ action: 'stop' }));
      } catch {}
    }

    const targetUtterance = this.currentUtteranceId;
    if (this.finalizeTimer) clearTimeout(this.finalizeTimer);
    // 3. Bounded finalization timeout: if server does not respond within 1.5 seconds, dispatch provisional transcript
    this.finalizeTimer = setTimeout(() => {
      if (this.currentUtteranceId === targetUtterance && !this.hasDispatchedFinal) {
        const fallback = this.authoritativeTranscript || this.provisionalTranscript;
        if (fallback) {
          this.dispatchFinalTranscript(fallback, targetUtterance);
        }
        this.cleanupGnaniStreaming();
        this.callbacks.onListeningEnd?.();
      }
    }, 1500);
  }

  public cancelGnaniStreaming(): void {
    if (this.finalizeTimer) {
      clearTimeout(this.finalizeTimer);
      this.finalizeTimer = null;
    }
    if (this.gnaniWebSocket && this.gnaniWebSocket.readyState === WebSocket.OPEN) {
      try {
        this.gnaniWebSocket.send(JSON.stringify({ action: 'cancel' }));
      } catch {}
    }
    this.cleanupGnaniStreaming();
  }

  public cleanupGnaniStreaming(): void {
    this.isGnaniStreaming = false;
    this.isListeningActive = false;
    this.stopAudioAnalyser();

    if (this.scriptProcessor) {
      try {
        this.scriptProcessor.disconnect();
      } catch {}
      this.scriptProcessor = null;
    }

    if (this.muteGainNode) {
      try {
        this.muteGainNode.disconnect();
      } catch {}
      this.muteGainNode = null;
    }

    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {}
      this.sourceNode = null;
    }

    if (this.audioContext) {
      try {
        this.audioContext.close();
      } catch {}
      this.audioContext = null;
    }

    if (this.micStream) {
      try {
        this.micStream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      } catch {}
      this.micStream = null;
    }

    if (this.gnaniWebSocket) {
      try {
        this.gnaniWebSocket.onopen = null;
        this.gnaniWebSocket.onmessage = null;
        this.gnaniWebSocket.onerror = null;
        this.gnaniWebSocket.onclose = null;
        this.gnaniWebSocket.close();
      } catch {}
      this.gnaniWebSocket = null;
    }

    this.preConnectionAudioQueue = [];
  }

  /**
   * Gracefully finishes listening: stops mic capture and waits for STT transcription.
   */
  public finishListening(): void {
    this.isExplicitlyCancelled = false;
    this.isFinalizingSession = true;

    // Immediately stop microphone capture so background audio is cut off
    if (this.micStream) {
      try {
        this.micStream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      } catch {}
      this.micStream = null;
    }
    this.stopAudioAnalyser();

    const targetUtterance = this.currentUtteranceId;

    if (this.isGnaniStreaming) {
      this.stopGnaniStreaming();
    } else if (this.recognitionInstance) {
      try {
        this.recognitionInstance.stop();
      } catch {}

      const fallback = this.authoritativeTranscript || this.provisionalTranscript;
      if (fallback) {
        this.dispatchFinalTranscript(fallback, targetUtterance);
        this.callbacks.onListeningEnd?.();
      } else {
        if (this.finalizeTimer) clearTimeout(this.finalizeTimer);
        this.finalizeTimer = setTimeout(() => {
          if (this.currentUtteranceId === targetUtterance && !this.hasDispatchedFinal) {
            const delayedFallback = this.authoritativeTranscript || this.provisionalTranscript;
            if (delayedFallback) {
              this.dispatchFinalTranscript(delayedFallback, targetUtterance);
            }
            this.callbacks.onListeningEnd?.();
          }
        }, 1000);
      }
    }
  }

  public dispatchFinalTranscript(text: string, utteranceId?: string | null): void {
    if (this.hasDispatchedFinal || this.isExplicitlyCancelled) {
      return;
    }
    if (utteranceId && this.currentUtteranceId && utteranceId !== this.currentUtteranceId) {
      return;
    }
    const clean = text.trim();
    if (!clean) {
      return;
    }
    this.hasDispatchedFinal = true;
    if (this.finalizeTimer) {
      clearTimeout(this.finalizeTimer);
      this.finalizeTimer = null;
    }
    this.callbacks.onTranscriptionResult?.(clean, utteranceId || this.currentUtteranceId || undefined);
  }

  public stopListening(): void {
    this.isExplicitlyCancelled = true;
    this.isFinalizingSession = false;
    this.currentUtteranceId = null;
    this.provisionalTranscript = '';
    this.authoritativeTranscript = '';
    if (this.finalizeTimer) {
      clearTimeout(this.finalizeTimer);
      this.finalizeTimer = null;
    }
    if (this.isGnaniStreaming) {
      this.cancelGnaniStreaming();
    }
    if (this.recognitionInstance) {
      try {
        this.recognitionInstance.abort();
      } catch {}
      this.recognitionInstance = null;
    }
    if (this.micStream) {
      try {
        this.micStream.getTracks().forEach((t) => t.stop());
      } catch {}
      this.micStream = null;
    }
    this.stopAudioAnalyser();
    this.isListeningActive = false;
  }

  /**
   * Preloads an audio blob for seamless gapless queue playback
   */
  public createPreloadedAudio(blob: Blob): { audio: HTMLAudioElement; url: string } {
    const url = URL.createObjectURL(blob);
    const audio = new Audio();
    audio.preload = 'auto';
    audio.src = url;
    try {
      audio.load();
    } catch (e) {}
    return { audio, url };
  }

  public playPreloadedAudio(
    audioData: { audio: HTMLAudioElement; url: string },
    onEndCallback?: () => void,
    onErrorCallback?: (err: any) => void,
    onStartCallback?: () => void,
    options?: { isQueueItem?: boolean; isFinal?: boolean }
  ): boolean {
    const isQueueItem = options?.isQueueItem ?? false;
    const isFinal = options?.isFinal ?? true;

    if (!isQueueItem) {
      this.stopSpeaking();
    } else {
      // For queue items, gracefully release any prior audio element without cancelling speaking state
      if (this.currentAudioElement && this.currentAudioElement !== audioData.audio) {
        try {
          this.currentAudioElement.pause();
        } catch (e) {}
        this.cleanupAudio();
      }
    }
    this.isExplicitlyCancelled = false;

    const { audio, url } = audioData;
    this.currentAudioUrl = url;
    this.currentAudioElement = audio;

    audio.onplay = () => {
      this.isSpeakingActive = true;
      this.callbacks.onSpeakingStart?.();
      onStartCallback?.();
    };

    audio.onended = () => {
      this.cleanupAudio();
      if (isFinal) {
        this.isSpeakingActive = false;
        this.callbacks.onSpeakingEnd?.();
      }
      onEndCallback?.();
    };

    audio.onerror = (e) => {
      this.cleanupAudio();
      if (isFinal) {
        this.isSpeakingActive = false;
        this.callbacks.onSpeakingEnd?.();
      }
      if (!this.isExplicitlyCancelled) {
        this.callbacks.onError?.('Audio playback failed.', false);
        onErrorCallback?.(e);
      }
      onEndCallback?.();
    };

    try {
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          this.cleanupAudio();
          if (isFinal) {
            this.isSpeakingActive = false;
            this.callbacks.onSpeakingEnd?.();
          }
          if (!this.isExplicitlyCancelled) {
            console.warn('Audio playback error / autoplay rejection:', err);
            this.callbacks.onError?.('Audio playback failed or was blocked by autoplay.', false);
            onErrorCallback?.(err);
          }
          onEndCallback?.();
        });
      }
      return true;
    } catch (err) {
      this.cleanupAudio();
      if (isFinal) {
        this.isSpeakingActive = false;
        this.callbacks.onSpeakingEnd?.();
      }
      onErrorCallback?.(err);
      onEndCallback?.();
      return false;
    }
  }

  public speak(
    text: string,
    onEndCallback?: () => void
  ): boolean {
    const caps = VoiceController.getCapabilities();
    if (!caps.speechSynthesisSupported) {
      console.warn('SpeechSynthesis is not supported in this browser.');
      onEndCallback?.();
      return false;
    }

    this.stopSpeaking();
    this.isExplicitlyCancelled = false;

    const cleanText = text.replace(/\[.*?\]/g, '').trim();
    if (!cleanText) {
      onEndCallback?.();
      return false;
    }

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);

      if (!this.selectedVoice && this.availableVoices.length > 0) {
        this.updateSelectedVoice();
      }

      if (this.selectedVoice) {
        utterance.voice = this.selectedVoice;
        utterance.lang = this.selectedVoice.lang || this.language;
      } else {
        utterance.lang = this.language;
      }

      utterance.rate = this.language.startsWith('hi') ? 0.95 : 1.0;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        this.isSpeakingActive = true;
        this.callbacks.onSpeakingStart?.();
      };

      utterance.onend = () => {
        this.isSpeakingActive = false;
        this.callbacks.onSpeakingEnd?.();
        onEndCallback?.();
      };

      utterance.onerror = (e: any) => {
        const errorCode = e.error || 'unknown';
        this.isSpeakingActive = false;

        if (errorCode === 'canceled' || errorCode === 'interrupted' || this.isExplicitlyCancelled) {
          this.callbacks.onSpeakingEnd?.();
          onEndCallback?.();
          return;
        }

        let userFriendlyMsg = `Speech synthesis failed (${errorCode}).`;
        if (errorCode === 'language-unavailable' || errorCode === 'voice-unavailable') {
          userFriendlyMsg = `The selected voice or language (${this.language}) is not supported by your browser's TTS engine. Text fallback is active.`;
        } else if (errorCode === 'audio-busy') {
          userFriendlyMsg = 'Audio output device is currently busy. Please retry in a moment.';
        } else if (errorCode === 'not-allowed') {
          userFriendlyMsg = 'Audio playback was blocked by browser autoplay policy. Please click to interact.';
        }

        this.callbacks.onError?.(userFriendlyMsg, false);
        this.callbacks.onSpeakingEnd?.();
        onEndCallback?.();
      };

      window.speechSynthesis.speak(utterance);
      return true;
    } catch (err: any) {
      this.isSpeakingActive = false;
      this.callbacks.onSpeakingEnd?.();
      onEndCallback?.();
      return false;
    }
  }

  public playAudioBlob(
    blob: Blob,
    onEndCallback?: () => void,
    onErrorCallback?: (err: any) => void,
    onStartCallback?: () => void,
    options?: { isQueueItem?: boolean; isFinal?: boolean }
  ): boolean {
    if (typeof window === 'undefined' || typeof Audio === 'undefined') {
      onErrorCallback?.(new Error('Audio API not available in this environment'));
      onEndCallback?.();
      return false;
    }

    const isQueueItem = options?.isQueueItem ?? false;
    const isFinal = options?.isFinal ?? true;

    if (!isQueueItem) {
      this.stopSpeaking();
    } else {
      if (this.currentAudioElement) {
        try {
          this.currentAudioElement.pause();
        } catch (e) {}
        this.cleanupAudio();
      }
    }
    this.isExplicitlyCancelled = false;

    try {
      const url = URL.createObjectURL(blob);
      this.currentAudioUrl = url;
      const audio = new Audio(url);
      this.currentAudioElement = audio;

      audio.onplay = () => {
        this.isSpeakingActive = true;
        this.callbacks.onSpeakingStart?.();
        onStartCallback?.();
      };

      audio.onended = () => {
        this.cleanupAudio();
        if (isFinal) {
          this.isSpeakingActive = false;
          this.callbacks.onSpeakingEnd?.();
        }
        onEndCallback?.();
      };

      audio.onerror = (e) => {
        this.cleanupAudio();
        if (isFinal) {
          this.isSpeakingActive = false;
          this.callbacks.onSpeakingEnd?.();
        }
        if (!this.isExplicitlyCancelled) {
          this.callbacks.onError?.('Audio playback failed.', false);
          onErrorCallback?.(e);
        }
        onEndCallback?.();
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          this.cleanupAudio();
          if (isFinal) {
            this.isSpeakingActive = false;
            this.callbacks.onSpeakingEnd?.();
          }
          if (!this.isExplicitlyCancelled) {
            console.warn('Audio playback error / autoplay rejection:', err);
            this.callbacks.onError?.('Audio playback failed or was blocked by autoplay.', false);
            onErrorCallback?.(err);
          }
          onEndCallback?.();
        });
      }
      return true;
    } catch (err) {
      this.cleanupAudio();
      if (isFinal) {
        this.isSpeakingActive = false;
        this.callbacks.onSpeakingEnd?.();
      }
      onErrorCallback?.(err);
      onEndCallback?.();
      return false;
    }
  }

  private cleanupAudio(): void {
    if (this.currentAudioUrl) {
      try {
        URL.revokeObjectURL(this.currentAudioUrl);
      } catch (e) {}
      this.currentAudioUrl = null;
    }
    this.currentAudioElement = null;
  }

  public stopSpeaking(): void {
    this.isExplicitlyCancelled = true;

    if (this.currentAudioElement) {
      try {
        this.currentAudioElement.pause();
        this.currentAudioElement.currentTime = 0;
      } catch (e) {}
      this.cleanupAudio();
    }

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {}
    }
    this.isSpeakingActive = false;
  }

  public cancelAll(): void {
    this.isExplicitlyCancelled = true;
    this.stopListening();
    this.stopSpeaking();
  }

  public isListening(): boolean {
    return this.isListeningActive;
  }

  public isSpeaking(): boolean {
    return this.isSpeakingActive;
  }
}
