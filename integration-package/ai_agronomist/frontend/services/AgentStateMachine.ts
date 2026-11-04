/**
 * AgentStateMachine
 *
 * Implements a strict, deterministic Finite State Machine for the Voice Agent.
 * Enforces valid transitions and rejects invalid or concurrent operations.
 *
 * State Diagram:
 *   idle ──(START_LISTENING)──► listening ──(TRANSCRIPTION_RECEIVED)──► processing
 *     │                                                                     │
 *     └──(TEXT_SUBMITTED)───────────────────────────────────────────────────┤
 *                                                                           ▼
 *   idle ◄───────────────(SPEAK_END)─────────────────────────────────── speaking
 *     ▲                                                                     │
 *     │                                (FAIL from any active state)         ▼
 *     └─────────────────(CANCEL_OR_RESET)───────────────────────────────► error
 */

import { AgentState, StateEvent } from '../types/voiceAgent';

export type StateChangeCallback = (state: AgentState, error: string | null) => void;

export class AgentStateMachine {
  private currentState: AgentState = 'idle';
  private lastError: string | null = null;
  private listeners: Set<StateChangeCallback> = new Set();

  /**
   * Transition matrix defining valid (sourceState, event) -> targetState pairs
   */
  private static readonly TRANSITIONS: Record<
    AgentState,
    Partial<Record<StateEvent, AgentState>>
  > = {
    idle: {
      START_LISTENING: 'listening',
      TEXT_SUBMITTED: 'processing',
      CANCEL_OR_RESET: 'idle',
    },
    listening: {
      FINALIZE_START: 'finalizing',
      TRANSCRIPTION_RECEIVED: 'processing',
      FAIL: 'error',
      CANCEL_OR_RESET: 'idle',
    },
    finalizing: {
      TRANSCRIPTION_RECEIVED: 'processing',
      FAIL: 'error',
      CANCEL_OR_RESET: 'idle',
    },
    processing: {
      SPEAK_START: 'speaking',
      SPEAK_END: 'idle', // In case voice output is disabled/silent
      FAIL: 'error',
      CANCEL_OR_RESET: 'idle',
    },
    speaking: {
      SPEAK_END: 'idle',
      FAIL: 'error',
      CANCEL_OR_RESET: 'idle',
    },
    error: {
      START_LISTENING: 'listening', // Allow user to retry directly
      TEXT_SUBMITTED: 'processing', // Allow user to retry text input directly
      CANCEL_OR_RESET: 'idle',
    },
  };

  constructor(initialState: AgentState = 'idle') {
    this.currentState = initialState;
  }

  /**
   * Query if an event is permissible from the current state
   */
  public can(event: StateEvent): boolean {
    const validTargets = AgentStateMachine.TRANSITIONS[this.currentState];
    return validTargets ? Boolean(validTargets[event]) : false;
  }

  /**
   * Attempt transition. If invalid, does NOT alter state and returns success: false.
   */
  public transition(
    event: StateEvent,
    errorMsg?: string
  ): { success: boolean; state: AgentState; error?: string } {
    const validTargets = AgentStateMachine.TRANSITIONS[this.currentState];
    const nextState = validTargets ? validTargets[event] : undefined;

    if (!nextState) {
      const err = `Invalid transition: cannot handle event "${event}" while in state "${this.currentState}".`;
      return { success: false, state: this.currentState, error: err };
    }

    this.currentState = nextState;
    if (nextState === 'error') {
      this.lastError = errorMsg || 'An unknown interaction error occurred.';
    } else {
      this.lastError = null;
    }

    this.notify();
    return { success: true, state: this.currentState, error: this.lastError || undefined };
  }

  /**
   * Safely abort/cancel any current activity and return to 'idle'
   */
  public cancel(): void {
    this.currentState = 'idle';
    this.lastError = null;
    this.notify();
  }

  public getState(): AgentState {
    return this.currentState;
  }

  public getError(): string | null {
    return this.lastError;
  }

  public subscribe(cb: StateChangeCallback): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  private notify(): void {
    for (const listener of this.listeners) {
      try {
        listener(this.currentState, this.lastError);
      } catch (e) {
        console.error('Error in state machine listener:', e);
      }
    }
  }
}
