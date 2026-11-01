/**
 * Frontend Test Suite for Phase 11: Gnani AI Speech Integration
 * Tests:
 * - Audio resampling from 48 kHz / 44.1 kHz to 16 kHz
 * - Float32Array to 16-bit PCM Little Endian conversion
 * - VoiceController Gnani streaming lifecycle & PCM frame chunking
 * - STT & TTS provider fallback behavior and status labeling
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceController } from '../services/VoiceController';

describe('VoiceController Gnani Speech & Audio Processing', () => {
  describe('Audio Resampling', () => {
    it('returns the same array when source and target sample rates match', () => {
      const input = new Float32Array([0.0, 0.5, -0.5, 1.0]);
      const resampled = VoiceController.resampleAudio(input, 16000, 16000);
      expect(resampled).toBe(input);
      expect(resampled.length).toBe(4);
    });

    it('downsamples from 48 kHz to 16 kHz (3:1 ratio) correctly', () => {
      // 48000 Hz to 16000 Hz is a 3:1 decimation ratio
      const input = new Float32Array(4800); // 0.1s at 48kHz
      for (let i = 0; i < input.length; i++) {
        input[i] = Math.sin((2 * Math.PI * 440 * i) / 48000);
      }
      const resampled = VoiceController.resampleAudio(input, 48000, 16000);
      expect(resampled.length).toBe(1600); // 0.1s at 16kHz
      // Peak amplitude preserved within bounds
      expect(Math.max(...resampled)).toBeLessThanOrEqual(1.0);
      expect(Math.min(...resampled)).toBeGreaterThanOrEqual(-1.0);
    });

    it('downsamples from 44.1 kHz to 16 kHz correctly', () => {
      const input = new Float32Array(4410); // 0.1s at 44.1kHz
      const resampled = VoiceController.resampleAudio(input, 44100, 16000);
      expect(resampled.length).toBe(1600);
    });
  });

  describe('16-bit PCM Little-Endian Conversion', () => {
    it('converts float audio range [-1.0, 1.0] to signed 16-bit integers', () => {
      const input = new Float32Array([0.0, 1.0, -1.0, 0.5, -0.5]);
      const buffer = VoiceController.floatTo16BitPCM(input);
      expect(buffer.byteLength).toBe(input.length * 2);

      const view = new DataView(buffer);
      expect(view.getInt16(0, true)).toBe(0); // 0.0 -> 0
      expect(view.getInt16(2, true)).toBe(32767); // 1.0 -> 32767
      expect(view.getInt16(4, true)).toBe(-32768); // -1.0 -> -32768
      expect(view.getInt16(6, true)).toBe(16383); // 0.5 * 32767 truncated
      expect(view.getInt16(8, true)).toBe(-16384); // -0.5 * 32768
    });

    it('clamps values exceeding 1.0 or below -1.0 to prevent overflow', () => {
      const input = new Float32Array([2.5, -3.0]);
      const buffer = VoiceController.floatTo16BitPCM(input);
      const view = new DataView(buffer);
      expect(view.getInt16(0, true)).toBe(32767);
      expect(view.getInt16(2, true)).toBe(-32768);
    });
  });

  describe('VoiceController Gnani Streaming Lifecycle', () => {
    let mockWebSocket: any;
    let mockMediaStream: any;
    const originalWindow = (globalThis as any).window;

    beforeEach(() => {
      mockWebSocket = {
        readyState: 1, // OPEN
        send: vi.fn(),
        close: vi.fn(),
        onopen: null,
        onmessage: null,
        onerror: null,
        onclose: null,
      };

      (globalThis as any).WebSocket = vi.fn().mockImplementation(() => mockWebSocket) as any;
      ((globalThis as any).WebSocket as any).OPEN = 1;

      mockMediaStream = {
        getTracks: vi.fn().mockReturnValue([{ stop: vi.fn() }]),
      };

      if (!navigator.mediaDevices) {
        (navigator as any).mediaDevices = {};
      }
      navigator.mediaDevices.getUserMedia = vi.fn().mockResolvedValue(mockMediaStream);

      (globalThis as any).window = {
        location: { protocol: 'http:', host: '127.0.0.1:8000' },
        AudioContext: vi.fn(),
      };
    });

    afterEach(() => {
      vi.restoreAllMocks();
      (globalThis as any).window = originalWindow;
    });

    it('initializes streaming, forwards callbacks, and dispatches final transcripts', async () => {
      const onTranscript = vi.fn();
      const onListeningStart = vi.fn();
      const vc = new VoiceController({ onListeningStart });

      // Mock AudioContext for node/jsdom environment
      const mockScriptProcessor = {
        onaudioprocess: null as any,
        connect: vi.fn(),
        disconnect: vi.fn(),
      };
      const mockSourceNode = {
        connect: vi.fn(),
      };
      const mockAudioCtx = {
        sampleRate: 48000,
        createMediaStreamSource: vi.fn().mockReturnValue(mockSourceNode),
        createScriptProcessor: vi.fn().mockReturnValue(mockScriptProcessor),
        destination: {},
        close: vi.fn().mockResolvedValue(undefined),
      };

      (window as any).AudioContext = vi.fn().mockImplementation(() => mockAudioCtx);

      const started = await vc.startGnaniStreaming({
        wsUrl: 'ws://127.0.0.1:8000/api/ws/stt',
        onTranscript,
      });

      expect(started).toBe(true);
      expect(onListeningStart).toHaveBeenCalled();
      expect((globalThis as any).WebSocket).toHaveBeenCalledWith('ws://127.0.0.1:8000/api/ws/stt');

      // Simulate receiving final transcript message from server
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'final_transcript',
          text: 'मिट्टी की नमी 28 प्रतिशत है',
          detected_language: 'hi-IN',
          duration_ms: 2100,
        }),
      });

      expect(onTranscript).toHaveBeenCalledWith('मिट्टी की नमी 28 प्रतिशत है', true, 'hi-IN');

      // Stop streaming
      vc.stopGnaniStreaming();
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify({ action: 'stop' }));
    });

    it('reconciles interim preview with final transcript and prevents stale session leakage', async () => {
      const onTranscript = vi.fn();
      const vc = new VoiceController();

      const mockScriptProcessor = {
        onaudioprocess: null as any,
        connect: vi.fn(),
        disconnect: vi.fn(),
      };
      const mockSourceNode = { connect: vi.fn() };
      const mockAudioCtx = {
        sampleRate: 48000,
        createMediaStreamSource: vi.fn().mockReturnValue(mockSourceNode),
        createScriptProcessor: vi.fn().mockReturnValue(mockScriptProcessor),
        destination: {},
        close: vi.fn().mockResolvedValue(undefined),
      };
      (window as any).AudioContext = vi.fn().mockImplementation(() => mockAudioCtx);

      await vc.startGnaniStreaming({
        wsUrl: 'ws://127.0.0.1:8000/api/ws/stt',
        onTranscript,
      });

      // 1. Receive interim transcript
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'interim_transcript',
          text: 'मेरे खेत की स्थिति क्या है',
          detected_language: 'hi-IN',
        }),
      });

      expect(onTranscript).toHaveBeenCalledWith('मेरे खेत की स्थिति क्या है', false, 'hi-IN');

      // 2. User clicks finishListening
      vc.finishListening();

      // finishListening should have sent 'stop' to websocket
      expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify({ action: 'stop' }));

      // 3. Server sends trailing final transcript with only a fragment e.g. "स्थिति"
      // The controller reconciles with the longer authoritative provisional transcript
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'final_transcript',
          text: 'स्थिति',
          detected_language: 'hi-IN',
        }),
      });

      // Should have dispatched the full reconciled text
      const finalCalls = onTranscript.mock.calls.filter((call) => call[1] === true);
      expect(finalCalls.length).toBeGreaterThan(0);
      expect(finalCalls[finalCalls.length - 1][0]).toBe('मेरे खेत की स्थिति क्या है');
    });
  });
});
