import { screen } from '@testing-library/react';
import { renderWithProviders as render } from '../test/utils';
import { describe, expect, it } from 'vitest';

import { RejectionState } from './RejectionState';
import { ExecutionTrace } from './ExecutionTrace';
import { modalityMismatch, rejectedResponse } from '../test/fixtures';

describe('RejectionState', () => {
  it('renders the reason verbatim, never paraphrased or truncated', () => {
    render(<RejectionState rejection={modalityMismatch} />);
    expect(screen.getByText(modalityMismatch.humanReadableReason)).toBeInTheDocument();
  });

  it('shows the reason code and the corrective action', () => {
    render(<RejectionState rejection={modalityMismatch} />);

    expect(screen.getByText(/MODALITY_MISMATCH/)).toBeInTheDocument();
    expect(screen.getByText(modalityMismatch.suggestedAction!)).toBeInTheDocument();
  });

  it('shows what was detected against what was required', () => {
    render(<RejectionState rejection={modalityMismatch} />);

    // Both modalities appear, in the detected-context rows as well as the prose.
    expect(screen.getAllByText(/optical/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/sar/i).length).toBeGreaterThan(0);
    expect(screen.getByText('optical+optical, sar+sar')).toBeInTheDocument();
  });
});

describe('RejectionState actions', () => {
  it('offers the fusion shortcut for a modality mismatch', () => {
    render(<RejectionState rejection={modalityMismatch} />);
    expect(screen.getByText('Switch to Optical-SAR Fusion Query')).toBeInTheDocument();
  });

  it.each(['ambiguous_intent', 'crs_mismatch_unresolvable', 'unsupported_format'] as const)(
    'does not offer the fusion shortcut for %s',
    (reasonCode) => {
      render(<RejectionState rejection={{ ...modalityMismatch, reasonCode }} />);
      expect(screen.queryByText('Switch to Optical-SAR Fusion Query')).not.toBeInTheDocument();
    },
  );

  it('frames an ambiguous query as needing clarification, not as a bad input', () => {
    render(<RejectionState rejection={{ ...modalityMismatch, reasonCode: 'ambiguous_intent' }} />);
    expect(screen.getByText('Query Needs Clarification')).toBeInTheDocument();
    expect(screen.queryByText('Physical Input Precondition Rejection')).not.toBeInTheDocument();
    expect(screen.getByText('Rephrase Query')).toBeInTheDocument();
  });
});

describe('ExecutionTrace on a rejected session', () => {
  it('still renders a trace — a rejection is audited, not silent', () => {
    render(<ExecutionTrace trace={rejectedResponse.executionTrace} defaultExpanded />);

    // The steps that did run are shown rather than hidden, per the trace-emitter
    // contract: query interpretation succeeded before the validator rejected.
    expect(screen.getByText('QueryInterpreter')).toBeInTheDocument();
    expect(screen.getByText(/Parsed natural language query/)).toBeInTheDocument();
  });

  it('reports the task it resolved before halting', () => {
    render(<ExecutionTrace trace={rejectedResponse.executionTrace} defaultExpanded />);
    expect(screen.getByText(/1 Steps|1 Step/i)).toBeInTheDocument();
  });
});
