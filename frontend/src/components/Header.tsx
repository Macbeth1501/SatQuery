import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Satellite, Layers, Activity, Cpu, Sparkles, Sun, Moon } from 'lucide-react';
import { useSatQuery } from '../context/SatQueryContext';

export const Header: React.FC = () => {
  const location = useLocation();
  const { results, isAnalyzing } = useSatQuery();

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('satquery-theme') as 'light' | 'dark') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('satquery-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <header style={{
      borderBottom: '1px solid var(--border-subtle)',
      background: 'var(--bg-glass)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '0 32px',
      transition: 'background 0.2s ease, border-color 0.2s ease'
    }}>
      <div style={{
        maxWidth: 1440,
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 68
      }}>
        {/* Brand & Project Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 10px rgba(2, 132, 199, 0.3)'
            }}>
              <Satellite size={22} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 19,
                  fontWeight: 800,
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.03em'
                }}>
                  SatQuery<span style={{ color: 'var(--cyan-primary)' }}> AI</span>
                </span>
                <span className="badge badge-indigo" style={{ fontSize: 10 }}>
                  SIH26167
                </span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
                ISRO / Department of Space • Agentic Vision-Language Assistant
              </p>
            </div>
          </Link>
        </div>

        {/* Primary Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Link
            to="/"
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: 13,
              fontWeight: 500,
              color: location.pathname === '/' ? 'var(--cyan-primary)' : 'var(--text-secondary)',
              background: location.pathname === '/' ? 'rgba(2, 132, 199, 0.1)' : 'transparent',
              border: location.pathname === '/' ? '1px solid rgba(2, 132, 199, 0.28)' : '1px solid transparent',
              transition: 'all 0.2s ease'
            }}
          >
            Overview
          </Link>

          <Link
            to="/analyze"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: 13,
              fontWeight: 600,
              color: location.pathname === '/analyze' ? 'var(--cyan-primary)' : 'var(--text-secondary)',
              background: location.pathname === '/analyze' ? 'rgba(2, 132, 199, 0.12)' : 'transparent',
              border: location.pathname === '/analyze' ? '1px solid rgba(2, 132, 199, 0.3)' : '1px solid transparent',
              transition: 'all 0.2s ease'
            }}
          >
            <Sparkles size={14} color="var(--cyan-primary)" />
            Analysis Studio
          </Link>

          <Link
            to="/results"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: 13,
              fontWeight: 500,
              color: location.pathname === '/results' ? 'var(--cyan-primary)' : 'var(--text-secondary)',
              background: location.pathname === '/results' ? 'rgba(2, 132, 199, 0.1)' : 'transparent',
              border: location.pathname === '/results' ? '1px solid rgba(2, 132, 199, 0.25)' : '1px solid transparent',
              opacity: results || isAnalyzing ? 1 : 0.45,
              pointerEvents: results || isAnalyzing ? 'auto' : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            <Layers size={14} />
            Results Dashboard
            {results && (
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: results.rejected ? 'var(--rose-danger)' : 'var(--emerald-success)'
              }} />
            )}
          </Link>
        </nav>

        {/* System, Engine Status & Theme Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '5px 12px',
            background: 'var(--bg-elevated)',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--border-subtle)'
          }}>
            <Cpu size={13} color="var(--cyan-primary)" />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Engine:</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>LoRA Multi-Specialist</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '5px 12px',
            background: 'rgba(16, 185, 129, 0.08)',
            borderRadius: 'var(--radius-full)',
            border: '1px solid rgba(16, 185, 129, 0.25)'
          }}>
            <Activity size={12} color="var(--emerald-success)" />
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--emerald-success)' }}>
              {isAnalyzing ? 'ORCHESTRATING' : 'READY'}
            </span>
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-medium)',
              color: 'var(--text-primary)',
              boxShadow: 'var(--shadow-sm)',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {theme === 'light' ? (
              <Moon size={16} color="var(--indigo-primary)" />
            ) : (
              <Sun size={16} color="var(--amber-warning)" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
