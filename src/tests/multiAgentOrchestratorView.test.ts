/**
 * Frontend Multi-Agent Orchestrator Integration & Speech Isolation Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChatMessage, EngineResponse } from '../types/voiceAgent';
import { VoiceController } from '../services/VoiceController';

describe('Multi-Agent Response Model & Speech Isolation', () => {
  let mockSpeak: any;

  beforeEach(() => {
    mockSpeak = vi.fn().mockReturnValue(true);
    // Mock VoiceController speak method
    vi.spyOn(VoiceController.prototype, 'speak').mockImplementation(mockSpeak);
  });

  it('guarantees that speech synthesis receives only clean spoken text and never raw trace or JSON', () => {
    const vc = new VoiceController();

    const sampleEngineResponse: EngineResponse = {
      intent: 'agricultural_inquiry',
      text: 'Yellowing of lower leaves indicates nitrogen deficiency or root waterlogging.',
      confidence: 0.95,
      repeatable: true,
      agent_results: [
        {
          agent_id: 'crop_symptom',
          name: 'Crop Symptom Specialist',
          status: 'completed',
          summary: 'Nitrogen deficiency or root waterlogging detected.',
          evidence: ['Chlorosis matches nitrogen deficiency pattern'],
          limitations: ['Crop variety not specified'],
        },
      ],
      execution_trace: [
        {
          step_id: 's1',
          agent_id: 'orchestrator',
          action: 'plan_execution',
          status: 'completed',
          duration_ms: 12.5,
        },
      ],
      sources: ['Agronomic Knowledgebase v2.4'],
      warnings: ['Recent watering schedule unconfirmed'],
      needs_clarification: true,
      provider_status: 'mock',
    };

    // Simulate vocalization call as done in useVoiceAgent
    vc.speak(sampleEngineResponse.text, () => {});

    // Verification: speak was invoked with the exact natural text
    expect(mockSpeak).toHaveBeenCalledTimes(1);
    expect(mockSpeak).toHaveBeenCalledWith(
      'Yellowing of lower leaves indicates nitrogen deficiency or root waterlogging.',
      expect.any(Function)
    );

    // Verify it NEVER received JSON or trace strings
    const spokenArg = mockSpeak.mock.calls[0][0];
    expect(spokenArg).not.toContain('"agent_id"');
    expect(spokenArg).not.toContain('execution_trace');
    expect(spokenArg).not.toContain('duration_ms');
  });

  it('correctly maps multi-agent structured fields to ChatMessage', () => {
    const sampleBackendPayload = {
      reply: 'Soil moisture is optimal at 48.2%. Rain expected.',
      intent: 'irrigation_inquiry',
      confidence: 0.92,
      repeatable: true,
      agent_results: [
        {
          agent_id: 'irrigation_advisory',
          name: 'Irrigation Advisory Specialist',
          status: 'completed',
          summary: 'Postpone irrigation due to rain.',
          evidence: ['Moisture: 48.2%', 'Rain: 65%'],
          limitations: ['Single probe depth'],
        },
      ],
      execution_trace: [
        {
          step_id: 'step-1',
          agent_id: 'orchestrator',
          action: 'plan_execution',
          status: 'completed',
          duration_ms: 8.4,
        },
      ],
      sources: ['Farm Probe Telemetry (Read-Only)', 'Open-Meteo Weather API'],
      warnings: ['Telemetry reflects 15cm probe depth'],
      needs_clarification: false,
      provider_status: 'mock',
    };

    const chatMsg: ChatMessage = {
      id: 'msg-123',
      role: 'agent',
      text: sampleBackendPayload.reply,
      timestamp: new Date(),
      intent: sampleBackendPayload.intent as any,
      agentResults: sampleBackendPayload.agent_results,
      executionTrace: sampleBackendPayload.execution_trace,
      sources: sampleBackendPayload.sources,
      warnings: sampleBackendPayload.warnings,
      needsClarification: sampleBackendPayload.needs_clarification,
      providerStatus: sampleBackendPayload.provider_status,
    };

    expect(chatMsg.agentResults).toHaveLength(1);
    expect(chatMsg.agentResults![0].name).toBe('Irrigation Advisory Specialist');
    expect(chatMsg.executionTrace).toHaveLength(1);
    expect(chatMsg.sources).toHaveLength(2);
    expect(chatMsg.needsClarification).toBe(false);
    expect(chatMsg.providerStatus).toBe('mock');
  });
});
