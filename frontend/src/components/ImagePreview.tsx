import React from 'react';
import type { ImageMetadata } from '../types/satquery';
import { Trash2, Radio, Compass, Layers, Calendar, RefreshCw } from 'lucide-react';
import { resolveAssetUrl } from '../services/api';

interface ImagePreviewProps {
  metadata: ImageMetadata;
  slotLabel: string;
  onRemove: () => void;
  onReplace?: () => void;
}

export const ImagePreview: React.FC<ImagePreviewProps> = ({
  metadata,
  slotLabel,
  onRemove,
  onReplace
}) => {
  const isSar = metadata.detectedModality === 'sar';
  // A user upload whose facts the backend is still reading (POST /v1/inspect).
  const reading = metadata.metadataStatus === 'reading';

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      boxShadow: 'var(--shadow-sm)'
    }}>
      {/* Slot Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: 'var(--bg-elevated)',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            {slotLabel}
          </span>
          <span className={`badge ${isSar ? 'badge-amber' : 'badge-cyan'}`} style={{ fontSize: 10 }}>
            {metadata.detectedModality.toUpperCase()}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {onReplace && (
            <button
              onClick={onReplace}
              title="Replace image"
              style={{
                background: 'transparent',
                color: 'var(--text-secondary)',
                padding: 4,
                borderRadius: 4
              }}
            >
              <RefreshCw size={13} />
            </button>
          )}
          <button
            onClick={onRemove}
            title="Remove image"
            style={{
              background: 'transparent',
              color: 'var(--rose-danger)',
              padding: 4,
              borderRadius: 4
            }}
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Raster Image Visualizer */}
      <div style={{
        position: 'relative',
        width: '100%',
        height: 180,
        background: 'var(--bg-canvas)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        <img
          src={resolveAssetUrl(metadata.previewUrl)}
          alt={metadata.name}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />

        {/* Floating format badge */}
        <div style={{
          position: 'absolute',
          bottom: 8,
          left: 8,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          padding: '2px 8px',
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 600,
          fontFamily: 'var(--font-mono)',
          color: '#ffffff'
        }}>
          {metadata.format.toUpperCase()}
        </div>

        {metadata.cloudMaskPercent !== null && metadata.cloudMaskPercent !== undefined && metadata.cloudMaskPercent > 10 && (
          <div style={{
            position: 'absolute',
            bottom: 8,
            right: 8,
            background: 'rgba(245, 158, 11, 0.85)',
            padding: '2px 8px',
            borderRadius: 4,
            fontSize: 10,
            fontWeight: 600,
            color: '#000000'
          }}>
            Cloud: {metadata.cloudMaskPercent}%
          </div>
        )}
      </div>

      {/* Extracted Metadata Summary (GDAL / Rasterio) */}
      <div style={{
        padding: '10px 12px',
        fontSize: 11,
        color: 'var(--text-secondary)',
        display: 'flex',
        flexDirection: 'column',
        gap: 6
      }}>
        <div style={{
          fontWeight: 600,
          color: 'var(--text-primary)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}>
          {metadata.name}
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 6,
          marginTop: 2
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
            <Compass size={12} color="var(--cyan-primary)" />
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              {reading ? 'Reading file…' : metadata.crs ? metadata.crs.split(' ')[0] : 'No CRS'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
            <Radio size={12} color="var(--indigo-primary)" />
            <span style={{ fontSize: 10 }}>
              GSD: {reading ? '…' : metadata.gsdMeters ? `${metadata.gsdMeters}m` : 'unknown'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
            <Layers size={12} color="var(--emerald-success)" />
            <span style={{ fontSize: 10 }}>
              {reading ? '… Bands' : `${metadata.bandCount} Bands`}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
            <Calendar size={12} color="var(--amber-warning)" />
            <span style={{ fontSize: 10 }}>
              {reading ? '…' : metadata.acquisitionTimestamp ? metadata.acquisitionTimestamp.split('T')[0] : 'Date unknown'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
