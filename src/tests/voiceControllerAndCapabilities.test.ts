import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceController } from '../services/VoiceController';
import { ConversationEngine } from '../services/ConversationEngine';
import { AgentStateMachine } from '../services/AgentStateMachine';

describe('VoiceController & Fallback Capabilities', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // 9. Unsupported speech recognition does not break text interaction
  it('handles environment without Web Speech API safely without crashing text engine', () => {
    const caps = VoiceController.getCapabilities();
    expect(caps.speechRecognitionSupported).toBe(false);
    expect(caps.speechSynthesisSupported).toBe(false);

    let reportedError = '';
    const vc = new VoiceController({
      onError: (msg) => {
        reportedError = msg;
      },
    });

    const started = vc.startListening();
    expect(started).toBe(false);
    expect(reportedError).toContain('Speech recognition is not supported');

    // Text interaction via ConversationEngine and StateMachine continues to function flawlessly
    const engine = new ConversationEngine();
    const sm = new AgentStateMachine('idle');

    expect(sm.can('TEXT_SUBMITTED')).toBe(true);
    sm.transition('TEXT_SUBMITTED');
    expect(sm.getState()).toBe('processing');

    const result = engine.processInput('Hello');
    expect(result?.intent).toBe('greeting');

    sm.transition('SPEAK_END');
    expect(sm.getState()).toBe('idle');
  });

  it('cancelAll resets listening and speaking active flags', () => {
    const vc = new VoiceController();
    vc.cancelAll();
    expect(vc.isListening()).toBe(false);
    expect(vc.isSpeaking()).toBe(false);
  });

  it('allows language configuration', () => {
    const vc = new VoiceController();
    expect(vc.getLanguage()).toBe('en-US');
    vc.setLanguage('hi-IN');
    expect(vc.getLanguage()).toBe('hi-IN');
  });
});

describe('VoiceController with Mocked Web Speech APIs', () => {
  let originalWindow: any;
  let mockRecognitionInstance: any;
  let mockVoices: any[];

  beforeEach(() => {
    originalWindow = (globalThis as any).window;

    mockVoices = [
      { name: 'Google US English', lang: 'en-US', default: true },
      { name: 'Google हिन्दी', lang: 'hi-IN', default: false },
      { name: 'Rishi (Indian English)', lang: 'en-IN', default: false },
    ];

    // Define mock SpeechRecognition
    class MockSpeechRecognition {
      lang = 'en-US';
      continuous = false;
      interimResults = false;
      maxAlternatives = 1;
      onstart: (() => void) | null = null;
      onresult: ((event: any) => void) | null = null;
      onerror: ((event: any) => void) | null = null;
      onend: (() => void) | null = null;

      start = vi.fn(() => {
        mockRecognitionInstance = this;
        if (this.onstart) this.onstart();
      });

      abort = vi.fn(() => {
        if (this.onerror) this.onerror({ error: 'aborted' });
        if (this.onend) this.onend();
      });
    }

    const mockSpeechSynthesis = {
      speak: vi.fn(),
      cancel: vi.fn(),
      getVoices: vi.fn(() => mockVoices),
      onvoiceschanged: null,
    };

    class MockSpeechSynthesisUtterance {
      text: string;
      lang = 'en-US';
      rate = 1.0;
      pitch = 1.0;
      voice: any = null;
      onstart: (() => void) | null = null;
      onend: (() => void) | null = null;
      onerror: ((e: any) => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    }

    class MockAudio {
      src = '';
      onplay: (() => void) | null = null;
      onended: (() => void) | null = null;
      onerror: ((e: any) => void) | null = null;
      currentTime = 0;
      pause = vi.fn();
      play = vi.fn().mockImplementation(() => {
        if (this.onplay) this.onplay();
        return Promise.resolve();
      });
    }

    (globalThis as any).Audio = MockAudio;
    (globalThis as any).URL = {
      createObjectURL: vi.fn(() => 'blob:mock-url-1234'),
      revokeObjectURL: vi.fn(),
    };

    (globalThis as any).window = {
      SpeechRecognition: MockSpeechRecognition,
      speechSynthesis: mockSpeechSynthesis,
      SpeechSynthesisUtterance: MockSpeechSynthesisUtterance,
    };
    (globalThis as any).SpeechSynthesisUtterance = MockSpeechSynthesisUtterance;
  });

  afterEach(() => {
    (globalThis as any).window = originalWindow;
    delete (globalThis as any).SpeechSynthesisUtterance;
    delete (globalThis as any).Audio;
    delete (globalThis as any).URL;
  });

  it('detects Web Speech capabilities when APIs are present', () => {
    const caps = VoiceController.getCapabilities();
    expect(caps.speechRecognitionSupported).toBe(true);
    expect(caps.speechSynthesisSupported).toBe(true);
    expect(caps.hasHindiVoice).toBe(true);
  });

  // 5. Cancellation from listening
  it('cancellation from listening aborts recognition without triggering error callbacks', () => {
    let errorReported = false;
    const vc = new VoiceController({
      onError: () => {
        errorReported = true;
      },
    });

    const started = vc.startListening();
    expect(started).toBe(true);
    expect(vc.isListening()).toBe(true);
    expect(mockRecognitionInstance.start).toHaveBeenCalled();

    // Cancel while listening
    vc.stopListening();
    expect(mockRecognitionInstance.abort).toHaveBeenCalled();
    expect(vc.isListening()).toBe(false);

    // Ensure user-initiated abort did not trigger error callback
    expect(errorReported).toBe(false);
  });

  // 5. Cancellation from speaking
  it('cancellation from speaking calls speechSynthesis.cancel safely without false error', () => {
    let errorReported = false;
    const vc = new VoiceController({
      onError: () => {
        errorReported = true;
      },
    });

    let capturedUtterance: any;
    (globalThis as any).window.speechSynthesis.speak = vi.fn((utterance) => {
      capturedUtterance = utterance;
    });

    vc.speak('Testing speech output');
    expect((globalThis as any).window.speechSynthesis.speak).toHaveBeenCalled();

    // User cancels speaking
    vc.stopSpeaking();
    expect((globalThis as any).window.speechSynthesis.cancel).toHaveBeenCalled();
    expect(vc.isSpeaking()).toBe(false);

    // Browser fires onerror with error='canceled'
    capturedUtterance.onerror({ error: 'canceled' });
    expect(errorReported).toBe(false); // Suppressed expected cancel
  });

  // Speech playback start and completion lifecycle
  it('triggers onSpeakingStart and onSpeakingEnd callbacks only when browser emits those events', () => {
    let started = false;
    let ended = false;
    let capturedUtterance: any = null;

    (globalThis as any).window.speechSynthesis.speak = vi.fn((utterance: any) => {
      capturedUtterance = utterance;
    });

    const vc = new VoiceController({
      onSpeakingStart: () => {
        started = true;
      },
      onSpeakingEnd: () => {
        ended = true;
      },
    });

    vc.speak('Hello there');
    expect(started).toBe(false);
    expect(ended).toBe(false);

    // Simulate browser beginning speech playback
    capturedUtterance.onstart();
    expect(started).toBe(true);
    expect(ended).toBe(false);

    // Simulate browser finishing speech playback
    capturedUtterance.onend();
    expect(ended).toBe(true);
  });

  // Genuine SpeechSynthesis failure handling
  it('handles genuine SpeechSynthesis failure and triggers onError without crashing', () => {
    let reportedError = '';
    let isPerm = false;
    let capturedUtterance: any = null;

    (globalThis as any).window.speechSynthesis.speak = vi.fn((utterance: any) => {
      capturedUtterance = utterance;
    });

    const vc = new VoiceController({
      onError: (msg, perm) => {
        reportedError = msg;
        isPerm = perm;
      },
    });

    vc.speak('Some sentence');
    // Simulate genuine browser TTS error
    capturedUtterance.onerror({ error: 'language-unavailable' });

    expect(reportedError).toContain('not supported by your browser');
    expect(isPerm).toBe(false);
    expect(vc.isSpeaking()).toBe(false);
  });

  // Hindi voice selection
  it('selects suitable Hindi voice when hi-IN language is configured', () => {
    const vc = new VoiceController();
    vc.setLanguage('hi-IN');

    const selectedVoice = vc.getSelectedVoice();
    expect(selectedVoice).not.toBeNull();
    expect(selectedVoice?.name).toBe('Google हिन्दी');
    expect(selectedVoice?.lang).toBe('hi-IN');
  });

  // 6. Empty recognition results
  it('does not dispatch transcription result when recognition result is empty or silence', () => {
    let dispatchedText: string | null = null;
    const vc = new VoiceController({
      onTranscriptionResult: (text) => {
        dispatchedText = text;
      },
    });

    vc.startListening();
    mockRecognitionInstance.onresult({ results: [] });
    mockRecognitionInstance.onend();

    expect(dispatchedText).toBeNull();
    expect(vc.isListening()).toBe(false);
  });

  // 7. Recognition permission denied
  it('handles permission denied error (not-allowed) by flagging isPermissionDenied', () => {
    let errorMessage = '';
    let isPermDenied = false;

    const vc = new VoiceController({
      onError: (msg, denied) => {
        errorMessage = msg;
        isPermDenied = denied;
      },
    });

    vc.startListening();
    mockRecognitionInstance.onerror({ error: 'not-allowed' });

    expect(isPermDenied).toBe(true);
    expect(errorMessage).toContain('Microphone permission was denied');
    expect(vc.isListening()).toBe(false);
  });

  // 8. Prevention of duplicate transcript processing
  it('prevents duplicate transcript dispatching if recognition emits repeated events', () => {
    let dispatchCount = 0;
    let dispatchedText = '';

    const vc = new VoiceController({
      onTranscriptionResult: (text) => {
        dispatchCount += 1;
        dispatchedText = text;
      },
    });

    vc.startListening();
    mockRecognitionInstance.onresult({
      results: [[{ transcript: 'Hello assistant' }]],
    });
    mockRecognitionInstance.onend();

    // Redundant subsequent event or redundant onend
    mockRecognitionInstance.onend();

    expect(dispatchCount).toBe(1);
    expect(dispatchedText).toBe('Hello assistant');
  });

  // Duplicate startListening prevention
  it('rejects concurrent startListening calls while session is already active', () => {
    const vc = new VoiceController();
    const firstCall = vc.startListening();
    expect(firstCall).toBe(true);

    const secondCall = vc.startListening();
    expect(secondCall).toBe(false);
  });

  // Backend Audio Playback (playAudioBlob) tests
  it('playAudioBlob plays synthesized audio, triggers speaking callbacks, and revokes object URL on completion', () => {
    let speakingStarted = false;
    let speakingEnded = false;

    const vc = new VoiceController({
      onSpeakingStart: () => {
        speakingStarted = true;
      },
      onSpeakingEnd: () => {
        speakingEnded = true;
      },
    });

    const mockBlob = new Blob(['RIFFmockdata'], { type: 'audio/wav' });
    let callbackFinished = false;

    const played = vc.playAudioBlob(mockBlob, () => {
      callbackFinished = true;
    });

    expect(played).toBe(true);
    expect(speakingStarted).toBe(true);
    expect(vc.isSpeaking()).toBe(true);
    expect((globalThis as any).URL.createObjectURL).toHaveBeenCalledWith(mockBlob);

    // Simulate audio ended
    const currentAudio = (vc as any).currentAudioElement;
    expect(currentAudio).toBeDefined();
    currentAudio.onended();

    expect(speakingEnded).toBe(true);
    expect(callbackFinished).toBe(true);
    expect(vc.isSpeaking()).toBe(false);
    expect((globalThis as any).URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url-1234');
  });

  it('stopSpeaking and cancelAll pause active audio element and immediately clean up object URL', () => {
    const vc = new VoiceController();
    const mockBlob = new Blob(['RIFFmockdata'], { type: 'audio/wav' });

    vc.playAudioBlob(mockBlob);
    expect(vc.isSpeaking()).toBe(true);

    const currentAudio = (vc as any).currentAudioElement;
    expect(currentAudio).toBeDefined();

    // Cancel mid-playback
    vc.stopSpeaking();
    expect(currentAudio.pause).toHaveBeenCalled();
    expect(vc.isSpeaking()).toBe(false);
    expect((globalThis as any).URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url-1234');
    expect((vc as any).currentAudioElement).toBeNull();
  });

  it('state machine transitions cleanly through backend audio playback lifecycle', () => {
    const sm = new AgentStateMachine('idle');

    expect(sm.getState()).toBe('idle');
    expect(sm.can('START_LISTENING')).toBe(true);

    sm.transition('START_LISTENING');
    expect(sm.getState()).toBe('listening');

    sm.transition('TRANSCRIPTION_RECEIVED');
    expect(sm.getState()).toBe('processing');

    // Speech started from backend audio
    sm.transition('SPEAK_START');
    expect(sm.getState()).toBe('speaking');

    // Speech ended
    sm.transition('SPEAK_END');
    expect(sm.getState()).toBe('idle');
  });

  it('consecutive playAudioBlob calls cancel existing playback without overlapping audio sessions', () => {
    const vc = new VoiceController();
    const mockBlob1 = new Blob(['RIFFmockdata1'], { type: 'audio/wav' });
    const mockBlob2 = new Blob(['RIFFmockdata2'], { type: 'audio/wav' });

    vc.playAudioBlob(mockBlob1);
    const firstAudio = (vc as any).currentAudioElement;
    expect(firstAudio).toBeDefined();

    // Trigger second playback before first finishes
    vc.playAudioBlob(mockBlob2);
    expect(firstAudio.pause).toHaveBeenCalled();
    const secondAudio = (vc as any).currentAudioElement;
    expect(secondAudio).toBeDefined();
    expect(secondAudio).not.toBe(firstAudio);
    expect(vc.isSpeaking()).toBe(true);

    vc.stopSpeaking();
    expect(vc.isSpeaking()).toBe(false);
  });

  it('playAudioBlob gracefully handles audio play rejection without throwing unhandled exceptions', async () => {
    const vc = new VoiceController();
    const mockBlob = new Blob(['corruptdata'], { type: 'audio/wav' });

    let errorCaught = false;
    // Mock play to reject
    const mockPlayReject = vi.fn().mockRejectedValue(new Error('Autoplay policy violation'));
    const origAudio = (globalThis as any).Audio;
    class RejectingAudio {
      src = '';
      play = mockPlayReject;
      pause = vi.fn();
    }
    (globalThis as any).Audio = RejectingAudio;

    try {
      const res = vc.playAudioBlob(mockBlob, undefined, () => {
        errorCaught = true;
      });
      expect(res).toBe(true);
      // Allow promise microtask to resolve
      await Promise.resolve();
      expect(errorCaught).toBe(true);
    } finally {
      (globalThis as any).Audio = origAudio;
    }
  });
});
