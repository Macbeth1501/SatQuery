import React from 'react';
import { Radio, WifiOff } from 'lucide-react';
import type { ResultSource } from '../context/SatQueryContext';

interface ResultSourceBadgeProps {
  source: ResultSource | null;
}

/**
 * States plainly whether the displayed answer came from the backend or from the
 * bundled demo scenario.
 *
 * The client falls back to a demo scenario whenever the API call fails, which keeps
 * a live presentation running but otherwise leaves the two cases visually identical
 * -- a result that looks analysed but was never computed. This badge is what makes
 * them distinguishable.
 */
export const ResultSourceBadge: React.FC<ResultSourceBadgeProps> = ({ source }) => {
  if (!source) return null;

  const isLive = source === 'live';
  const Icon = isLive ? Radio : WifiOff;

  return (
    <span
      className={isLive ? 'badge badge-emerald' : 'badge badge-amber'}
      title={
        isLive
          ? 'Computed by the SatQuery AI backend for this request.'
          : 'The backend could not be reached, so a bundled demo scenario is being shown. These results were not computed from your input.'
      }
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        whiteSpace: 'nowrap',
      }}
    >
      <Icon size={12} />
      <span>{isLive ? 'Live Backend' : 'Demo Data — Backend Unreachable'}</span>
    </span>
  );
};
