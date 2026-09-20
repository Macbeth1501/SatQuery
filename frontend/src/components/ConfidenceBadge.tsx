import React, { useState } from 'react';
import type { ConfidenceTier } from '../types/satquery';
import { ShieldCheck, ShieldAlert, AlertTriangle, Check, X, HelpCircle } from 'lucide-react';

interface ConfidenceBadgeProps {
  tier: ConfidenceTier;
  rationale: string;
  details?: null | {
    geometryCheck: boolean;
    crossToolAgreement: boolean;
    quantityDiscrepancy: boolean;
  };
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  tier,
  rationale,
  details: detailsProp
}) => {
  // A rejection response carries details: null, and a default only fills undefined.
  const details = detailsProp ?? {
    geometryCheck: true,
    crossToolAgreement: true,
    quantityDiscrepancy: false,
  };

  const [showDetails, setShowDetails] = useState<boolean>(true);

  const tierColors = {
    High: {
      color: 'var(--emerald-success)',
      bg: 'rgba(16, 185, 129, 0.12)',
      border: 'rgba(16, 185, 129, 0.4)',
      icon: <ShieldCheck size={20} color="var(--emerald-success)" />
    },
    Medium: {
      color: 'var(--amber-warning)',
      bg: 'rgba(245, 158, 11, 0.12)',
      border: 'rgba(245, 158, 11, 0.4)',
      icon: <AlertTriangle size={20} color="var(--amber-warning)" />
    },
    Low: {
      color: 'var(--rose-danger)',
      bg: 'rgba(244, 63, 94, 0.12)',
      border: 'rgba(244, 63, 94, 0.4)',
      icon: <ShieldAlert size={20} color="var(--rose-danger)" />
    }
  };

  const current = tierColors[tier];

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: `1px solid ${current.border}`,
      borderRadius: 'var(--radius-md)',
      padding: '16px 20px',
      marginBottom: 20,
      boxShadow: 'var(--shadow-sm)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {current.icon}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Confidence Assessment
              </span>
              <span style={{
                fontSize: 12,
                fontWeight: 800,
                color: current.color,
                background: current.bg,
                padding: '2px 8px',
                borderRadius: 4,
                letterSpacing: '0.05em'
              }}>
                {tier.toUpperCase()} CONFIDENCE
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={() => setShowDetails(!showDetails)}
          style={{
            background: 'transparent',
            color: 'var(--text-muted)',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 4
          }}
        >
          <HelpCircle size={13} />
          {showDetails ? 'Hide Verification Audit' : 'Show Verification Audit'}
        </button>
      </div>

      {/* Rationale explanation */}
      <p style={{
        fontSize: 13,
        color: 'var(--text-primary)',
        lineHeight: 1.5,
        margin: '0 0 12px',
        padding: '8px 12px',
        background: 'var(--bg-elevated)',
        borderRadius: 6,
        borderLeft: `3px solid ${current.color}`
      }}>
        {rationale}
      </p>

      {/* Verifier Node Audit Checklist */}
      {showDetails && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 8,
          paddingTop: 8,
          borderTop: '1px solid var(--border-subtle)',
          fontSize: 11
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {details.geometryCheck ? (
              <Check size={14} color="var(--emerald-success)" />
            ) : (
              <X size={14} color="var(--rose-danger)" />
            )}
            <span style={{ color: details.geometryCheck ? 'var(--text-secondary)' : 'var(--rose-danger)' }}>
              Geometric Sanity: <strong>{details.geometryCheck ? 'PASSED' : 'FAILED'}</strong>
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {details.crossToolAgreement ? (
              <Check size={14} color="var(--emerald-success)" />
            ) : (
              <X size={14} color="var(--rose-danger)" />
            )}
            <span style={{ color: details.crossToolAgreement ? 'var(--text-secondary)' : 'var(--rose-danger)' }}>
              Cross-Tool Agreement: <strong>{details.crossToolAgreement ? 'HIGH' : 'LOW'}</strong>
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {!details.quantityDiscrepancy ? (
              <Check size={14} color="var(--emerald-success)" />
            ) : (
              <X size={14} color="var(--rose-danger)" />
            )}
            <span style={{ color: !details.quantityDiscrepancy ? 'var(--text-secondary)' : 'var(--rose-danger)' }}>
              Quantity Cross-Check: <strong>{!details.quantityDiscrepancy ? 'CONSISTENT' : 'DISCREPANCY'}</strong>
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
