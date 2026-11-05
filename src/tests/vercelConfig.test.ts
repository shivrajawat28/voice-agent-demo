/**
 * Unit Tests for Vercel Deployment Configuration (vercel.json)
 */
import { describe, it, expect } from 'vitest';
import vercelConfig from '../../vercel.json';

describe('Vercel Configuration Verification', () => {
  it('vercel.json is successfully loaded as valid JSON module', () => {
    expect(vercelConfig).toBeDefined();
    expect(typeof vercelConfig).toBe('object');
  });

  it('configures framework as vite and output directory as dist', () => {
    expect(vercelConfig.framework).toBe('vite');
    expect(vercelConfig.outputDirectory).toBe('dist');
    expect(vercelConfig.buildCommand).toBe('npm run build');
  });

  it('configures SPA catch-all rewrite to index.html without proxy rewrites', () => {
    expect(Array.isArray(vercelConfig.rewrites)).toBe(true);
    expect(vercelConfig.rewrites.length).toBe(1);
    expect(vercelConfig.rewrites[0].source).toBe('/(.*)');
    expect(vercelConfig.rewrites[0].destination).toBe('/index.html');
  });

  it('configures necessary production security headers', () => {
    expect(Array.isArray(vercelConfig.headers)).toBe(true);
    expect(vercelConfig.headers.length).toBeGreaterThan(0);

    const globalHeaders = vercelConfig.headers.find((h: { source: string }) => h.source === '/(.*)');
    expect(globalHeaders).toBeDefined();

    const headerKeys = globalHeaders?.headers.map((h: { key: string }) => h.key) ?? [];
    expect(headerKeys).toContain('X-Content-Type-Options');
    expect(headerKeys).toContain('X-Frame-Options');
    expect(headerKeys).toContain('X-XSS-Protection');
    expect(headerKeys).toContain('Referrer-Policy');
  });

  it('does not contain hardcoded backend URLs or credentials in vercel.json', () => {
    const serialized = JSON.stringify(vercelConfig);
    expect(serialized).not.toContain('onrender.com');
    expect(serialized).not.toContain('API_KEY');
    expect(serialized).not.toContain('secret');
  });
});
