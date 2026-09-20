import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../test/utils';
import { successResponse } from '../test/fixtures';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, analyzeRaster: vi.fn(), getSession: vi.fn() };
});

import { analyzeRaster } from '../services/api';
import { useSatQuery } from './SatQueryContext';

// A recognisable TIFF header (little-endian "II*\0"), so the assertion can tell real raster
// bytes from the 26-byte placeholder blob the demo path falls back to.
const TIFF_BYTES = new Uint8Array([0x49, 0x49, 0x2a, 0x00, ...new Array(2048).fill(7)]);

function Controls({ id }: { id: string }) {
  const { loadScenario, startAnalysis } = useSatQuery();
  return (
    <>
      <button onClick={() => loadScenario(id)}>load</button>
      <button onClick={() => startAnalysis()}>start</button>
    </>
  );
}

describe('demo scenarios upload their georeferenced rasters', () => {
  beforeEach(() => {
    vi.mocked(analyzeRaster).mockReset();
    vi.mocked(analyzeRaster).mockResolvedValue(successResponse);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, blob: async () => new Blob([TIFF_BYTES]) })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends the fetched GeoTIFF bytes under the scenario file names', async () => {
    renderWithProviders(<Controls id="scenario_d" />);
    // Separate clicks so startAnalysis renders against the state loadScenario set.
    fireEvent.click(screen.getByText('load'));
    fireEvent.click(screen.getByText('start'));

    await waitFor(() => expect(analyzeRaster).toHaveBeenCalled(), { timeout: 5000 });

    const files = vi.mocked(analyzeRaster).mock.calls[0][1] as File[];
    expect(files.map((f) => f.name)).toEqual([
      'Sentinel2_RGBNIR_Assam.tif',
      'Sentinel1_SAR_Assam_C_Band.tif',
    ]);
    for (const file of files) {
      expect(file.type).toBe('image/tiff');
      expect(file.size).toBe(TIFF_BYTES.byteLength);
    }
    expect(fetch).toHaveBeenCalledWith('/demo/Sentinel2_RGBNIR_Assam.tif');
    expect(fetch).toHaveBeenCalledWith('/demo/Sentinel1_SAR_Assam_C_Band.tif');
  });
});
