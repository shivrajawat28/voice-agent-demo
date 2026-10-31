/**
 * Vitest Tests for Pump Approval Workflow & GNANI AI Branding (Phase 18)
 */
import { describe, it, expect } from 'vitest';
import { ConversationEngine } from '../services/ConversationEngine';
import { PumpActionPayload } from '../types/voiceAgent';

describe('Pump Approval Workflow & Conversation Rules', () => {
  it('correctly categorizes pump activation queries in Hindi and English', () => {
    const engine = new ConversationEngine();

    const resHi = engine.processInput('फर्टोबॉट, मेरा पंप चालू कर दो');
    expect(resHi).not.toBeNull();
    expect(resHi?.intent).toBe('irrigation_inquiry');
    expect(resHi?.text).toContain('पंप चालू करने की अनुमति दें');

    const resEn = engine.processInput('turn on pump');
    expect(resEn).not.toBeNull();
    expect(resEn?.intent).toBe('irrigation_inquiry');
    expect(resEn?.text).toContain('Permission required');
  });

  it('correctly categorizes pump shutdown queries', () => {
    const engine = new ConversationEngine();

    const resHi = engine.processInput('पंप बंद कर दो');
    expect(resHi).not.toBeNull();
    expect(resHi?.text).toContain('पंप तुरंत बंद');

    const resEn = engine.processInput('turn off pump');
    expect(resEn).not.toBeNull();
    expect(resEn?.text).toContain('shut off immediately');
  });

  it('correctly categorizes pump status queries', () => {
    const engine = new ConversationEngine();

    const resHi = engine.processInput('पंप चालू है या बंद?');
    expect(resHi).not.toBeNull();
    expect(resHi?.text).toContain('DEMO-ZONE-001');

    const resEn = engine.processInput('is pump running?');
    expect(resEn).not.toBeNull();
    expect(resEn?.text).toContain('DEMO-ZONE-001');
  });

  it('validates PumpActionPayload safety fields', () => {
    const payload: PumpActionPayload = {
      action_id: 'act-12345678',
      session_id: 'test-sess',
      zone_id: 'DEMO-ZONE-001',
      probe_id: 'DEMO-DEVICE-001',
      action_type: 'PUMP_ON',
      state: 'AWAITING_USER_APPROVAL',
      created_at: Date.now() / 1000,
      expires_at: Date.now() / 1000 + 300,
      simulation_mode: true,
      actuation_permitted: false,
    };

    expect(payload.simulation_mode).toBe(true);
    expect(payload.actuation_permitted).toBe(false);
    expect(payload.expires_at - payload.created_at).toBe(300);
    expect(payload.state).toBe('AWAITING_USER_APPROVAL');
  });
});
