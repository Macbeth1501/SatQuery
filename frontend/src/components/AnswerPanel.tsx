import React, { useState } from 'react';
import { Bot, Copy, Check, Compass } from 'lucide-react';

interface AnswerPanelProps {
  answerText: string;
  query: string;
  taskType?: string;
}

export const AnswerPanel: React.FC<AnswerPanelProps> = ({
  answerText,
  query,
  taskType
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(answerText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-lg)',
      padding: '20px 24px',
      marginBottom: 24,
      boxShadow: 'var(--shadow-md)'
    }}>
      {/* Header bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 14,
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 'var(--radius-sm)',
            background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(2, 132, 199, 0.3)'
          }}>
            <Bot size={18} color="#ffffff" />
          </div>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              Grounded Remote-Sensing Response
            </h3>
            {taskType && (
              <span style={{ fontSize: 11, color: 'var(--cyan-primary)', fontFamily: 'var(--font-mono)' }}>
                Task: {taskType.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        <button
          onClick={handleCopy}
          className="btn-secondary"
          style={{ padding: '6px 12px', fontSize: 12 }}
        >
          {copied ? <Check size={14} color="var(--emerald-success)" /> : <Copy size={14} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Query echo */}
      <div style={{
        fontSize: 12,
        color: 'var(--text-muted)',
        marginBottom: 12,
        padding: '6px 12px',
        background: 'var(--bg-elevated)',
        borderRadius: 'var(--radius-sm)',
        display: 'flex',
        alignItems: 'center',
        gap: 6
      }}>
        <Compass size={13} color="var(--cyan-primary)" />
        <span>Query:</span>
        <strong style={{ color: 'var(--text-secondary)' }}>"{query}"</strong>
      </div>

      {/* Grounded synthesis text */}
      <div style={{
        fontSize: 14.5,
        lineHeight: 1.7,
        color: 'var(--text-primary)',
        letterSpacing: '0.01em'
      }}>
        {answerText}
      </div>
    </div>
  );
};
