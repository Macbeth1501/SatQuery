import React from 'react';
import { DEMO_SCENARIOS } from '../data/mockScenarios';
import { useSatQuery } from '../context/SatQueryContext';
import { Play, Sparkles } from 'lucide-react';

export const DemoScenarioBar: React.FC = () => {
  const { activeScenario, loadScenario } = useSatQuery();

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.85)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-lg)',
      padding: '16px 20px',
      marginBottom: 24,
      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.45)',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(56, 189, 248, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Sparkles size={16} color="var(--cyan-primary)" />
          </div>
          <div>
            <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>
              Evaluation Scenarios (1-Click Presets)
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
              Pre-load verified ISRO benchmark imagery & representative queries to test each mandatory capability:
            </p>
          </div>
        </div>

        <span className="badge badge-cyan" style={{ fontSize: 10 }}>
          Deterministic Demo Engine
        </span>
      </div>

      {/* Scenario buttons */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: 10
      }}>
        {DEMO_SCENARIOS.map((scenario) => {
          const isSelected = activeScenario?.id === scenario.id;
          const isRejection = scenario.mockResponse.rejected;

          return (
            <button
              key={scenario.id}
              onClick={() => loadScenario(scenario.id)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: isSelected 
                  ? (isRejection ? 'rgba(225, 29, 72, 0.12)' : 'rgba(2, 132, 199, 0.12)') 
                  : 'var(--bg-elevated)',
                border: isSelected
                  ? (isRejection ? '1px solid rgba(225, 29, 72, 0.5)' : '1px solid rgba(2, 132, 199, 0.5)')
                  : '1px solid var(--border-subtle)',
                textAlign: 'left',
                boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
                transition: 'all 0.2s ease',
                cursor: 'pointer'
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                marginBottom: 4
              }}>
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  color: isRejection ? 'var(--rose-danger)' : (isSelected ? 'var(--cyan-primary)' : 'var(--text-muted)')
                }}>
                  {scenario.tag}
                </span>
                {isSelected && (
                  <Play size={10} fill="currentColor" color={isRejection ? 'var(--rose-danger)' : 'var(--cyan-primary)'} />
                )}
              </div>
              <span style={{
                fontSize: 12,
                fontWeight: 600,
                color: isSelected ? (isRejection ? 'var(--rose-danger)' : 'var(--cyan-primary)') : 'var(--text-primary)',
                lineHeight: 1.3
              }}>
                {scenario.name.split(':')[1]?.trim() || scenario.name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
