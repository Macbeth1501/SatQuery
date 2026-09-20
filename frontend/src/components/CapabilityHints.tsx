import React from 'react';
import { useSatQuery } from '../context/SatQueryContext';
import { CheckCircle2, AlertCircle, Eye, Focus, Clock, Combine, GitFork } from 'lucide-react';

export const CapabilityHints: React.FC = () => {
  const { supportedCapabilities, image1, image2 } = useSatQuery();

  const capabilities = [
    {
      id: 'vqa',
      title: 'Single-Image VQA',
      icon: <Eye size={14} />,
      enabled: supportedCapabilities.singleVqa,
      req: '1 Image (Any modality)',
      badge: 'PS Mandatory'
    },
    {
      id: 'grounding',
      title: 'Region Grounding',
      icon: <Focus size={14} />,
      enabled: supportedCapabilities.grounding,
      req: '1 Optical Image',
      badge: 'Ambiguity-Aware'
    },
    {
      id: 'change',
      title: 'Bi-Temporal Change',
      icon: <Clock size={14} />,
      enabled: supportedCapabilities.changeAnalysis,
      req: '2 Images (Same modality, Δt)',
      badge: 'CEM + Pixel Count'
    },
    {
      id: 'fusion',
      title: 'Optical-SAR Fusion',
      icon: <Combine size={14} />,
      enabled: supportedCapabilities.opticalSarFusion,
      req: 'Optical + SAR Pair',
      badge: 'Complementary'
    },
    {
      id: 'compound',
      title: 'Compound Pipeline',
      icon: <GitFork size={14} />,
      enabled: supportedCapabilities.compoundPipeline,
      req: 'Multi-Sensor / Temporal Pair',
      badge: 'Sequential Plan'
    }
  ];

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-md)',
      padding: '14px 18px',
      marginBottom: 24,
      boxShadow: 'var(--shadow-sm)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 10
      }}>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
          Precondition Matrix & Capability Readiness
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Active Inputs: <strong style={{ color: 'var(--text-primary)' }}>{(image1 ? 1 : 0) + (image2 ? 1 : 0)} image(s)</strong>
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 10
      }}>
        {capabilities.map((cap) => (
          <div
            key={cap.id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 8,
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              background: cap.enabled ? 'rgba(5, 150, 105, 0.08)' : 'var(--bg-elevated)',
              border: cap.enabled ? '1px solid rgba(5, 150, 105, 0.25)' : '1px solid var(--border-subtle)',
              opacity: cap.enabled ? 1 : 0.45,
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{
              marginTop: 2,
              color: cap.enabled ? 'var(--emerald-success)' : 'var(--text-muted)'
            }}>
              {cap.icon}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: cap.enabled ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {cap.title}
                </span>
                {cap.enabled ? (
                  <CheckCircle2 size={12} color="var(--emerald-success)" />
                ) : (
                  <AlertCircle size={12} color="var(--text-muted)" />
                )}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                {cap.req}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
