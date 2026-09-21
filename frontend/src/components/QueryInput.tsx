import React from 'react';
import { useSatQuery } from '../context/SatQueryContext';
import { sampleDate } from '../data/realSample';
import { MessageSquare, Sparkles, X } from 'lucide-react';

export const QueryInput: React.FC = () => {
  const { query, setQuery, activeRealSample } = useSatQuery();
  const realSampleActive = activeRealSample !== null;

  const isoQueries = [
    'Describe the land-cover and major objects visible in this image.',
    'Highlight the water body referred to in the query.',
    'What changed between these two dates, and where did the change occur?',
    'Use the optical and SAR images together to identify built-up and water-covered regions.',
    'Has the built-up area increased, decreased, or remained unchanged?'
  ];

  // With the real BigEarthNet sample loaded, offer its own questions: they have reference
  // answers, and they are the only format the trained adapter was taught.
  const representativeQueries = activeRealSample ? activeRealSample.questions.map((q) => q.question) : isoQueries;
  const accent = realSampleActive ? 'var(--emerald-success)' : 'var(--cyan-primary)';
  const accentBg = realSampleActive ? 'rgba(5, 150, 105, 0.12)' : 'rgba(2, 132, 199, 0.12)';
  const accentBorder = realSampleActive ? '1px solid rgba(5, 150, 105, 0.5)' : '1px solid rgba(2, 132, 199, 0.4)';

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8
      }}>
        <label style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 13,
          fontWeight: 600,
          color: 'var(--text-primary)'
        }}>
          <MessageSquare size={14} color="var(--cyan-primary)" />
          Natural-Language Query
        </label>
        {query && (
          <button
            onClick={() => setQuery('')}
            style={{
              background: 'transparent',
              color: 'var(--text-muted)',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 6px'
            }}
          >
            <X size={12} />
            Clear
          </button>
        )}
      </div>

      <div style={{ position: 'relative' }}>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask any remote-sensing question in natural language (e.g., land-cover classification, region grounding, temporal change, or optical-SAR fusion)..."
          rows={3}
          style={{
            width: '100%',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 16px',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-sans)',
            fontSize: 14,
            lineHeight: 1.5,
            resize: 'none',
            outline: 'none',
            boxShadow: 'var(--shadow-sm)',
            transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = 'var(--cyan-primary)';
            e.currentTarget.style.boxShadow = '0 0 16px var(--cyan-glow)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-medium)';
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
          }}
        />
      </div>

      {/* PS Representative Query Suggestions */}
      <div style={{ marginTop: 10 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 11,
          color: 'var(--text-muted)',
          marginBottom: 6
        }}>
          <Sparkles size={11} color={realSampleActive ? 'var(--emerald-success)' : 'var(--indigo-primary)'} />
          <span>
            {realSampleActive
              ? "BigEarthNet's questions for this image, answered by the trained model (Click to use):"
              : 'ISRO Representative Queries (Click to use):'}
          </span>
        </div>

        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 6
        }}>
          {representativeQueries.map((q, idx) => (
            <button
              key={idx}
              onClick={() => setQuery(q)}
              style={{
                background: query === q ? accentBg : 'var(--bg-elevated)',
                border: query === q ? accentBorder : '1px solid var(--border-subtle)',
                color: query === q ? accent : 'var(--text-secondary)',
                borderRadius: 'var(--radius-full)',
                padding: '4px 12px',
                fontSize: 11,
                fontWeight: 500,
                transition: 'all 0.15s ease',
                cursor: 'pointer'
              }}
            >
              {q}
            </button>
          ))}
        </div>

        {activeRealSample && (
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '8px 0 0', lineHeight: 1.45 }}>
            Real Sentinel-2 image ({activeRealSample.country}, {sampleDate(activeRealSample)}); tile {activeRealSample.tile} was
            never seen in training. These images were chosen because the model answers their questions well. Across all unseen
            tiles it scores about 33% on multiple choice (chance 25%) and 50% on yes/no, so treat one image as a
            sample, not as its accuracy.
          </p>
        )}
      </div>
    </div>
  );
};
