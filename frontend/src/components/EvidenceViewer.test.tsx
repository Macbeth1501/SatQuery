import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EvidenceViewer } from './EvidenceViewer';
import { fusionResponse, successResponse } from '../test/fixtures';

const { boxes } = successResponse.evidence;

describe('EvidenceViewer', () => {
  it('renders when the API sends null for regionTags and masks', () => {
    // Regression: the backend sends null (not undefined) for every non-fusion task.
    // A default parameter only fills undefined, so `regionTags.length` threw and took
    // the whole Results page down on every live single-image analysis.
    expect(() =>
      render(
        <EvidenceViewer
          primaryImageUrl="data:image/png;base64,iVBORw0KGgo="
          boxes={boxes}
          masks={null}
          regionTags={null}
        />
      )
    ).not.toThrow();

    expect(screen.getByText(/Bounding Boxes \(3\)/i)).toBeInTheDocument();
  });

  it('renders every grounding candidate rather than a silent top-1', () => {
    render(
      <EvidenceViewer
        primaryImageUrl="data:image/png;base64,iVBORw0KGgo="
        boxes={boxes}
        regionTags={null}
      />
    );

    for (const box of boxes) {
      expect(screen.getByText(box.label!)).toBeInTheDocument();
    }
  });

  it('distinguishes candidates by score rather than styling them identically', () => {
    const { container } = render(
      <EvidenceViewer
        primaryImageUrl="data:image/png;base64,iVBORw0KGgo="
        boxes={boxes}
        regionTags={null}
      />
    );

    // Each box carries its score, so a reviewer can tell the 0.96 candidate from
    // the 0.41 one without reading the JSON.
    expect(screen.getByText('96%')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
    expect(screen.getByText('41%')).toBeInTheDocument();
    expect(container.querySelectorAll('[style*="border"]').length).toBeGreaterThan(0);
  });

  it('shows sensor complementarity tags only when the task produced them', () => {
    const { rerender } = render(
      <EvidenceViewer
        primaryImageUrl="data:image/png;base64,iVBORw0KGgo="
        boxes={boxes}
        regionTags={null}
      />
    );
    expect(screen.queryByText(/Sensor Tags/i)).not.toBeInTheDocument();

    rerender(
      <EvidenceViewer
        primaryImageUrl="data:image/png;base64,iVBORw0KGgo="
        boxes={boxes}
        regionTags={fusionResponse.evidence.regionTags}
      />
    );
    expect(screen.getByText(/Sensor Tags \(3\)/i)).toBeInTheDocument();
  });

  it('resolves backend-relative overlay paths against the API, not the dev server', () => {
    render(
      <EvidenceViewer
        primaryImageUrl="/storage/sessions/sq-test0001/inputs/image_1_scene.png"
        boxes={[]}
        regionTags={null}
      />
    );

    const img = document.querySelector('img');
    expect(img?.getAttribute('src')).toBe(
      'http://127.0.0.1:8000/storage/sessions/sq-test0001/inputs/image_1_scene.png'
    );
  });
});
