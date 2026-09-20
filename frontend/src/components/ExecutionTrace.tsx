import React, { useState } from 'react';
import type { ExecutionTrace as IExecutionTrace } from '../types/satquery';
import { Terminal, ChevronDown, ChevronUp, Clock, CheckCircle2, ShieldAlert } from 'lucide-react';

interface ExecutionTraceProps {
  trace: IExecutionTrace;
  defaultExpanded?: boolean;
}

export const ExecutionTrace: React.FC<ExecutionTraceProps> = ({
  trace,
  defaultExpanded = true
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);

  const totalTimeMs = trace.steps.reduce((sum, s) => sum + s.wallClockMs, 0);

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      marginBottom: 24,
      boxShadow: 'var(--shadow-md)'
    }}>
      {/* Trace Header / Toggle Bar */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          background: 'var(--bg-elevated)',
          cursor: 'pointer',
          borderBottom: isExpanded ? '1px solid var(--border-subtle)' : 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Terminal size={16} color="var(--cyan-primary)" />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h4 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                Auditable Execution Trace
              </h4>
              <span className="badge badge-indigo" style={{ fontSize: 10 }}>
                {trace.steps.length} Steps
              </span>
              <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Session: {trace.sessionId}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--cyan-primary)', fontSize: 11 }}>
            <Clock size={12} />
            <span style={{ fontFamily: 'var(--font-mono)' }}>{totalTimeMs} ms</span>
          </div>

          <button style={{ background: 'transparent', color: 'var(--text-secondary)' }}>
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded Trace Timeline & Parameter Audit */}
      {isExpanded && (
        <div style={{ padding: '16px 20px' }}>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '0 0 16px' }}>
            Auditable execution log: Every component invocation, LoRA adapter ID, active parameters, and runtime duration recorded.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {trace.steps.map((step) => {
              const isRejected = step.status === 'rejected';

              return (
                <div
                  key={step.stepIndex}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-sm)',
                    background: isRejected ? 'rgba(225, 29, 72, 0.08)' : 'var(--bg-surface)',
                    border: isRejected ? '1px solid rgba(225, 29, 72, 0.3)' : '1px solid var(--border-subtle)',
                    boxShadow: 'var(--shadow-sm)',
                    gap: 6
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 8
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        width: 20,
                        height: 20,
                        borderRadius: '50%',
                        background: isRejected ? 'rgba(225, 29, 72, 0.15)' : 'rgba(2, 132, 199, 0.12)',
                        color: isRejected ? 'var(--rose-danger)' : 'var(--cyan-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 10,
                        fontWeight: 700
                      }}>
                        {step.stepIndex}
                      </span>

                      <span style={{
                        fontSize: 12,
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        color: isRejected ? 'var(--rose-danger)' : 'var(--text-primary)'
                      }}>
                        {step.component}
                      </span>

                      {step.adapterIdOrVersion && (
                        <span className="badge badge-cyan" style={{ fontSize: 9, fontFamily: 'var(--font-mono)' }}>
                          {step.adapterIdOrVersion}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontSize: 11,
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-muted)'
                      }}>
                        {step.wallClockMs} ms
                      </span>
                      {isRejected ? (
                        <ShieldAlert size={14} color="var(--rose-danger)" />
                      ) : (
                        <CheckCircle2 size={14} color="var(--emerald-success)" />
                      )}
                    </div>
                  </div>

                  {/* Output Summary */}
                  <div style={{
                    fontSize: 12,
                    color: 'var(--text-primary)',
                    paddingLeft: 28
                  }}>
                    {step.outputSummary}
                  </div>

                  {/* Parameters used */}
                  {Object.keys(step.parametersUsed).length > 0 && (
                    <div style={{
                      paddingLeft: 28,
                      fontSize: 10,
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-muted)',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: 8
                    }}>
                      <span>Parameters:</span>
                      {Object.entries(step.parametersUsed).map(([k, v]) => (
                        <span
                          key={k}
                          style={{
                            background: 'var(--bg-elevated)',
                            padding: '1px 6px',
                            borderRadius: 3,
                            border: '1px solid var(--border-subtle)'
                          }}
                        >
                          {k}={typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
