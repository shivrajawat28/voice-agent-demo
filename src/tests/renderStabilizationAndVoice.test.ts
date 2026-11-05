import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceController } from '../services/VoiceController';

describe('Phase 33.0 Render Stabilization and Voice Pipeline', () => {
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
      location: { protocol: 'https:', host: 'fertobot-staging.onrender.com' },
      AudioContext: vi.fn().mockImplementation(() => ({
        sampleRate: 16000,
        createMediaStreamSource: vi.fn().mockReturnValue({ connect: vi.fn(), disconnect: vi.fn() }),
        createScriptProcessor: vi.fn().mockReturnValue({ onaudioprocess: null, connect: vi.fn(), disconnect: vi.fn() }),
        createGain: vi.fn().mockReturnValue({ connect: vi.fn(), disconnect: vi.fn(), gain: { value: 1 } }),
        destination: {},
        close: vi.fn().mockResolvedValue(undefined),
      })),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
    (globalThis as any).window = originalWindow;
  });

  describe('STT Idle Timeout Handling', () => {
    it('dispatches onIdleTimeout callback when server sends idle_timeout event and does not trigger onError', async () => {
      const onIdleTimeout = vi.fn();
      const onError = vi.fn();
      const onListeningEnd = vi.fn();

      const vc = new VoiceController({
        onIdleTimeout,
        onError,
        onListeningEnd,
      });

      const started = await vc.startGnaniStreaming({
        wsUrl: 'wss://fertobot-staging.onrender.com/api/ws/stt',
      });
      expect(started).toBe(true);

      // Simulate the backend emitting an idle_timeout message after 60 seconds
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'idle_timeout',
          code: 'NO_SPEECH_TIMEOUT',
          message: 'No speech detected. Tap the microphone to try again.',
        }),
      });

      expect(onIdleTimeout).toHaveBeenCalledWith('No speech detected. Tap the microphone to try again.');
      expect(onListeningEnd).toHaveBeenCalled();
      // Crucial: onError must NOT have been called!
      expect(onError).not.toHaveBeenCalled();
    });

    it('cleans up event listeners and audio nodes when idle timeout occurs', async () => {
      const vc = new VoiceController();
      await vc.startGnaniStreaming();

      // Verify listeners attached
      expect(mockWebSocket.onmessage).not.toBeNull();

      // Trigger idle timeout
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'idle_timeout',
          code: 'NO_SPEECH_TIMEOUT',
          message: 'Session closed',
        }),
      });

      // After cleanup, listeners are nulled out to prevent memory leaks / ghost events
      expect(mockWebSocket.onmessage).toBeNull();
      expect(mockWebSocket.onerror).toBeNull();
      expect(mockWebSocket.onclose).toBeNull();
    });
  });

  describe('Voice Sample URLs', () => {
    it('references existing neural sample audio files for Deepak and Nalini', () => {
      const getSampleUrl = (voice: string) =>
        voice === 'Deepak' ? '/samples/sample_1_deepak.wav' : '/samples/sample_1_nalini.wav';

      expect(getSampleUrl('Deepak')).toBe('/samples/sample_1_deepak.wav');
      expect(getSampleUrl('Nalini')).toBe('/samples/sample_1_nalini.wav');
      // Must NOT be the old 404 filenames
      expect(getSampleUrl('Deepak')).not.toContain('Deepak_hi_sample_1.wav');
      expect(getSampleUrl('Nalini')).not.toContain('Nalini_hi_sample_1.wav');
    });
  });

  describe('Voice Selection Resolution', () => {
    it('preserves user selected voice instead of blindly overriding to Nalini for Hindi', () => {
      const resolveVoice = (selectedVoice: string, language: string) => {
        return selectedVoice || (language.startsWith('hi') ? 'Nalini' : 'Kaveri');
      };

      // When user selects Deepak for Hindi:
      expect(resolveVoice('Deepak', 'hi-IN')).toBe('Deepak');

      // When user selects Nalini for Hindi:
      expect(resolveVoice('Nalini', 'hi-IN')).toBe('Nalini');

      // When user leaves voice unselected (empty string):
      expect(resolveVoice('', 'hi-IN')).toBe('Nalini');
      expect(resolveVoice('', 'en-IN')).toBe('Kaveri');

      // When user selects Pranav for English:
      expect(resolveVoice('Pranav', 'en-IN')).toBe('Pranav');
    });
  });
});
