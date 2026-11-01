import { describe, it, expect, beforeEach } from 'vitest';
import { AgentStateMachine } from '../services/AgentStateMachine';

describe('AgentStateMachine (Finite State Machine)', () => {
  let sm: AgentStateMachine;

  beforeEach(() => {
    sm = new AgentStateMachine('idle');
  });

  it('starts in idle state', () => {
    expect(sm.getState()).toBe('idle');
    expect(sm.getError()).toBeNull();
  });

  // Valid voice flow: idle -> listening -> processing -> speaking -> idle
  it('follows valid voice input lifecycle correctly', () => {
    // 1. Start listening
    expect(sm.can('START_LISTENING')).toBe(true);
    const step1 = sm.transition('START_LISTENING');
    expect(step1.success).toBe(true);
    expect(sm.getState()).toBe('listening');

    // 2. Transcription received -> processing
    expect(sm.can('TRANSCRIPTION_RECEIVED')).toBe(true);
    const step2 = sm.transition('TRANSCRIPTION_RECEIVED');
    expect(step2.success).toBe(true);
    expect(sm.getState()).toBe('processing');

    // 3. Speaking start
    expect(sm.can('SPEAK_START')).toBe(true);
    const step3 = sm.transition('SPEAK_START');
    expect(step3.success).toBe(true);
    expect(sm.getState()).toBe('speaking');

    // 4. Speaking end -> idle
    expect(sm.can('SPEAK_END')).toBe(true);
    const step4 = sm.transition('SPEAK_END');
    expect(step4.success).toBe(true);
    expect(sm.getState()).toBe('idle');
  });

  // Valid text fallback flow: idle -> processing -> speaking -> idle
  it('follows valid text fallback lifecycle correctly', () => {
    expect(sm.can('TEXT_SUBMITTED')).toBe(true);
    const step1 = sm.transition('TEXT_SUBMITTED');
    expect(step1.success).toBe(true);
    expect(sm.getState()).toBe('processing');

    const step2 = sm.transition('SPEAK_END');
    expect(step2.success).toBe(true);
    expect(sm.getState()).toBe('idle');
  });

  // 7. Invalid state transitions are rejected or safely handled
  it('rejects invalid state transitions without corrupting current state', () => {
    // Cannot jump from idle directly to speaking
    expect(sm.can('SPEAK_START')).toBe(false);
    const invalidResult = sm.transition('SPEAK_START');
    expect(invalidResult.success).toBe(false);
    expect(invalidResult.error).toContain('cannot handle event "SPEAK_START" while in state "idle"');
    expect(sm.getState()).toBe('idle');

    // Start listening
    sm.transition('START_LISTENING');
    expect(sm.getState()).toBe('listening');

    // Cannot jump from listening directly to speaking without processing
    expect(sm.can('SPEAK_START')).toBe(false);
    const badStep = sm.transition('SPEAK_START');
    expect(badStep.success).toBe(false);
    expect(sm.getState()).toBe('listening');
  });

  // 8. Cancel returns the controller to a usable state
  it('cancel returns state machine to idle from any state', () => {
    // Cancel from listening
    sm.transition('START_LISTENING');
    expect(sm.getState()).toBe('listening');
    sm.cancel();
    expect(sm.getState()).toBe('idle');
    expect(sm.getError()).toBeNull();

    // Cancel from processing
    sm.transition('TEXT_SUBMITTED');
    expect(sm.getState()).toBe('processing');
    sm.cancel();
    expect(sm.getState()).toBe('idle');

    // Cancel from speaking
    sm.transition('TEXT_SUBMITTED');
    sm.transition('SPEAK_START');
    expect(sm.getState()).toBe('speaking');
    sm.cancel();
    expect(sm.getState()).toBe('idle');

    // Cancel from error
    sm.transition('START_LISTENING');
    sm.transition('FAIL', 'Microphone connection timeout');
    expect(sm.getState()).toBe('error');
    expect(sm.getError()).toBe('Microphone connection timeout');
    sm.cancel();
    expect(sm.getState()).toBe('idle');
    expect(sm.getError()).toBeNull();
  });

  // 10. Recovery after a recoverable error
  it('allows safe recovery from error state via retry listening, text input, or dismissal', () => {
    // Put into error state
    sm.transition('START_LISTENING');
    sm.transition('FAIL', 'Permission denied');
    expect(sm.getState()).toBe('error');
    expect(sm.getError()).toBe('Permission denied');

    // Recovery path 1: Retry microphone input
    expect(sm.can('START_LISTENING')).toBe(true);
    const retryMic = sm.transition('START_LISTENING');
    expect(retryMic.success).toBe(true);
    expect(sm.getState()).toBe('listening');
    expect(sm.getError()).toBeNull(); // Error cleared upon successful transition

    // Put back into error state
    sm.transition('FAIL', 'Network unreachable');
    expect(sm.getState()).toBe('error');

    // Recovery path 2: Fallback to text input
    expect(sm.can('TEXT_SUBMITTED')).toBe(true);
    const retryText = sm.transition('TEXT_SUBMITTED');
    expect(retryText.success).toBe(true);
    expect(sm.getState()).toBe('processing');
    expect(sm.getError()).toBeNull();

    // Complete flow
    sm.transition('SPEAK_END');
    expect(sm.getState()).toBe('idle');

    // Put into error state once more
    sm.transition('START_LISTENING');
    sm.transition('FAIL', 'Audio device disconnected');
    expect(sm.getState()).toBe('error');

    // Recovery path 3: Cancel / Dismiss
    sm.transition('CANCEL_OR_RESET');
    expect(sm.getState()).toBe('idle');
    expect(sm.getError()).toBeNull();
  });

  it('notifies subscribers on state transitions', () => {
    let notifiedState = '';
    sm.subscribe((state) => {
      notifiedState = state;
    });

    sm.transition('START_LISTENING');
    expect(notifiedState).toBe('listening');

    sm.transition('TRANSCRIPTION_RECEIVED');
    expect(notifiedState).toBe('processing');
  });

  // Phase 26: Finalizing State Transitions
  it('supports the Phase 26 finalizing workflow and guards against duplicate finalization', () => {
    // 1. Enter listening
    sm.transition('START_LISTENING');
    expect(sm.getState()).toBe('listening');

    // 2. User clicks "Done Speaking" -> FINALIZE_START
    expect(sm.can('FINALIZE_START')).toBe(true);
    const finalizeStep = sm.transition('FINALIZE_START');
    expect(finalizeStep.success).toBe(true);
    expect(sm.getState()).toBe('finalizing');

    // 3. Duplicate clicks to FINALIZE_START are rejected while finalizing
    expect(sm.can('FINALIZE_START')).toBe(false);
    const duplicateStep = sm.transition('FINALIZE_START');
    expect(duplicateStep.success).toBe(false);
    expect(sm.getState()).toBe('finalizing');

    // 4. Transcription received moves to processing
    expect(sm.can('TRANSCRIPTION_RECEIVED')).toBe(true);
    const processStep = sm.transition('TRANSCRIPTION_RECEIVED');
    expect(processStep.success).toBe(true);
    expect(sm.getState()).toBe('processing');

    // 5. Duplicate FINALIZE_START is also rejected while processing
    expect(sm.can('FINALIZE_START')).toBe(false);
    expect(sm.transition('FINALIZE_START').success).toBe(false);

    // 6. Complete normal speech lifecycle
    sm.transition('SPEAK_START');
    expect(sm.getState()).toBe('speaking');
    sm.transition('SPEAK_END');
    expect(sm.getState()).toBe('idle');
  });

  it('allows safe cancel or error from finalizing state', () => {
    // Cancel path
    sm.transition('START_LISTENING');
    sm.transition('FINALIZE_START');
    expect(sm.getState()).toBe('finalizing');
    sm.cancel();
    expect(sm.getState()).toBe('idle');

    // Error path
    sm.transition('START_LISTENING');
    sm.transition('FINALIZE_START');
    expect(sm.getState()).toBe('finalizing');
    sm.transition('FAIL', 'WebSocket dropped during finalization');
    expect(sm.getState()).toBe('error');
    expect(sm.getError()).toBe('WebSocket dropped during finalization');
  });
});

