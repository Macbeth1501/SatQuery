import React from 'react';
import { useSatQuery } from '../context/SatQueryContext';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Loader2, ArrowRight } from 'lucide-react';

export const AnalyzeButton: React.FC = () => {
  const { image1, query, isAnalyzing, startAnalysis } = useSatQuery();
  const navigate = useNavigate();

  const isReady = Boolean(image1 && query.trim());

  const handleClick = () => {
    if (!isReady || isAnalyzing) return;
    startAnalysis(() => {
      navigate('/results');
    });
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 16 }}>
      {!isReady && (
        <span style={{ fontSize: 12, color: 'var(--amber-warning)' }}>
          Please upload at least Image 1 and enter a query to run analysis.
        </span>
      )}

      <button
        onClick={handleClick}
        disabled={!isReady || isAnalyzing}
        className="btn-primary"
        style={{
          opacity: isReady && !isAnalyzing ? 1 : 0.5,
          cursor: isReady && !isAnalyzing ? 'pointer' : 'not-allowed',
          minWidth: 240,
          padding: '14px 28px',
          fontSize: 15
        }}
      >
        {isAnalyzing ? (
          <>
            <Loader2 size={18} className="pulse-indicator" />
            <span>Agent Orchestrating...</span>
          </>
        ) : (
          <>
            <Sparkles size={18} />
            <span>Run Agentic Analysis</span>
            <ArrowRight size={16} />
          </>
        )}
      </button>
    </div>
  );
};
