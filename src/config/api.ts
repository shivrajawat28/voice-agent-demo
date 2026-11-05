/**
 * Centralized API & WebSocket Configuration
 *
 * Resolves API and WebSocket URLs across environments:
 * 1. Local development (Vite proxy to http://127.0.0.1:8000)
 * 2. Monolithic Render deployment (same-origin relative paths)
 * 3. Decoupled Vercel frontend + Google Cloud Run backend deployment
 *
 * Environment variables:
 * - VITE_API_BASE_URL: Base HTTP(S) URL for backend REST endpoints (e.g. "https://api.example.com")
 * - VITE_WS_URL: Direct WSS/WS endpoint for real-time STT audio streaming (e.g. "wss://api.example.com/api/ws/stt")
 *
 * SECURITY INVARIANT:
 * Frontend VITE_* environment variables are embedded in public client bundles.
 * NEVER expose backend API keys (GEMINI_API_KEY, GNANI_API_KEY) in client variables.
 */

function sanitizeEnvValue(val: unknown): string | undefined {
  if (typeof val !== 'string') return undefined;
  const trimmed = val.trim();
  if (trimmed === '' || trimmed === 'undefined' || trimmed === 'null') {
    return undefined;
  }
  return trimmed;
}

/**
 * Returns the sanitized base API URL, stripping any trailing slashes.
 * Returns empty string ("") if unconfigured, preserving relative paths.
 */
export function getApiBaseUrl(): string {
  let raw: unknown;
  try {
    raw = import.meta?.env?.VITE_API_BASE_URL;
  } catch {
    raw = undefined;
  }

  const clean = sanitizeEnvValue(raw);
  if (clean) {
    return clean.replace(/\/+$/, '');
  }

  return '';
}

/**
 * Resolves a full REST API endpoint URL.
 * Automatically handles leading/trailing slashes to prevent malformed URLs.
 *
 * @param path Relative path, e.g. "/api/chat" or "api/config"
 * @returns Fully-qualified URL if VITE_API_BASE_URL is set, otherwise relative path
 */
export function getApiUrl(path: string): string {
  const baseUrl = getApiBaseUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  if (!baseUrl) {
    return cleanPath;
  }

  return `${baseUrl}${cleanPath}`;
}

/**
 * Resolves the WebSocket URL for real-time STT streaming.
 *
 * Resolution precedence:
 * 1. Explicit VITE_WS_URL environment variable
 * 2. Derived from VITE_API_BASE_URL (http -> ws, https -> wss)
 * 3. Fallback to browser window.location (preserving local dev proxy and Render same-origin)
 * 4. Fallback to localhost:8000 for non-browser/test environments
 *
 * @param path WebSocket path, default "/api/ws/stt"
 * @returns Full WebSocket URL (e.g. "wss://backend.run.app/api/ws/stt")
 */
export function getWebSocketUrl(path: string = '/api/ws/stt'): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  // 1. Explicit VITE_WS_URL
  let rawWs: unknown;
  try {
    rawWs = import.meta?.env?.VITE_WS_URL;
  } catch {
    rawWs = undefined;
  }

  const cleanWs = sanitizeEnvValue(rawWs);
  if (cleanWs) {
    return cleanWs.replace(/\/+$/, '');
  }

  // 2. Derived from VITE_API_BASE_URL
  const apiBase = getApiBaseUrl();
  if (apiBase) {
    try {
      const parsed = new URL(apiBase);
      const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${parsed.host}${cleanPath}`;
    } catch {
      const wsBase = apiBase
        .replace(/^https:\/\//i, 'wss://')
        .replace(/^http:\/\//i, 'ws://');
      return `${wsBase}${cleanPath}`;
    }
  }

  // 3. Fallback to browser window.location
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    if (host && host !== 'undefined' && host !== 'null') {
      return `${protocol}//${host}${cleanPath}`;
    }
  }

  // 4. Default for Node/SSR/testing
  return `ws://127.0.0.1:8000${cleanPath}`;
}
