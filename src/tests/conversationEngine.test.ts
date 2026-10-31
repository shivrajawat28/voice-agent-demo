import { describe, it, expect, beforeEach } from 'vitest';
import { ConversationEngine } from '../services/ConversationEngine';

describe('ConversationEngine (Deterministic Brain)', () => {
  let engine: ConversationEngine;

  beforeEach(() => {
    engine = new ConversationEngine();
  });

  // 1. Greeting produces expected response
  it('identifies greeting intent and generates expected welcoming response', () => {
    const res1 = engine.processInput('Hello');
    expect(res1).not.toBeNull();
    expect(res1?.intent).toBe('greeting');
    expect(res1?.text).toContain('FertoBot Voice Assistant running in local demo mode');

    const res2 = engine.processInput('hi there');
    expect(res2?.intent).toBe('greeting');

    const res3 = engine.processInput('Namaste');
    expect(res3?.intent).toBe('greeting');
  });

  // 2. Agent introduction produces expected response
  it('identifies introduction intent and returns agent identity', () => {
    const res = engine.processInput('Who are you?');
    expect(res).not.toBeNull();
    expect(res?.intent).toBe('intro');
    expect(res?.text).toContain('FertoBot Voice Agent, an AI farm assistant demo');
  });

  // 3. Help produces expected response
  it('identifies help intent and describes capabilities', () => {
    const res = engine.processInput('What can you do?');
    expect(res).not.toBeNull();
    expect(res?.intent).toBe('help');
    expect(res?.text).toContain('You can say: "Hello", "Who are you?", "Farm status"');
  });

  // 4. Unknown input returns a friendly fallback
  it('routes unfamiliar input to fallback intent with guidance', () => {
    const res = engine.processInput('What is the capital of Mars?');
    expect(res).not.toBeNull();
    expect(res?.intent).toBe('unknown');
    expect(res?.text).toContain("I didn't quite catch that in this demo");
  });

  // 5. Repeat works when a previous response exists, and handles empty history
  it('handles repeat intent correctly with and without previous response', () => {
    // When no previous response exists:
    const initialRepeat = engine.processInput('Repeat that');
    expect(initialRepeat?.intent).toBe('repeat');
    expect(initialRepeat?.text).toContain("I haven't said anything yet to repeat!");

    // After a previous response:
    engine.processInput('Hello');
    const repeatAfterHello = engine.processInput('say that again');
    expect(repeatAfterHello?.intent).toBe('repeat');
    expect(repeatAfterHello?.text).toContain('Repeating: "Hello! I am your FertoBot Voice Assistant');

    // Repeat itself should not overwrite the underlying repeatable text
    const secondRepeat = engine.processInput('repeat');
    expect(secondRepeat?.text).toContain('Repeating: "Hello! I am your FertoBot Voice Assistant');
  });

  // 6. Goodbye is handled predictably
  it('identifies goodbye intent and responds gracefully', () => {
    const res = engine.processInput('Goodbye');
    expect(res).not.toBeNull();
    expect(res?.intent).toBe('goodbye');
    expect(res?.text).toContain('May your harvest be bountiful');
  });

  // 10. Empty transcripts do not create unintended responses
  it('returns null for empty strings or whitespace input', () => {
    expect(engine.processInput('')).toBeNull();
    expect(engine.processInput('   ')).toBeNull();
    expect(engine.processInput('\t\n')).toBeNull();
  });

  // Extra: Farm Status Domain Previews
  it('handles farm status queries deterministically', () => {
    const res = engine.processInput('Check soil moisture and temperature');
    expect(res?.intent).toBe('farm_status');
    expect(res?.text).toContain('Soil Moisture: 48.2%');
  });
});

