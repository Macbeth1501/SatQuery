import { afterEach, describe, expect, it, vi } from 'vitest';

async function loadApi() {
  vi.resetModules();
  return import('./api');
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('API base URL', () => {
  it('defaults to a locally running backend', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '');
    const { API_BASE } = await loadApi();
    expect(API_BASE).toBe('http://127.0.0.1:8000');
  });

  it('is taken from VITE_API_BASE_URL', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.org');
    const { API_BASE } = await loadApi();
    expect(API_BASE).toBe('https://api.example.org');
  });

  it('strips trailing slashes so callers can append a leading-slash path', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.org///');
    const { API_BASE, resolveAssetUrl } = await loadApi();
    expect(API_BASE).toBe('https://api.example.org');
    expect(resolveAssetUrl('/storage/a.png')).toBe('https://api.example.org/storage/a.png');
  });
});

describe('resolveAssetUrl', () => {
  it('leaves data, blob and absolute URLs untouched', async () => {
    const { resolveAssetUrl } = await loadApi();
    expect(resolveAssetUrl('data:image/svg+xml;utf8,<svg/>')).toBe('data:image/svg+xml;utf8,<svg/>');
    expect(resolveAssetUrl('blob:http://x/abc')).toBe('blob:http://x/abc');
    expect(resolveAssetUrl('https://cdn.example/a.png')).toBe('https://cdn.example/a.png');
  });

  it('sends only backend paths to the API and keeps the frontend’s own assets same-origin', async () => {
    const { API_BASE, resolveAssetUrl } = await loadApi();
    expect(resolveAssetUrl('/storage/sessions/sq-1/evidence/o.png')).toBe(`${API_BASE}/storage/sessions/sq-1/evidence/o.png`);
    expect(resolveAssetUrl('/v1/session/sq-1/report?format=pdf')).toBe(`${API_BASE}/v1/session/sq-1/report?format=pdf`);
    // The live-model sample image is served by Vite, not the API; prefixing it gave a 404 (seen in a browser).
    expect(resolveAssetUrl('/real/bigearthnet_T29UPU_55_58.png')).toBe('/real/bigearthnet_T29UPU_55_58.png');
  });

  it('returns an empty string for a missing URL', async () => {
    const { resolveAssetUrl } = await loadApi();
    expect(resolveAssetUrl(null)).toBe('');
    expect(resolveAssetUrl(undefined)).toBe('');
  });
});
