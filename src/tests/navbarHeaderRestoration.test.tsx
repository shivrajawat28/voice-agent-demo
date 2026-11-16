/**
 * Unit Tests for Standalone AI Agronomist-Only Interface Header
 * Verifies isolation of AI Agronomist experience and removal of unrelated dashboard modules.
 */
import { describe, it, expect, vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { Navbar } from '../components/Navbar';

describe('AI Agronomist-Only Interface Header', () => {
  it('renders FertoBot branding and AI Agronomist identity', () => {
    const html = renderToString(<Navbar />);

    expect(html).toContain('Ferto');
    expect(html).toContain('Bot');
    expect(html).toContain('AI Agronomist');
    expect(html).toContain('कृषि मित्र');
    expect(html).toContain('Autonomous Multi-Agent Indic Voice Assistant');
  });

  it('renders safety status and telemetry channels', () => {
    const html = renderToString(
      <Navbar llmProvider="gemini" gnaniConfigured={true} selectedVoice="Nalini" />
    );

    expect(html).toContain('SIMULATED HARDWARE DEMO (ACTUATION LOCKED)');
    expect(html).toContain('Soil Telemetry:');
    expect(html).toContain('7 Channels Active');
    expect(html).toContain('GEMINI Multi-Agent');
    expect(html).toContain('GNANI Indic Voice (Nalini) Live');
    expect(html).toContain('Safe Autonomous Advisory');
  });

  it('strictly excludes all unrelated dashboard navigation items', () => {
    const html = renderToString(<Navbar />);

    // Unrelated dashboard modules must NOT be present
    expect(html).not.toContain('Dashboard (Active Experience)');
    expect(html).not.toContain('Farm Settings');
    expect(html).not.toContain('Feature Studio');
    expect(html).not.toContain('Reports');
    expect(html).not.toContain('Security');
    expect(html).not.toContain('Probes');
    expect(html).not.toContain('Irrigation');
    expect(html).not.toContain('Plots');
  });

  it('strictly excludes unrelated dashboard simulation triggers and profile pill', () => {
    const html = renderToString(<Navbar />);

    expect(html).not.toContain('+ Rain');
    expect(html).not.toContain('- NPK');
    expect(html).not.toContain('! Intruder');
    expect(html).not.toContain('Prince AgriTech Hub');
    expect(html).not.toContain('Sign Out');
    expect(html).not.toContain('5 NODES ONLINE (DEMO)');
  });

  it('renders Target Zone selector with 4 zones', () => {
    const onZoneChange = vi.fn();
    const html = renderToString(
      <Navbar activeZoneId="DEMO-ZONE-001" onZoneChange={onZoneChange} />
    );

    expect(html).toContain('Target:');
    expect(html).toContain('Zone 1: Wheat (गेहूं)');
    expect(html).toContain('Zone 2: Cotton (कपास)');
    expect(html).toContain('Zone 3: Tomato (टमाटर)');
    expect(html).toContain('Zone 4: Mustard (सरसों)');
  });

  it('renders repeat response and clear chat controls', () => {
    const onRepeat = vi.fn();
    const onClear = vi.fn();
    const html = renderToString(
      <Navbar onRepeatResponse={onRepeat} onClearTranscript={onClear} hasMessages={true} />
    );

    expect(html).toContain('पुनः सुनें');
    expect(html).toContain('साफ़ करें');
  });

  it('renders language selector with Hindi, Hinglish, and English options', () => {
    const html = renderToString(<Navbar currentLanguage="hi-IN" />);

    expect(html).toContain('हिन्दी');
    expect(html).toContain('Hinglish');
    expect(html).toContain('English (India)');
    expect(html).toContain('English (US)');
  });
});
