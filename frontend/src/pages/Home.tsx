import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Terminal,
  CheckCircle2,
  Combine
} from 'lucide-react';

export const Home: React.FC = () => {
  return (
    <div style={{ padding: '32px 0 64px' }}>
      {/* Hero Section */}
      <section style={{
        textAlign: 'center',
        maxWidth: 920,
        margin: '0 auto 64px',
        padding: '24px 16px'
      }}>

        <h1 style={{
          fontSize: 48,
          lineHeight: 1.15,
          fontWeight: 800,
          color: 'var(--text-primary)',
          marginBottom: 20,
          letterSpacing: '-0.03em'
        }}>
          Grounded Multimodal Intelligence for <span style={{
            background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>Earth Observation</span>
        </h1>

        <p style={{
          fontSize: 17,
          lineHeight: 1.6,
          color: 'var(--text-secondary)',
          maxWidth: 780,
          margin: '0 auto 32px'
        }}>
          SatQuery AI is an agentic vision-language assistant for analyzing single, cross-modal (Optical + SAR),
          and bi-temporal remote-sensing imagery through plain natural-language queries — backed by deterministic
          input validation, specialist LoRA adapters, and verifier-in-the-loop auditability.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
          <Link to="/analyze" className="btn-primary" style={{ padding: '14px 32px', fontSize: 16 }}>
            <Sparkles size={18} />
            <span>Launch Analysis Studio</span>
            <ArrowRight size={18} />
          </Link>

          <a
            href="https://arxiv.org/abs/2603.29630"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
            style={{ padding: '14px 24px', fontSize: 14 }}
          >
            <span>BigEarthNet.txt Paper</span>
          </a>
        </div>
      </section>

      {/* Core Architectural Pillars Grid */}
      <section style={{ marginBottom: 64 }}>
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--cyan-primary)', letterSpacing: '0.06em' }}>
            ENGINEERING EXCELLENCE
          </span>
          <h2 style={{ fontSize: 28, fontWeight: 700, margin: '6px 0 0' }}>
            Four Governing System Principles
          </h2>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 20
        }}>
          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(2, 132, 199, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16
            }}>
              <ShieldCheck size={22} color="var(--cyan-primary)" />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>
              1. Validate Before You Execute
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Compatibility Validator structurally verifies physical preconditions (CRS, overlap at least 70%, modality count, temporal Δt) before any specialist runs. Rejects invalid requests with human-readable guidance.
            </p>
          </div>

          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(79, 70, 229, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16
            }}>
              <Combine size={22} color="var(--indigo-primary)" />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>
              2. Structured Optical-SAR Fusion
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Avoids empirically-falsified naive early channel concatenation. Uses independent single-image extraction, InfoNCE-grounded complementarity tagging (agreement, sar_only), and modality-cited verbalization.
            </p>
          </div>

          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(5, 150, 105, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16
            }}>
              <CheckCircle2 size={22} color="var(--emerald-success)" />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>
              3. Verifier-in-the-Loop
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Dedicated verifier node enforces $[0, 100]$ geometric sanity, evaluates cross-tool agreement, and checks LLM text claims against deterministic pixel counts to avoid hallucinated quantities.
            </p>
          </div>

          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(217, 119, 6, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16
            }}>
              <Terminal size={22} color="var(--amber-warning)" />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>
              4. Observable Audit Trace
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Zero hidden chain-of-thought. Emits an auditable execution summary of selected task, specialist models/adapters, active parameters, and runtime wall-clock milliseconds on every response.
            </p>
          </div>
        </div>
      </section>

      {/* Mandatory Capability Matrix */}
      <section style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-medium)',
        borderRadius: 'var(--radius-lg)',
        padding: 32,
        marginBottom: 48,
        boxShadow: 'var(--shadow-md)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--cyan-primary)' }}>
              PS SCOPE COMPLIANCE
            </span>
            <h3 style={{ fontSize: 20, fontWeight: 700, margin: '4px 0 0' }}>
              Full Evaluation Rubric Traceability
            </h3>
          </div>
          <span className="badge badge-emerald">100% PS Functional Scope Covered</span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 16
        }}>
          <div style={{ padding: 14, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--cyan-primary)' }}>SINGLE-IMAGE</span>
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '4px 0 6px' }}>VQA & Captioning</h4>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>Open-ended & closed-set VQA, multi-class LULC classification on optical/SAR imagery.</p>
          </div>

          <div style={{ padding: 14, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--indigo-primary)' }}>GROUNDING</span>
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '4px 0 6px' }}>Text-Guided Localization</h4>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>Normalized bounding boxes with dedicated multi-candidate ambiguity protocol.</p>
          </div>

          <div style={{ padding: 14, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--emerald-success)' }}>BI-TEMPORAL</span>
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '4px 0 6px' }}>Change VQA & Masks</h4>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>Siamese CEM attention, spatial change heatmaps, and deterministic pixel validation.</p>
          </div>

          <div style={{ padding: 14, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--amber-warning)' }}>CROSS-MODAL</span>
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '4px 0 6px' }}>Optical-SAR Fusion</h4>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>Cloud penetration via radar backscatter, structural double-bounce corroboration.</p>
          </div>
        </div>
      </section>

      {/* CTA Footer banner */}
      <section style={{
        textAlign: 'center',
        padding: '36px 24px',
        background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, rgba(79, 70, 229, 0.12) 100%)',
        border: '1px solid rgba(2, 132, 199, 0.3)',
        borderRadius: 'var(--radius-lg)'
      }}>
        <h3 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>
          Ready to Test the Agentic Pipeline?
        </h3>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', maxWidth: 560, margin: '0 auto 20px' }}>
          Explore the interactive studio with pre-loaded demo scenarios or upload your own satellite rasters.
        </p>
        <Link to="/analyze" className="btn-primary" style={{ padding: '12px 28px' }}>
          <span>Launch Analysis Studio</span>
          <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
};
