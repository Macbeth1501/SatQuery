import React, { useRef } from 'react';
import { useSatQuery } from '../context/SatQueryContext';
import { ImagePreview } from './ImagePreview';
import type { ImageMetadata, ImageFormat, Modality } from '../types/satquery';
import { Upload, Plus } from 'lucide-react';

export const ImageUploader: React.FC = () => {
  const { image1, image2, setImage1, setImage2, setFile1, setFile2 } = useSatQuery();
  const fileInputRef1 = useRef<HTMLInputElement>(null);
  const fileInputRef2 = useRef<HTMLInputElement>(null);

  // Helper to construct ImageMetadata from user file upload
  const handleFileUpload = (file: File, slot: 1 | 2) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || 'png';
    const isTiff = ext === 'tif' || ext === 'tiff';
    const format: ImageFormat = isTiff ? 'geotiff' : (ext === 'jpeg' || ext === 'jpg' ? 'jpeg' : 'png');
    
    // Guess modality from filename or default to optical
    const lowerName = file.name.toLowerCase();
    const detectedModality: Modality = lowerName.includes('sar') || lowerName.includes('s1') || lowerName.includes('risat')
      ? 'sar'
      : 'optical';

    const newMetadata: ImageMetadata = {
      imageId: `upload_${Date.now()}_slot${slot}`,
      name: file.name,
      format,
      crs: isTiff ? 'EPSG:32643 (UTM 43N)' : 'Local Pixel Grid',
      bandCount: detectedModality === 'sar' ? 2 : 4,
      detectedModality,
      gsdMeters: detectedModality === 'sar' ? 1.0 : 0.65,
      acquisitionTimestamp: new Date().toISOString(),
      nodataPercent: 0.0,
      cloudMaskPercent: 0.0,
      previewUrl: URL.createObjectURL(file)
    };

    if (slot === 1) {
      setFile1(file);
      setImage1(newMetadata);
    } else {
      setFile2(file);
      setImage2(newMetadata);
    }
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 16,
      marginBottom: 20
    }}>
      {/* Hidden file inputs */}
      <input
        type="file"
        ref={fileInputRef1}
        style={{ display: 'none' }}
        accept=".tif,.tiff,.png,.jpg,.jpeg"
        onChange={(e) => {
          if (e.target.files?.[0]) handleFileUpload(e.target.files[0], 1);
        }}
      />
      <input
        type="file"
        ref={fileInputRef2}
        style={{ display: 'none' }}
        accept=".tif,.tiff,.png,.jpg,.jpeg"
        onChange={(e) => {
          if (e.target.files?.[0]) handleFileUpload(e.target.files[0], 2);
        }}
      />

      {/* Slot 1: Primary Image */}
      <div style={{ minHeight: 280 }}>
        {image1 ? (
          <ImagePreview
            metadata={image1}
            slotLabel="Image 1 (Primary / T1 / Optical)"
            onRemove={() => setImage1(null)}
            onReplace={() => fileInputRef1.current?.click()}
          />
        ) : (
          <div
            onClick={() => fileInputRef1.current?.click()}
            style={{
              height: '100%',
              minHeight: 280,
              border: '2px dashed var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 24,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              textAlign: 'center'
            }}
          >
            <div style={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              background: 'rgba(2, 132, 199, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 12
            }}>
              <Upload size={22} color="var(--cyan-primary)" />
            </div>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
              Upload Image 1 (Required)
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 220, marginBottom: 12 }}>
              Drag & drop or browse GeoTIFF, TIFF, PNG, or JPEG
            </p>
            <span className="badge badge-cyan">Primary / T1 / Optical</span>
          </div>
        )}
      </div>

      {/* Slot 2: Secondary Image */}
      <div style={{ minHeight: 280 }}>
        {image2 ? (
          <ImagePreview
            metadata={image2}
            slotLabel="Image 2 (Secondary / T2 / SAR)"
            onRemove={() => setImage2(null)}
            onReplace={() => fileInputRef2.current?.click()}
          />
        ) : (
          <div
            onClick={() => fileInputRef2.current?.click()}
            style={{
              height: '100%',
              minHeight: 280,
              border: '2px dashed var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 24,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              textAlign: 'center'
            }}
          >
            <div style={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              background: 'rgba(99, 102, 241, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 12
            }}>
              <Plus size={22} color="var(--indigo-primary)" />
            </div>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
              Upload Image 2 (Optional)
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 240, marginBottom: 12 }}>
              Required for Bi-temporal Change or Optical-SAR Fusion
            </p>
            <span className="badge badge-indigo">Pair: T2 / SAR</span>
          </div>
        )}
      </div>
    </div>
  );
};
