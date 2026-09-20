import React, { useState } from 'react';
import type { AnalyzeResponse } from '../types/satquery';
import { FileText, Code, Check } from 'lucide-react';
import { API_BASE } from '../services/api';

interface ReportDownloadProps {
  response: AnalyzeResponse;
  query?: string;
}

export const ReportDownload: React.FC<ReportDownloadProps> = ({
  response,
}) => {
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'json' | null>(null);

  const handleDownloadJSON = () => {
    setDownloadingFormat('json');
    // Try opening backend generated report attachment, with fallback to client json
    const backendUrl = `${API_BASE}/v1/session/${response.sessionId}/report?format=json`;
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', backendUrl);
    downloadAnchor.setAttribute('download', `SatQuery_Report_${response.sessionId}.json`);
    downloadAnchor.setAttribute('target', '_blank');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    setTimeout(() => setDownloadingFormat(null), 1500);
  };

  const handleDownloadPDF = () => {
    setDownloadingFormat('pdf');
    // Open backend rendered printable report in new tab or trigger window print
    const backendReportUrl = `${API_BASE}/v1/session/${response.sessionId}/report?format=pdf`;
    window.open(backendReportUrl, '_blank');
    setTimeout(() => setDownloadingFormat(null), 1500);
  };

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-md)',
      padding: '16px 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: 12,
      boxShadow: 'var(--shadow-sm)'
    }}>
      <div>
        <h4 style={{ fontSize: 13, fontWeight: 700, margin: '0 0 2px', color: 'var(--text-primary)' }}>
          Downloadable Evidence Report (SPDD §9.6 Parity)
        </h4>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
          Exports grounded response, visual evidence coordinates, confidence tier, and full audit trace table.
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button
          onClick={handleDownloadPDF}
          className="btn-secondary"
          style={{ fontSize: 12, padding: '8px 14px' }}
        >
          {downloadingFormat === 'pdf' ? <Check size={14} color="var(--emerald-success)" /> : <FileText size={14} color="var(--cyan-primary)" />}
          <span>Download PDF Report</span>
        </button>

        <button
          onClick={handleDownloadJSON}
          className="btn-secondary"
          style={{ fontSize: 12, padding: '8px 14px' }}
        >
          {downloadingFormat === 'json' ? <Check size={14} color="var(--emerald-success)" /> : <Code size={14} color="var(--indigo-primary)" />}
          <span>Export Trace (JSON)</span>
        </button>
      </div>
    </div>
  );
};
