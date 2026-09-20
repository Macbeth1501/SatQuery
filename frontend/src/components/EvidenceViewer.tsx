import React, { useState } from 'react';
import type { BoundingBox, RegionTag } from '../types/satquery';
import { Eye, EyeOff, Layers } from 'lucide-react';
import { resolveAssetUrl } from '../services/api';

interface EvidenceViewerProps {
  primaryImageUrl: string;
  secondaryImageUrl?: string | null;
  boxes: BoundingBox[];
  masks?: string[] | null;
  regionTags?: RegionTag[] | null;
  primaryLabel?: string;
  secondaryLabel?: string;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  primaryImageUrl,
  secondaryImageUrl,
  boxes,
  masks: masksProp,
  regionTags: regionTagsProp,
  primaryLabel = 'Observation / Scene',
  secondaryLabel = 'Paired Modality / T2'
}) => {
  // Defaults only apply to undefined; the API sends null, so normalize explicitly.
  const masks = masksProp ?? [];
  const regionTags = regionTagsProp ?? [];

  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [showMasks, setShowMasks] = useState<boolean>(true);
  const [showRegions, setShowRegions] = useState<boolean>(true);
  const [activeImageTab, setActiveImageTab] = useState<'primary' | 'secondary'>('primary');
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null);

  const isDualView = Boolean(secondaryImageUrl);
  const currentImageUrl = resolveAssetUrl(
    activeImageTab === 'secondary' && secondaryImageUrl ? secondaryImageUrl : primaryImageUrl
  );

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      marginBottom: 24,
      boxShadow: 'var(--shadow-md)'
    }}>
      {/* Viewer Controls Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: 'var(--bg-elevated)',
        borderBottom: '1px solid var(--border-subtle)',
        flexWrap: 'wrap',
        gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Layers size={16} color="var(--cyan-primary)" />
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            Visual Evidence Canvas
          </span>

          {/* Dual image switcher if secondary image exists */}
          {isDualView && (
            <div style={{
              display: 'flex',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: 2,
              marginLeft: 8
            }}>
              <button
                onClick={() => setActiveImageTab('primary')}
                style={{
                  padding: '4px 10px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  background: activeImageTab === 'primary' ? 'var(--cyan-primary)' : 'transparent',
                  color: activeImageTab === 'primary' ? '#ffffff' : 'var(--text-secondary)'
                }}
              >
                {primaryLabel}
              </button>
              <button
                onClick={() => setActiveImageTab('secondary')}
                style={{
                  padding: '4px 10px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  background: activeImageTab === 'secondary' ? 'var(--indigo-primary)' : 'transparent',
                  color: activeImageTab === 'secondary' ? '#ffffff' : 'var(--text-secondary)'
                }}
              >
                {secondaryLabel}
              </button>
            </div>
          )}
        </div>

        {/* Evidence Layer Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {boxes.length > 0 && (
            <button
              onClick={() => setShowBoxes(!showBoxes)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                borderRadius: 'var(--radius-full)',
                fontSize: 11,
                fontWeight: 600,
                background: showBoxes ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                border: showBoxes ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid var(--border-subtle)',
                color: showBoxes ? 'var(--cyan-primary)' : 'var(--text-muted)'
              }}
            >
              {showBoxes ? <Eye size={12} /> : <EyeOff size={12} />}
              <span>Bounding Boxes ({boxes.length})</span>
            </button>
          )}

          {masks.length > 0 && (
            <button
              onClick={() => setShowMasks(!showMasks)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                borderRadius: 'var(--radius-full)',
                fontSize: 11,
                fontWeight: 600,
                background: showMasks ? 'rgba(244, 63, 94, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                border: showMasks ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid var(--border-subtle)',
                color: showMasks ? 'var(--rose-danger)' : 'var(--text-muted)'
              }}
            >
              {showMasks ? <Eye size={12} /> : <EyeOff size={12} />}
              <span>Change Heatmap</span>
            </button>
          )}

          {regionTags.length > 0 && (
            <button
              onClick={() => setShowRegions(!showRegions)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                borderRadius: 'var(--radius-full)',
                fontSize: 11,
                fontWeight: 600,
                background: showRegions ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                border: showRegions ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid var(--border-subtle)',
                color: showRegions ? 'var(--emerald-success)' : 'var(--text-muted)'
              }}
            >
              {showRegions ? <Eye size={12} /> : <EyeOff size={12} />}
              <span>Sensor Tags ({regionTags.length})</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Canvas Viewport */}
      <div style={{
        position: 'relative',
        width: '100%',
        minHeight: 440,
        background: 'var(--bg-canvas)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        {/* Base Raster Image */}
        <img
          src={currentImageUrl}
          alt="Satellite Observation"
          style={{
            width: '100%',
            height: 'auto',
            maxHeight: 560,
            objectFit: 'contain',
            display: 'block'
          }}
        />

        {/* Change Mask Simulated Heatmap Overlay */}
        {showMasks && masks.length > 0 && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle at 75% 30%, rgba(244, 63, 94, 0.45) 0%, rgba(245, 158, 11, 0.25) 35%, transparent 65%)',
            pointerEvents: 'none',
            mixBlendMode: 'screen'
          }} />
        )}

        {/* Interactive Bounding Box Overlays (SPDD Normalized [0, 100] coordinates) */}
        {showBoxes && boxes.map((box, idx) => {
          const isHovered = hoveredBoxId === box.id;
          const isPrimary = box.isPrimary !== false;

          return (
            <div
              key={box.id || idx}
              onMouseEnter={() => box.id && setHoveredBoxId(box.id)}
              onMouseLeave={() => setHoveredBoxId(null)}
              style={{
                position: 'absolute',
                left: `${box.xLeft}%`,
                top: `${box.yTop}%`,
                width: `${box.xRight - box.xLeft}%`,
                height: `${box.yBottom - box.yTop}%`,
                border: isHovered 
                  ? '2px solid #ffffff' 
                  : (isPrimary ? '2px solid var(--cyan-primary)' : '2px dashed #0284c7'),
                background: isHovered 
                  ? 'rgba(2, 132, 199, 0.25)' 
                  : (isPrimary ? 'rgba(2, 132, 199, 0.12)' : 'rgba(2, 132, 199, 0.06)'),
                boxShadow: isHovered ? '0 0 16px var(--cyan-glow)' : 'none',
                transition: 'all 0.15s ease',
                cursor: 'pointer',
                zIndex: isHovered ? 20 : 10
              }}
            >
              {/* Box Tag Label */}
              <div style={{
                position: 'absolute',
                top: -24,
                left: 0,
                background: isHovered ? 'var(--cyan-primary)' : 'var(--bg-surface)',
                color: isHovered ? '#ffffff' : 'var(--text-primary)',
                border: `1px solid ${isPrimary ? 'var(--cyan-primary)' : 'var(--border-medium)'}`,
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 700,
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                boxShadow: 'var(--shadow-sm)'
              }}>
                <span>{box.label || `Region ${idx + 1}`}</span>
                {box.score && (
                  <span style={{ fontFamily: 'var(--font-mono)', opacity: 0.85 }}>
                    {(box.score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Optical-SAR Complementarity Region Breakdown (if available) */}
      {showRegions && regionTags.length > 0 && (
        <div style={{
          padding: '14px 18px',
          background: 'var(--bg-elevated)',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
            Multi-Sensor Complementarity Analysis:
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
            {regionTags.map((tag, i) => {
              const tagColors = {
                agreement: { badge: 'badge-emerald', label: 'DUAL-SENSOR AGREEMENT' },
                sar_only: { badge: 'badge-amber', label: 'SAR RADAR ONLY (CLOUD PIERCED)' },
                optical_only: { badge: 'badge-cyan', label: 'OPTICAL SPECTRAL ONLY' }
              };
              const config = tagColors[tag.tag] || { badge: 'badge-cyan', label: tag.tag.toUpperCase() };

              return (
                <div
                  key={i}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    boxShadow: 'var(--shadow-sm)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{tag.region}</span>
                    <span className={`badge ${config.badge}`} style={{ fontSize: 9 }}>
                      {config.label}
                    </span>
                  </div>
                  {tag.description && (
                    <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: 0 }}>
                      {tag.description}
                    </p>
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
