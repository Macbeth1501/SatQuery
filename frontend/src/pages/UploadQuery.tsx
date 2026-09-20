import React from 'react';
import { ImageUploader } from '../components/ImageUploader';
import { QueryInput } from '../components/QueryInput';
import { CapabilityHints } from '../components/CapabilityHints';
import { AnalyzeButton } from '../components/AnalyzeButton';
import { DemoScenarioBar } from '../components/DemoScenarioBar';
import { ProcessingStatus } from '../components/ProcessingStatus';

export const UploadQuery: React.FC = () => {
  return (
    <div style={{ padding: '16px 0 48px' }}>
      {/* Page Heading */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 20
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <h2 style={{ fontSize: 24, fontWeight: 800, margin: 0 }}>
              Analysis Studio
            </h2>
            <span className="badge badge-cyan">Ingestion & Querying</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Upload 1 or 2 satellite rasters (GeoTIFF/TIFF/PNG/JPEG) and enter a natural-language query.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Validation Protocol:
          </span>
          <span className="badge badge-emerald">
            GeoGraphRAG Structural Preconditions Active
          </span>
        </div>
      </div>

      {/* 1-Click Evaluation Scenario Presets */}
      <DemoScenarioBar />

      {/* Main Studio Interaction Grid */}
      <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
        {/* Dual Slot Image Uploader */}
        <ImageUploader />

        {/* Natural Language Query Input */}
        <QueryInput />

        {/* Dynamic Capability & Precondition Readiness Matrix */}
        <CapabilityHints />

        {/* Analyze Submission Action */}
        <AnalyzeButton />
      </div>

      {/* Processing State Modal (Active during step progression) */}
      <ProcessingStatus />
    </div>
  );
};
