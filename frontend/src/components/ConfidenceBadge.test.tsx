import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ConfidenceBadge } from './ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it.each([
    ['High', 'emerald-success'],
    ['Medium', 'amber-warning'],
    ['Low', 'rose-danger'],
  ] as const)('renders %s with its own colour, not a shared one', (tier, token) => {
    const { container } = render(
      <ConfidenceBadge tier={tier} rationale={`${tier} rationale text.`} />
    );

    expect(screen.getByText(`${tier.toUpperCase()} CONFIDENCE`)).toBeInTheDocument();
    expect(container.innerHTML).toContain(token);
  });

  it('shows the rationale, which is a judge-facing artifact and must not be hidden', () => {
    render(
      <ConfidenceBadge
        tier="Low"
        rationale="Quantity discrepancy flagged: Text claims 5 targets but 3 features localized."
      />
    );

    expect(
      screen.getByText(/Text claims 5 targets but 3 features localized/)
    ).toBeInTheDocument();
  });

  it('renders the verifier checklist from the details block', () => {
    render(
      <ConfidenceBadge
        tier="Low"
        rationale="Geometry failed."
        details={{ geometryCheck: false, crossToolAgreement: true, quantityDiscrepancy: true }}
      />
    );

    expect(screen.getByText(/FAILED/)).toBeInTheDocument();
    expect(screen.getByText(/HIGH/)).toBeInTheDocument();
  });

  it('survives details: null, which is what a rejection response carries', () => {
    // Same class of bug as EvidenceViewer: a default parameter fills undefined,
    // never null, so reading details.geometryCheck threw.
    expect(() =>
      render(<ConfidenceBadge tier="Low" rationale="Precondition failed." details={null} />)
    ).not.toThrow();

    expect(screen.getByText('LOW CONFIDENCE')).toBeInTheDocument();
  });
});
