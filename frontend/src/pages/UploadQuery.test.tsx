import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '../test/utils';
import { UploadQuery } from './UploadQuery';
import { AnalyzeButton } from '../components/AnalyzeButton';
import { useSatQuery } from '../context/SatQueryContext';

describe('UploadQuery page', () => {
  it('renders the studio with its uploader, query box and demo scenarios', () => {
    renderWithProviders(<UploadQuery />, { route: '/analyze' });

    expect(screen.getByText(/Analysis Studio/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Agentic Analysis/i })).toBeInTheDocument();
  });

  it('offers the problem statement representative queries as examples', () => {
    renderWithProviders(<UploadQuery />, { route: '/analyze' });

    // The default scenario also seeds the first query, so it appears more than once.
    expect(
      screen.getAllByText('Describe the land-cover and major objects visible in this image.').length
    ).toBeGreaterThan(0);
    expect(
      screen.getByText('What changed between these two dates, and where did the change occur?')
    ).toBeInTheDocument();
  });
});

/** Drives the submit gate directly: no image or no query means no analysis. */
function GateHarness({ image, query }: { image: boolean; query: string }) {
  const { setImage1, setQuery, image1 } = useSatQuery();

  if (!image && image1) setImage1(null);
  if (query !== undefined) {
    // Seed once; setQuery is idempotent for the same value.
    setQuery(query);
  }

  return <AnalyzeButton />;
}

describe('Analyze submit gate', () => {
  it('is disabled with a query but no image', async () => {
    renderWithProviders(<GateHarness image={false} query="count the tanks" />);
    expect(screen.getByRole('button', { name: /Run Agentic Analysis/i })).toBeDisabled();
  });

  it('is disabled with an image but an empty query', () => {
    renderWithProviders(<GateHarness image query="   " />);
    expect(screen.getByRole('button', { name: /Run Agentic Analysis/i })).toBeDisabled();
  });

  it('is enabled once an image and a non-empty query are both present', () => {
    // The provider seeds scenario one's image by default, so only the query is needed.
    renderWithProviders(<GateHarness image query="count the fuel storage tanks" />);
    expect(screen.getByRole('button', { name: /Run Agentic Analysis/i })).toBeEnabled();
  });

  it('does not submit while disabled', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GateHarness image={false} query="count the tanks" />);

    const button = screen.getByRole('button', { name: /Run Agentic Analysis/i });
    await user.click(button);
    expect(button).toBeDisabled();
  });
});
