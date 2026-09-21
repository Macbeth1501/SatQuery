import React, { useRef } from 'react';
import { useSatQuery } from '../context/SatQueryContext';
import { findSampleByFile } from '../data/realSample';
import { inspectRaster } from '../services/api';
import { ImagePreview } from './ImagePreview';
import type { ImageMetadata, ImageFormat, Modality } from '../types/satquery';
import { Upload, Plus } from 'lucide-react';

export const ImageUploader: React.FC = () => {
  const { image1, image2, setImage1, setImage2, setFile1, setFile2, loadRealSample } = useSatQuery();
  const fileInputRef1 = useRef<HTMLInputElement>(null);
  const fileInputRef2 = useRef<HTMLInputElement>(null);

  // Each slot's latest upload; an inspect reply for an older file is ignored.
  const latestUpload = useRef<Record<1 | 2, string>>({ 1: '', 2: '' });
  const uploadCount = useRef(0);

  /**
   * Shows an uploaded file at once, then fills in what the file itself says, read by the backend
   * (POST /v1/inspect): CRS, GSD, bands, acquisition time, modality, and a preview a browser can
   * display even for a TIFF. Until then, and if the backend cannot be reached, those fields are
   * shown as unknown -- never guessed.
   */
  const handleFileUpload = (file: File, slot: 1 | 2) => {
    // A live-model sample (frontend/public/real/) uploaded by hand: use its known facts and PNG
    // preview, and switch on its questions.
    const sample = slot === 1 ? findSampleByFile(file.name) : null;
    if (sample) {
      latestUpload.current[1] = '';
      loadRealSample(sample.id, undefined, file);
      return;
    }

    const ext = file.name.split('.').pop()?.toLowerCase() || 'png';
    const isTiff = ext === 'tif' || ext === 'tiff';
    const format: ImageFormat = isTiff ? 'geotiff' : (ext === 'jpeg' || ext === 'jpg' ? 'jpeg' : 'png');
    // Provisional until the backend reads the file: the capability matrix needs a modality now.
    const lowerName = file.name.toLowerCase();
    const detectedModality: Modality = lowerName.includes('sar') || lowerName.includes('s1') || lowerName.includes('risat')
      ? 'sar'
      : 'optical';

    uploadCount.current += 1;
    const imageId = `upload_${uploadCount.current}_slot${slot}`;
    const provisional: ImageMetadata = {
      imageId,
      name: file.name,
      format,
      crs: null,
      bandCount: 0,
      detectedModality,
      gsdMeters: null,
      acquisitionTimestamp: null,
      nodataPercent: 0,
      cloudMaskPercent: null,
      previewUrl: URL.createObjectURL(file),
      metadataStatus: 'reading',
    };

    const setImage = slot === 1 ? setImage1 : setImage2;
    latestUpload.current[slot] = imageId;
    (slot === 1 ? setFile1 : setFile2)(file);
    setImage(provisional);

    inspectRaster(file)
      .then(({ metadata, previewDataUrl }) => {
        if (latestUpload.current[slot] !== imageId) return;
        // The backend's PNG replaces the blob preview, so the blob can be released.
        if (previewDataUrl) URL.revokeObjectURL(provisional.previewUrl);
        setImage({
          ...metadata,
          imageId,
          name: file.name,
          previewUrl: previewDataUrl ?? provisional.previewUrl,
          metadataStatus: 'read',
        });
      })
      .catch(() => {
        if (latestUpload.current[slot] !== imageId) return;
        setImage({ ...provisional, metadataStatus: 'unavailable' });
      });
  };

  const removeImage = (slot: 1 | 2) => {
    latestUpload.current[slot] = '';
    (slot === 1 ? setFile1 : setFile2)(null);
    (slot === 1 ? setImage1 : setImage2)(null);
  };

  const dropProps = (slot: 1 | 2) => ({
    onDragOver: (e: React.DragEvent) => e.preventDefault(),
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) handleFileUpload(file, slot);
    },
  });

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
          e.target.value = ''; // so picking the same file again still fires onChange
        }}
      />
      <input
        type="file"
        ref={fileInputRef2}
        style={{ display: 'none' }}
        accept=".tif,.tiff,.png,.jpg,.jpeg"
        onChange={(e) => {
          if (e.target.files?.[0]) handleFileUpload(e.target.files[0], 2);
          e.target.value = '';
        }}
      />

      {/* Slot 1: Primary Image */}
      <div style={{ minHeight: 280 }}>
        {image1 ? (
          <ImagePreview
            metadata={image1}
            slotLabel="Image 1 (Primary / T1 / Optical)"
            onRemove={() => removeImage(1)}
            onReplace={() => fileInputRef1.current?.click()}
          />
        ) : (
          <div
            onClick={() => fileInputRef1.current?.click()}
            {...dropProps(1)}
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
            onRemove={() => removeImage(2)}
            onReplace={() => fileInputRef2.current?.click()}
          />
        ) : (
          <div
            onClick={() => fileInputRef2.current?.click()}
            {...dropProps(2)}
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
