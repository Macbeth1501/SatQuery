import React from 'react';
import type { RejectionInfo } from '../types/satquery';
import { ShieldAlert, ArrowRight, RefreshCcw, HelpCircle, CheckCircle2, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useSatQuery } from '../context/SatQueryContext';

interface RejectionStateProps {
  rejection: RejectionInfo;
}

export const RejectionState: React.FC<RejectionStateProps> = ({ rejection }) => {
  const navigate = useNavigate();
  const { setQuery } = useSatQuery();
  // An unclear query is not a problem with the inputs, and the fusion shortcut only helps an
  // optical+SAR pair that was submitted for change detection.
  const isAmbiguous = rejection.reasonCode === 'ambiguous_intent';
  const offersFusion = rejection.reasonCode === 'modality_mismatch';
  // No model exists for the task yet: neither the inputs nor the wording are at fault.
  const noModel = rejection.reasonCode === 'no_trained_model';
  const title = isAmbiguous
    ? 'Query Needs Clarification'
    : noModel
      ? 'No Trained Model for This Task Yet'
      : 'Physical Input Precondition Rejection';
  const retryLabel = isAmbiguous ? 'Rephrase Query' : noModel ? 'Ask a Different Question' : 'Modify Uploaded Images';

  return (
    <div style={{
      maxWidth: 900,
      margin: '0 auto 32px',
      background: 'var(--bg-card)',
      border: '1px solid rgba(225, 29, 72, 0.35)',
      borderRadius: 'var(--radius-lg)',
      padding: 32,
      boxShadow: 'var(--shadow-md)'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <div style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: 'rgba(225, 29, 72, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(225, 29, 72, 0.3)'
        }}>
          <ShieldAlert size={26} color="var(--rose-danger)" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              {title}
            </h3>
            <span className="badge badge-rose" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              CODE: {rejection.reasonCode.toUpperCase()}
            </span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
            Validated by Compatibility Validator • Execution halted before model inference
          </p>
        </div>
      </div>

      {/* Human Readable Explanation */}
      <div style={{
        background: 'rgba(225, 29, 72, 0.06)',
        borderLeft: '4px solid var(--rose-danger)',
        padding: '16px 20px',
        borderRadius: '0 var(--radius-md) var(--radius-md) 0',
        fontSize: 14,
        lineHeight: 1.6,
        color: 'var(--text-primary)',
        marginBottom: 24
      }}>
        {rejection.humanReadableReason}
      </div>

      {/* Comparison Grid: Detected vs Required */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 16,
        marginBottom: 24
      }}>
        {/* Detected Context */}
        <div style={{
          padding: '14px 16px',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(225, 29, 72, 0.05)',
          border: '1px solid rgba(225, 29, 72, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, color: 'var(--rose-danger)', fontWeight: 700, fontSize: 12 }}>
            <XCircle size={14} />
            <span>DETECTED CONFIGURATION</span>
          </div>
          {rejection.detectedContext ? (
            Object.entries(rejection.detectedContext).map(([k, v]) => (
              <div key={k} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>{k}:</span> <strong>{v}</strong>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Optical + SAR Cross-Modal Pair
            </span>
          )}
        </div>

        {/* Required Context */}
        <div style={{
          padding: '14px 16px',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(5, 150, 105, 0.05)',
          border: '1px solid rgba(5, 150, 105, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, color: 'var(--emerald-success)', fontWeight: 700, fontSize: 12 }}>
            <CheckCircle2 size={14} />
            <span>REQUIRED FOR REQUESTED TASK</span>
          </div>
          {rejection.requiredContext ? (
            Object.entries(rejection.requiredContext).map(([k, v]) => (
              <div key={k} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>{k}:</span> <strong>{v}</strong>
              </div>
            ))
          ) : (
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Two same-modality images acquired at different dates with at least 70% overlap
            </span>
          )}
        </div>
      </div>

      {/* Suggested Action */}
      {rejection.suggestedAction && (
        <div style={{
          padding: '14px 18px',
          borderRadius: 'var(--radius-md)',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-subtle)',
          marginBottom: 24
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: 'var(--cyan-primary)', marginBottom: 4 }}>
            <HelpCircle size={14} />
            <span>SUGGESTED CORRECTIVE ACTION</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
            {rejection.suggestedAction}
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'flex-end' }}>
        {offersFusion && (
          <button
            onClick={() => {
              // Preset to working optical-SAR fusion query
              setQuery('Use the optical and SAR images together to identify built-up and water-covered regions.');
              navigate('/analyze');
            }}
            className="btn-secondary"
            style={{ fontSize: 12 }}
          >
            <span>Switch to Optical-SAR Fusion Query</span>
            <ArrowRight size={14} />
          </button>
        )}

        <button
          onClick={() => navigate('/analyze')}
          className="btn-primary"
          style={{ fontSize: 13 }}
        >
          <RefreshCcw size={14} />
          <span>{retryLabel}</span>
        </button>
      </div>
    </div>
  );
};
