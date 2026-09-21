import type { AnalyzeResponse, InspectResponse } from '../types/satquery';

/**
 * Base URL of the SatQuery API. Set VITE_API_BASE_URL at build or dev time to point
 * at a deployed backend; the default targets a locally running one. A trailing slash
 * is stripped so callers can always append a path that starts with one.
 */
export const API_BASE: string = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

/** Resolves a backend-relative asset path (/storage/... or /v1/...) to an absolute URL.
 *  Data URIs, absolute URLs and the frontend's own static assets (e.g. /real/..., served by
 *  this origin, not the API) are returned untouched. */
export function resolveAssetUrl(url: string | undefined | null): string {
  if (!url) return '';
  if (/^(https?:|data:|blob:)/.test(url)) return url;
  if (!/^\/?(storage|v1)\//.test(url)) return url;
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
}

export async function analyzeRaster(
  query: string,
  files: File[] = [],
  sessionOptions?: Record<string, unknown>
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append('query', query);

  for (const file of files) {
    formData.append('files', file);
  }

  if (sessionOptions) {
    formData.append('session_options', JSON.stringify(sessionOptions));
  }

  const response = await fetch(`${API_BASE}/v1/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`API error (${response.status}): ${errText}`);
  }

  return response.json();
}

/** Reads one file's real metadata and a displayable preview, without running an analysis. */
export async function inspectRaster(file: File): Promise<InspectResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/v1/inspect`, { method: 'POST', body: formData });
  if (!response.ok) {
    throw new Error(`API error (${response.status}): ${await response.text()}`);
  }
  return response.json();
}

/** Thrown when the backend has no session with the requested id (HTTP 404). */
export class SessionNotFoundError extends Error {
  constructor(sessionId: string) {
    super(`Session '${sessionId}' was not found.`);
    this.name = 'SessionNotFoundError';
  }
}

export async function getSession(sessionId: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE}/v1/session/${encodeURIComponent(sessionId)}`);
  if (response.status === 404) {
    throw new SessionNotFoundError(sessionId);
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch session (${response.status})`);
  }
  return response.json();
}

export async function getHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE}/v1/health`);
  return response.json();
}

export async function getRegistry(): Promise<unknown> {
  const response = await fetch(`${API_BASE}/v1/registry`);
  return response.json();
}
