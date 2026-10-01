import React, { useState, useEffect } from 'react';
import { Shield, ArrowRight, Menu, X } from 'lucide-react';

export default function Navbar({ onOpenContact }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [latency, setLatency] = useState(14);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    let isMounted = true;
    const fetchStatus = async () => {
      if (document.hidden) return;
      try {
        const res = await fetch('/api/v1/status');
        if (res.ok && isMounted) {
          const data = await res.json();
          if (data.latency_ms !== undefined) {
            setLatency(typeof data.latency_ms === 'number' ? data.latency_ms.toFixed(1) : data.latency_ms);
          }
        }
      } catch {
        // fallback
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);


  return (
    <header className={`navbar-wrapper ${scrolled ? 'navbar-scrolled' : ''}`}>
      <div className="container">
        <nav className="navbar-content">
          {/* Brand Logo - Salesrocket Minimalist Style */}
          <a href="#" className="brand-logo" id="nav-brand">
            <div className="brand-icon-circ">
              <Shield size={16} />
            </div>
            <span className="brand-name">Castleweb</span>
          </a>

          {/* Desktop Nav Links - Centered */}
          <div className="nav-links">
            <a href="#hero" className="nav-link">Главная</a>
            <a href="#features" className="nav-link">Преимущества</a>
            <a href="#cases" className="nav-link">Кейсы</a>
            <a href="#calculator" className="nav-link">Калькулятор</a>
            <a href="#architecture" className="nav-link">Архитектура</a>
            <a href="#faq" className="nav-link">FAQ</a>
          </div>

          {/* Nav Right CTA */}
          <div className="nav-actions">
            <div className="nav-telemetry-badge" title="Задержка отклика API">
              <span className="pulse-beacon" />
              <span>{latency} ms</span>
            </div>

            <button 
              className="btn-primary nav-cta-btn" 
              onClick={onOpenContact}
              id="nav-btn-discuss"
            >
              <span>Обсудить проект</span>
              <ArrowRight size={14} />
            </button>

            <button 
              className="mobile-toggle-btn"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </nav>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="mobile-menu">
            <a href="#features" onClick={() => setMobileMenuOpen(false)} className="mobile-link">Преимущества</a>
            <a href="#cases" onClick={() => setMobileMenuOpen(false)} className="mobile-link">Кейсы</a>
            <a href="#calculator" onClick={() => setMobileMenuOpen(false)} className="mobile-link">Калькулятор</a>
            <a href="#architecture" onClick={() => setMobileMenuOpen(false)} className="mobile-link">Архитектура</a>
            <a href="#faq" onClick={() => setMobileMenuOpen(false)} className="mobile-link">FAQ</a>
            <button 
              className="btn-primary w-full" 
              onClick={() => { setMobileMenuOpen(false); onOpenContact(); }}
            >
              <span>Обсудить проект</span>
            </button>
          </div>
        )}
      </div>

      <style>{`
        .navbar-wrapper {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 100;
          padding: 20px 0;
          transition: all var(--transition-normal);
        }
        .navbar-scrolled {
          padding: 14px 0;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-bottom: 1px solid var(--border-subtle);
        }
        .navbar-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }
        .brand-logo {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .brand-icon-circ {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.16);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
        }
        .brand-name {
          font-family: var(--font-display);
          font-size: 1.15rem;
          font-weight: 700;
          color: #ffffff;
          letter-spacing: -0.02em;
        }
        .nav-links {
          display: flex;
          align-items: center;
          gap: 32px;
        }
        .nav-link {
          font-size: 0.88rem;
          font-weight: 500;
          color: var(--text-secondary);
          transition: color var(--transition-fast);
        }
        .nav-link:hover {
          color: #ffffff;
        }
        .nav-actions {
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .nav-telemetry-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-subtle);
          border-radius: 9999px;
          font-size: 0.75rem;
          font-family: var(--font-mono);
          color: var(--text-secondary);
        }
        .nav-cta-btn {
          padding: 10px 20px;
          font-size: 0.85rem;
        }
        .mobile-toggle-btn {
          display: none;
          color: #ffffff;
        }
        .mobile-menu {
          display: none;
        }

        @media (max-width: 900px) {
          .nav-links, .nav-telemetry-badge {
            display: none;
          }
          .mobile-toggle-btn {
            display: block;
          }
          .mobile-menu {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-top: 16px;
            padding: 24px;
            background: #08090d;
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
          }
          .mobile-link {
            font-size: 1rem;
            color: var(--text-secondary);
          }
        }
      `}</style>
    </header>
  );
}
