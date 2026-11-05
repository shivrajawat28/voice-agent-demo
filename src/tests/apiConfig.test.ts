/**
 * Unit Tests for Centralized API & WebSocket URL Configuration
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { getApiBaseUrl, getApiUrl, getWebSocketUrl } from '../config/api';

describe('API and WebSocket URL Configuration', () => {
  const originalEnv = { ...import.meta.env };

  beforeEach(() => {
    // Reset env vars before each test
    (import.meta.env as any).VITE_API_BASE_URL = undefined;
    (import.meta.env as any).VITE_WS_URL = undefined;
  });

  afterEach(() => {
    // Restore original env
    (import.meta.env as any).VITE_API_BASE_URL = originalEnv.VITE_API_BASE_URL;
    (import.meta.env as any).VITE_WS_URL = originalEnv.VITE_WS_URL;
  });

  describe('getApiBaseUrl', () => {
    it('returns empty string when VITE_API_BASE_URL is undefined', () => {
      expect(getApiBaseUrl()).toBe('');
    });

    it('returns empty string when VITE_API_BASE_URL is empty or whitespace', () => {
      (import.meta.env as any).VITE_API_BASE_URL = '   ';
      expect(getApiBaseUrl()).toBe('');
    });

    it('strips trailing slashes from VITE_API_BASE_URL', () => {
      (import.meta.env as any).VITE_API_BASE_URL = 'https://fertobot-backend.a.run.app///';
      expect(getApiBaseUrl()).toBe('https://fertobot-backend.a.run.app');
    });

    it('trims leading/trailing whitespace from VITE_API_BASE_URL', () => {
      (import.meta.env as any).VITE_API_BASE_URL = '  https://api.fertobot.com  ';
      expect(getApiBaseUrl()).toBe('https://api.fertobot.com');
    });
  });

  describe('getApiUrl', () => {
    it('returns relative path when VITE_API_BASE_URL is not set', () => {
      expect(getApiUrl('/api/chat')).toBe('/api/chat');
      expect(getApiUrl('api/config')).toBe('/api/config');
    });

    it('concatenates VITE_API_BASE_URL and path without duplicate slashes', () => {
      (import.meta.env as any).VITE_API_BASE_URL = 'https://fertobot-backend.a.run.app/';
      expect(getApiUrl('/api/chat')).toBe('https://fertobot-backend.a.run.app/api/chat');
      expect(getApiUrl('api/tts')).toBe('https://fertobot-backend.a.run.app/api/tts');
    });

    it('handles query parameters correctly', () => {
      (import.meta.env as any).VITE_API_BASE_URL = 'https://fertobot-backend.a.run.app';
      expect(getApiUrl('/api/provider/llm?provider=gemini')).toBe(
        'https://fertobot-backend.a.run.app/api/provider/llm?provider=gemini'
      );
    });
  });

  describe('getWebSocketUrl', () => {
    it('uses explicit VITE_WS_URL when provided', () => {
      (import.meta.env as any).VITE_WS_URL = 'wss://custom-ws.fertobot.com/api/ws/stt';
      expect(getWebSocketUrl('/api/ws/stt')).toBe('wss://custom-ws.fertobot.com/api/ws/stt');
    });

    it('derives WSS URL from HTTPS VITE_API_BASE_URL when VITE_WS_URL is not set', () => {
      (import.meta.env as any).VITE_API_BASE_URL = 'https://fertobot-backend.a.run.app';
      expect(getWebSocketUrl('/api/ws/stt')).toBe('wss://fertobot-backend.a.run.app/api/ws/stt');
    });

    it('derives WS URL from HTTP VITE_API_BASE_URL when VITE_WS_URL is not set', () => {
      (import.meta.env as any).VITE_API_BASE_URL = 'http://127.0.0.1:8000/';
      expect(getWebSocketUrl('/api/ws/stt')).toBe('ws://127.0.0.1:8000/api/ws/stt');
    });

    it('falls back to window.location when neither env var is provided', () => {
      // In Node environment window may be mocked or undefined
      const wsUrl = getWebSocketUrl('/api/ws/stt');
      expect(wsUrl).toMatch(/^wss?:\/\/.+\/api\/ws\/stt$/);
    });

    it('normalizes path without leading slash', () => {
      (import.meta.env as any).VITE_API_BASE_URL = 'https://backend.example.com';
      expect(getWebSocketUrl('api/ws/stt')).toBe('wss://backend.example.com/api/ws/stt');
    });
  });
});
