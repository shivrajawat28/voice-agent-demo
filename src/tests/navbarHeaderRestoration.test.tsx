/**
 * Unit Tests for Restored Original FertoBot Website Header & Navigation
 * Phase 33.5 Verification
 */
import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { Navbar } from '../components/Navbar';

describe('Phase 33.5: Restored Original FertoBot Header & Navigation', () => {
  it('renders original FertoBot branding and farm name', () => {
    const html = renderToString(<Navbar />);

    expect(html).toContain('Ferto');
    expect(html).toContain('Bot');
    expect(html).toContain('Prince AgriTech Hub');
  });

  it('renders top status bar with node count, health score, and weather location', () => {
    const html = renderToString(
      <Navbar healthScore={88} weatherLocation="Varanasi, Uttar Pradesh" weatherTemp="25°C" />
    );

    expect(html).toContain('5 NODES ONLINE');
    expect(html).toContain('Health:');
    expect(html).toContain('88');
    expect(html).toContain('Varanasi, Uttar Pradesh');
    expect(html).toContain('25°C');
  });

  it('renders all original navigation items including Dashboard, Plots, and Agronomist', () => {
    const html = renderToString(<Navbar />);

    // Check all verified navigation tabs from original FertoBot website
    expect(html).toContain('Dashboard');
    expect(html).toContain('Plots');
    expect(html).toContain('Irrigation');
    expect(html).toContain('Probes');
    expect(html).toContain('Security');
    expect(html).toContain('Agronomist');
    expect(html).toContain('Reports');
    expect(html).toContain('Feature Studio');
    expect(html).toContain('Farm Settings');
  });

  it('highlights Agronomist as the active experience tab with emerald styling', () => {
    const html = renderToString(<Navbar />);

    expect(html).toContain('bg-emerald-600/15 text-emerald-400 font-semibold border border-emerald-500/30');
    expect(html).toContain('Agronomist (Active Experience)');
  });

  it('renders simulation controls strip (+ Rain, - NPK, ! Intruder, Reset)', () => {
    const html = renderToString(<Navbar />);

    expect(html).toContain('+ Rain');
    expect(html).toContain('- NPK');
    expect(html).toContain('! Intruder');
    expect(html).toContain('Simulate Rain Shower');
    expect(html).toContain('Simulate Nutrient Drop');
    expect(html).toContain('Simulate CCTV Motion');
    expect(html).toContain('Reset Simulation');
  });

  it('renders language selector with Hindi and English options', () => {
    const html = renderToString(<Navbar currentLanguage="hi-IN" />);

    expect(html).toContain('हिन्दी');
    expect(html).toContain('Hinglish');
    expect(html).toContain('EN');
  });

  it('renders user profile pill with name Prince and Sign Out action', () => {
    const html = renderToString(<Navbar />);

    expect(html).toContain('Prince');
    expect(html).toContain('Sign Out');
    expect(html).toContain('👨‍🌾');
  });
});
