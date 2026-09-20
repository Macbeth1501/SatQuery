import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSatQuery } from '../context/SatQueryContext';
import { AnswerPanel } from '../components/AnswerPanel';
import { EvidenceViewer } from '../components/EvidenceViewer';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { ExecutionTrace } from '../components/ExecutionTrace';
import { ReportDownload } from '../components/ReportDownload';
import { RejectionState } from '../components/RejectionState';
import { ResultSourceBadge } from '../components/ResultSourceBadge';
import { getSession, SessionNotFoundError } from '../services/api';
import { ArrowLeft, Layers, Loader2, SearchX } from 'lucide-react';

export const Results: React.FC = () => {
  const { results, query, image1, image2, resultSource, openSession } = useSatQuery();
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [load, setLoad] = useState<'idle' | 'loading' | 'notFound' | 'error'>('idle');

  const needsFetch = Boolean(sessionId) && results?.sessionId !== sessionId;

  // Direct navigation to /results/:sessionId, or a reload: no router state or context
  // survives, so fetch the stored session from the backend.
  useEffect(() => {
    if (!sessionId || !needsFetch) return;
    let cancelled = false;
    setLoad('loading');
    getSession(sessionId)
      .then((res) => {
        if (cancelled) return;
        openSession(res);
        setLoad('idle');
      })
      .catch((err) => {
        if (cancelled) return;
        setLoad(err instanceof SessionNotFoundError ? 'notFound' : 'error');
      });
    return () => {
      cancelled = true;
    };
    // openSession is recreated each render; the effect must key on the id only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, needsFetch]);

  // Give a fresh live result a URL that survives a reload. Demo results were never
  // persisted, so they keep the plain /results path.
  useEffect(() => {
    if (!sessionId && results && resultSource === 'live') {
      navigate(`/results/${results.sessionId}`, { replace: true });
    }
  }, [sessionId, results, resultSource, navigate]);

  if (needsFetch && load !== 'notFound' && load !== 'error') {
    return (
      <div role="status" style={{ textAlign: 'center', padding: '80px 20px' }}>
        <Loader2 size={28} className="pulse-indicator" color="var(--cyan-primary)" />
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 12 }}>
          Loading session {sessionId}…
        </p>
      </div>
    );
  }

  if (needsFetch) {
    const notFound = load === 'notFound';
    return (
      <div style={{ textAlign: 'center', padding: '80px 20px', maxWidth: 540, margin: '0 auto' }}>
        <SearchX size={32} color="var(--rose-danger, #e11d48)" />
        <h3 style={{ fontSize: 20, fontWeight: 700, margin: '12px 0 8px' }}>
          {notFound ? 'Session Not Found' : 'Could Not Load Session'}
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
          {notFound
            ? `No stored analysis exists for "${sessionId}". The link may be mistyped or the session may have been removed.`
            : `The backend could not be reached while loading "${sessionId}". Check that it is running and try again.`}
        </p>
        <Link to="/analyze" className="btn-primary">
          <span>Go to Analysis Studio</span>
        </Link>
      </div>
    );
  }

  // Handle empty state
  if (!results) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '80px 20px',
        maxWidth: 540,
        margin: '0 auto'
      }}>
        <div style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: 'rgba(2, 132, 199, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px'
        }}>
          <Layers size={28} color="var(--cyan-primary)" />
        </div>
        <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          No Active Analysis Results
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
          Upload satellite imagery and enter a natural-language query in the Analysis Studio to generate verified results.
        </p>
        <Link to="/analyze" className="btn-primary">
          <span>Go to Analysis Studio</span>
        </Link>
      </div>
    );
  }

  // FIRST-CLASS REJECTION VIEW
  if (results.rejected && results.rejectionDetails) {
    return (
      <div style={{ padding: '20px 0 48px' }}>
        {/* Navigation bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 24
        }}>
          <button
            onClick={() => navigate('/analyze')}
            className="btn-secondary"
            style={{ fontSize: 12, padding: '6px 14px' }}
          >
            <ArrowLeft size={14} />
            <span>Back to Studio</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ResultSourceBadge source={resultSource} />
            <span className="badge badge-rose" style={{ fontSize: 11 }}>
              Input Precondition Failed
            </span>
          </div>
        </div>

        {/* Dedicated Rejection Experience Card */}
        <RejectionState rejection={results.rejectionDetails} />

        {/* Trace of Rejection */}
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <ExecutionTrace trace={results.executionTrace} defaultExpanded={true} />
        </div>
      </div>
    );
  }

  // STANDARD SUCCESS DASHBOARD (Two-column layout per Hackathon Dev Plan §10)
  return (
    <div style={{ padding: '16px 0 48px' }}>
      {/* Top action bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 20
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={() => navigate('/analyze')}
            className="btn-secondary"
            style={{ fontSize: 12, padding: '8px 14px' }}
          >
            <ArrowLeft size={14} />
            <span>New Analysis</span>
          </button>
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>
              Analysis Results & Evidence
            </h2>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              Session: {results.sessionId}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <ResultSourceBadge source={resultSource} />
          <span className="badge badge-emerald">
            Verification Checks Passed
          </span>
        </div>
      </div>

      {/* Two-Column Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.2fr 0.8fr',
        gap: 24,
        alignItems: 'start'
      }}>
        {/* Left Column: Grounded Answer & Visual Evidence */}
        <div>
          {/* Grounded Natural-Language Answer Card */}
          <AnswerPanel
            answerText={results.answerText || 'Analysis completed.'}
            query={query}
            taskType={results.executionTrace.selectedTaskType}
          />

          {/* Interactive Evidence Canvas */}
          <EvidenceViewer
            primaryImageUrl={image1?.previewUrl || ''}
            secondaryImageUrl={image2?.previewUrl}
            boxes={results.evidence.boxes}
            masks={results.evidence.masks}
            regionTags={results.evidence.regionTags}
            primaryLabel={image1?.detectedModality.toUpperCase()}
            secondaryLabel={image2?.detectedModality.toUpperCase()}
          />

          {/* Report Download CTA */}
          <ReportDownload response={results} query={query} />
        </div>

        {/* Right Column: Audit, Confidence & Trace */}
        <div>
          {/* Confidence Badge with Verifier Checklist */}
          <ConfidenceBadge
            tier={results.confidence.tier}
            rationale={results.confidence.rationale}
            details={results.confidence.details}
          />

          {/* Auditable Execution Trace */}
          <ExecutionTrace
            trace={results.executionTrace}
            defaultExpanded={true}
          />
        </div>
      </div>
    </div>
  );
};
