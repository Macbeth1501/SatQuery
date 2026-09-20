import React from 'react';
import { useSatQuery, PIPELINE_STEPS } from '../context/SatQueryContext';
import { Loader2, CheckCircle2, CircleDashed, Terminal, ShieldAlert } from 'lucide-react';

export const ProcessingStatus: React.FC = () => {
  const { isAnalyzing, activeStep, activeScenario } = useSatQuery();

  if (!isAnalyzing) return null;

  const isRejection = activeScenario?.mockResponse.rejected ?? false;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(15, 23, 42, 0.6)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 24
    }}>
      <div style={{
        maxWidth: 680,
        width: '100%',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-medium)',
        borderRadius: 'var(--radius-lg)',
        padding: 32,
        boxShadow: 'var(--shadow-lg)'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 24,
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: 16
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(2, 132, 199, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Terminal size={20} color="var(--cyan-primary)" />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                Agentic Orchestration Pipeline
              </h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                Observable execution trace active • Step {activeStep} of {isRejection ? 2 : 8}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Loader2 size={16} className="pulse-indicator" color="var(--cyan-primary)" />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--cyan-primary)' }}>
              PROCESSING
            </span>
          </div>
        </div>

        {/* Observable Pipeline Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {PIPELINE_STEPS.slice(0, isRejection ? 2 : 8).map((step) => {
            const isCompleted = activeStep > step.index;
            const isCurrent = activeStep === step.index;
            const isFailedRejection = isRejection && isCompleted && step.index === 2;

            return (
              <div
                key={step.index}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: isCurrent 
                    ? 'rgba(2, 132, 199, 0.1)' 
                    : (isCompleted ? 'var(--bg-elevated)' : 'transparent'),
                  border: isCurrent 
                    ? '1px solid rgba(2, 132, 199, 0.35)' 
                    : (isCompleted ? '1px solid var(--border-subtle)' : '1px solid transparent'),
                  transition: 'all 0.2s ease'
                }}
              >
                {/* Step indicator */}
                <div style={{ width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {isCompleted ? (
                    isFailedRejection ? (
                      <ShieldAlert size={18} color="var(--rose-danger)" />
                    ) : (
                      <CheckCircle2 size={18} color="var(--emerald-success)" />
                    )
                  ) : isCurrent ? (
                    <Loader2 size={18} className="pulse-indicator" color="var(--cyan-primary)" />
                  ) : (
                    <CircleDashed size={18} color="var(--text-muted)" />
                  )}
                </div>

                {/* Step Details */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: isCurrent ? 'var(--cyan-primary)' : (isCompleted ? 'var(--text-primary)' : 'var(--text-muted)')
                    }}>
                      {step.index}. {step.label}
                    </span>
                    <span style={{
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                      color: isCurrent ? 'var(--cyan-primary)' : 'var(--text-muted)'
                    }}>
                      {step.component}
                    </span>
                  </div>
                  <p style={{
                    fontSize: 11,
                    color: isCurrent ? 'var(--text-secondary)' : 'var(--text-muted)',
                    margin: '2px 0 0'
                  }}>
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Live progress footer */}
        <div style={{
          marginTop: 24,
          paddingTop: 16,
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 11,
          color: 'var(--text-muted)'
        }}>
          <span>Enforcing GeoGraphRAG Preconditions & Verifier-in-the-Loop</span>
          <span style={{ fontFamily: 'var(--font-mono)' }}>Elapsed: ~{(activeStep * 350 / 1000).toFixed(1)}s</span>
        </div>
      </div>
    </div>
  );
};
