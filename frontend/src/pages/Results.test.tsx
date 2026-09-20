import { useEffect } from 'react';
import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../test/utils';
import { Results } from './Results';
import { fusionResponse, rejectedResponse, successResponse } from '../test/fixtures';
import type { AnalyzeResponse } from '../types/satquery';

// The page reads its result from context, so drive the context's own API call.
vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, analyzeRaster: vi.fn(), getSession: vi.fn() };
});

import { analyzeRaster, getSession, SessionNotFoundError } from '../services/api';
import { useSatQuery } from '../context/SatQueryContext';

/** Renders Results with a given response already seeded into context. */
function renderWithResult(response: AnalyzeResponse) {
  const Harness = () => {
    const { setResults } = useSatQuery();
    useEffect(() => {
      setResults(response);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return <Results />;
  };
  return renderWithProviders(<Harness />, { route: '/results' });
}

describe('Results page', () => {
  beforeEach(() => {
    vi.mocked(analyzeRaster).mockReset();
  });

  it('shows an empty state when no analysis has run', () => {
    renderWithProviders(<Results />, { route: '/results' });
    expect(screen.getByText(/No Active Analysis Results/i)).toBeInTheDocument();
  });

  it('renders the success branch without crashing on regionTags: null', () => {
    // This is the exact shape that took the page down: a live single-image
    // response, where the backend sends regionTags: null.
    renderWithResult(successResponse);

    expect(screen.getByText(/Analysis Results & Evidence/i)).toBeInTheDocument();
    expect(screen.getByText(successResponse.answerText!)).toBeInTheDocument();
    expect(screen.getByText('HIGH CONFIDENCE')).toBeInTheDocument();
    expect(screen.queryByText(/No Active Analysis Results/i)).not.toBeInTheDocument();
  });

  it('renders the rejection branch instead of the answer panel', () => {
    renderWithResult(rejectedResponse);

    expect(screen.getByText(rejectedResponse.rejectionDetails!.humanReadableReason)).toBeInTheDocument();
    expect(screen.getByText(/Input Precondition Failed/i)).toBeInTheDocument();
    // No answer panel on a rejection.
    expect(screen.queryByText(/Grounded Remote-Sensing Response/i)).not.toBeInTheDocument();
  });

  it('renders sensor complementarity tags on a fusion result', () => {
    renderWithResult(fusionResponse);
    expect(screen.getByText(/Sensor Tags \(3\)/i)).toBeInTheDocument();
  });
});

describe('Results page: direct session reopen (A8)', () => {
  const renderAt = (route: string) =>
    renderWithProviders(
      <Routes>
        <Route path="/results/:sessionId" element={<Results />} />
        <Route path="/results" element={<Results />} />
      </Routes>,
      { route }
    );

  beforeEach(() => {
    vi.mocked(getSession).mockReset();
  });

  it('fetches the session from the URL and renders it', async () => {
    vi.mocked(getSession).mockResolvedValue({ ...successResponse, sessionId: 'sq-abc12345' });
    renderAt('/results/sq-abc12345');
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(await screen.findByText(successResponse.answerText as string)).toBeInTheDocument();
    expect(getSession).toHaveBeenCalledWith('sq-abc12345');
  });

  it('renders a rejected stored session through the rejection view', async () => {
    vi.mocked(getSession).mockResolvedValue({ ...rejectedResponse, sessionId: 'sq-rej00001' });
    renderAt('/results/sq-rej00001');
    expect(await screen.findByText(/Input Precondition Failed/i)).toBeInTheDocument();
  });

  it('shows a distinct not-found state on 404', async () => {
    vi.mocked(getSession).mockRejectedValue(new SessionNotFoundError('sq-nope0000'));
    renderAt('/results/sq-nope0000');
    expect(await screen.findByText(/Session Not Found/i)).toBeInTheDocument();
    expect(screen.queryByText(/No Active Analysis Results/i)).not.toBeInTheDocument();
  });

  it('shows a load-error state, not not-found, when the backend is unreachable', async () => {
    vi.mocked(getSession).mockRejectedValue(new Error('network down'));
    renderAt('/results/sq-abc12345');
    expect(await screen.findByText(/Could Not Load Session/i)).toBeInTheDocument();
    expect(screen.queryByText(/Session Not Found/i)).not.toBeInTheDocument();
  });

  it('does not fetch on plain /results', () => {
    renderAt('/results');
    expect(getSession).not.toHaveBeenCalled();
    expect(screen.getByText(/No Active Analysis Results/i)).toBeInTheDocument();
  });
});
