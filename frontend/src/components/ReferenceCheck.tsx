import React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { gradeAnswer, type RealSample } from '../data/realSample';

interface ReferenceCheckProps {
  sample: RealSample;
  query: string;
  answerText: string;
}

/**
 * Sets the trained model's answer beside BigEarthNet's reference answer for the real sample, so a
 * viewer sees it graded rather than taking it on trust. Renders nothing for a question the sample
 * has no reference for.
 */
export const ReferenceCheck: React.FC<ReferenceCheckProps> = ({ sample, query, answerText }) => {
  const graded = gradeAnswer(sample, query, answerText);
  if (!graded) return null;

  const Icon = graded.correct ? CheckCircle2 : XCircle;
  const color = graded.correct ? 'var(--emerald-success)' : 'var(--rose-danger)';

  return (
    <div
      data-testid="reference-check"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '12px 16px',
        marginBottom: 24,
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${color}`,
        background: 'var(--bg-card)',
        fontSize: 13,
      }}
    >
      <Icon size={18} color={color} />
      <span>
        BigEarthNet reference answer: <strong>{graded.referenceText}</strong>
        {' — '}
        {graded.modelAnswer === null
          ? 'the model reply could not be read as an answer'
          : graded.correct
            ? 'the model matches it'
            : 'the model got this wrong'}
      </span>
    </div>
  );
};
