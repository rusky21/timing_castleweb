import React from 'react';
import { ArrowRight, Sparkles, Percent } from 'lucide-react';

const PARTNERS = [
  'asana', 'Fidelity', 'CenturyLink', 'coinbase', 'BINANCE', 'Cloudflare', 'FastAPI', 'PostgreSQL'
];

export default function Hero({ onOpenContact, onExploreCases }) {
  return (
    <section className="hero-section" id="hero">
      <div className="container">
        {/* Main Hero Grid */}
        <div className="hero-grid">
          {/* Left Column: Headlines & CTA */}
          <div className="hero-content">
            {/* Salesrocket Top Pill */}
            <div className="badge-capsule hero-badge">
              <span className="badge-icon">
                <Sparkles size={11} />
              </span>
              <span>HIGHLOAD & AI-DRIVEN WEB ENGINEERING</span>
            </div>

            <h1 className="hero-title">
              AI-Driven & Highload Solutions <br />
              <span className="text-highlight">for Modern Businesses</span>
            </h1>

            <p className="hero-description">
              Castleweb is engineered with your goals in mind, making architecture and delivery reliable. 
              We build high-concurrency SaaS platforms, interactive 3D WebGL interfaces, and zero-downtime APIs without compromise.
            </p>

            <div className="hero-actions">
              <a href="#calculator" className="btn-primary" id="hero-btn-calc">
                <span>Рассчитать смету</span>
                <ArrowRight size={16} />
              </a>
              <button onClick={onExploreCases} className="btn-secondary" id="hero-btn-cases">
                <span>Смотреть кейсы</span>
              </button>
            </div>
          </div>

          {/* Right Column: 3D Liquid Chrome Sculpture */}
          <div className="hero-visual">
            <div className="hero-img-wrap">
              <img 
                src="/hero_chrome.jpg" 
                alt="3D Liquid Chrome Abstract Sculpture" 
                className="hero-3d-img"
              />
              <div className="hero-img-glow" />
            </div>
          </div>
        </div>

        {/* Stats Strip - Matches reference 380+ User Active | 230+ Trusted | $230M+ */}
        <div className="hero-stats-strip">
          <div className="stat-unit">
            <span className="stat-num">48+</span>
            <span className="stat-desc">Проектов в проде</span>
          </div>
          <div className="stat-sep" />
          <div className="stat-unit">
            <span className="stat-num">230+</span>
            <span className="stat-desc">Клиентов по всему миру</span>
          </div>
          <div className="stat-sep" />
          <div className="stat-unit">
            <span className="stat-num">99.98%</span>
            <span className="stat-desc">Гарантированный Uptime</span>
          </div>
          <div className="stat-sep" />
          <div className="stat-unit">
            <span className="stat-num">&lt; 50ms</span>
            <span className="stat-desc">Средний отклик API</span>
          </div>
        </div>

        {/* Partner Logos Strip */}
        <div className="hero-partners-strip">
          {PARTNERS.map((name, i) => (
            <div key={i} className="partner-logo-item">
              <span className="partner-name">{name}</span>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .hero-section {
          padding: 140px 0 80px;
          position: relative;
          overflow: hidden;
        }
        .hero-grid {
          display: grid;
          grid-template-columns: 1.15fr 0.85fr;
          gap: 40px;
          align-items: center;
          margin-bottom: 80px;
        }
        .hero-badge {
          margin-bottom: 24px;
        }
        .hero-title {
          font-size: 3.8rem;
          font-weight: 800;
          letter-spacing: -0.035em;
          line-height: 1.1;
          margin-bottom: 22px;
          color: #ffffff;
        }
        .text-highlight {
          color: #ffffff;
        }
        .hero-description {
          font-size: 1.1rem;
          color: var(--text-secondary);
          line-height: 1.65;
          margin-bottom: 34px;
          max-width: 540px;
        }
        .hero-actions {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .hero-visual {
          position: relative;
          display: flex;
          justify-content: center;
          align-items: center;
        }
        .hero-img-wrap {
          position: relative;
          width: 100%;
          max-width: 480px;
          display: flex;
          justify-content: center;
        }
        .hero-3d-img {
          width: 100%;
          height: auto;
          object-fit: contain;
          filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.9));
          animation: floatHero 6s ease-in-out infinite;
        }
        .hero-img-glow {
          position: absolute;
          width: 80%;
          height: 80%;
          background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%);
          top: 10%;
          left: 10%;
          pointer-events: none;
          z-index: -1;
        }
        @keyframes floatHero {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-12px) rotate(1deg); }
        }

        /* Stats Strip */
        .hero-stats-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 34px 44px;
          border-radius: 20px;
          background: rgba(13, 15, 21, 0.7);
          border: 1px solid var(--border-subtle);
          margin-bottom: 60px;
          backdrop-filter: blur(12px);
        }
        .stat-unit {
          display: flex;
          align-items: baseline;
          gap: 12px;
        }
        .stat-num {
          font-family: var(--font-display);
          font-size: 2.2rem;
          font-weight: 800;
          color: #ffffff;
          letter-spacing: -0.02em;
        }
        .stat-desc {
          font-size: 0.85rem;
          color: var(--text-secondary);
          font-weight: 500;
        }
        .stat-sep {
          width: 1px;
          height: 36px;
          background: var(--border-subtle);
        }

        /* Partners Logo Strip */
        .hero-partners-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 24px;
          padding: 20px 0;
          opacity: 0.6;
          transition: opacity var(--transition-fast);
        }
        .hero-partners-strip:hover {
          opacity: 0.9;
        }
        .partner-name {
          font-family: var(--font-display);
          font-size: 1.1rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          color: var(--text-secondary);
          text-transform: uppercase;
        }

        @media (max-width: 1024px) {
          .hero-grid {
            grid-template-columns: 1fr;
            text-align: center;
          }
          .hero-title {
            font-size: 2.8rem;
          }
          .hero-description {
            margin: 0 auto 30px;
          }
          .hero-actions {
            justify-content: center;
          }
          .hero-stats-strip {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            padding: 24px;
          }
          .stat-sep {
            display: none;
          }
        }

        @media (max-width: 640px) {
          .hero-title {
            font-size: 2.2rem;
          }
          .hero-stats-strip {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  );
}
