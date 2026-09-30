import React from 'react';
import { Shield, Send, Mail, ArrowUp, ExternalLink } from 'lucide-react';

const CURRENT_YEAR = new Date().getFullYear();

function GithubIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

export default function Footer({ onOpenContact }) {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="footer-wrap">
      <div className="container">
        {/* Top Footer Banner */}
        <div className="footer-cta-banner glass-card">
          <div className="footer-cta-text">
            <h3>Готовы обсудить архитектуру вашего проекта?</h3>
            <p>Дежурный архитектор ответит на вопросы по стеку и подготовит детальный расчет в течение 15 минут.</p>
          </div>
          <button className="btn-primary" onClick={onOpenContact} id="footer-cta-btn">
            <span>Обсудить задачу</span>
            <Send size={16} />
          </button>
        </div>

        {/* Main Footer Links */}
        <div className="footer-grid">
          {/* Col 1: Brand & Bio */}
          <div className="footer-col brand-col">
            <div className="brand-logo footer-logo">
              <div className="logo-icon-box">
                <Shield className="logo-icon" size={20} />
              </div>
              <div className="brand-text">
                <span className="brand-title">CASTLE<span className="brand-highlight">WEB</span></span>
                <span className="brand-subtitle">ENGINEERING STUDIO</span>
              </div>
            </div>
            <p className="footer-bio">
              Инженерная разработка высоконагруженных веб-сервисов, 3D E-commerce и B2B платформ. 
              Zero-cost инфраструктура, чистый код и автономность для бизнеса.
            </p>
            <div className="footer-socials">
              <a href="https://t.me" target="_blank" rel="noopener noreferrer" className="social-btn" title="Telegram">
                <Send size={16} />
              </a>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="social-btn" title="GitHub">
                <GithubIcon size={16} />
              </a>
              <a href="mailto:dev@castleweb.ru" className="social-btn" title="Email">
                <Mail size={16} />
              </a>
            </div>
          </div>

          {/* Col 2: Navigation */}
          <div className="footer-col">
            <h5 className="footer-heading">Навигация</h5>
            <ul className="footer-links">
              <li><a href="#hero">Главная</a></li>
              <li><a href="#cases">Кейсы и проекты</a></li>
              <li><a href="#calculator">Калькулятор сметы</a></li>
              <li><a href="#architecture">Стек & Архитектура</a></li>
              <li><a href="#about">О студии</a></li>
            </ul>
          </div>

          {/* Col 3: Tech & API */}
          <div className="footer-col">
            <h5 className="footer-heading">Инженерия & API</h5>
            <ul className="footer-links">
              <li>
                <a href="/api/v1/status" target="_blank" rel="noopener noreferrer" className="link-with-icon">
                  <span>Статус систем (JSON)</span>
                  <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="/docs" target="_blank" rel="noopener noreferrer" className="link-with-icon">
                  <span>Swagger / OpenAPI v3</span>
                  <ExternalLink size={12} />
                </a>
              </li>
              <li>
                <a href="#architecture">Clean Architecture</a>
              </li>
              <li>
                <a href="#architecture">0 ₽ Cloudflare R2</a>
              </li>
            </ul>
          </div>

          {/* Col 4: Contacts & Telemetry */}
          <div className="footer-col">
            <h5 className="footer-heading">Прямая связь</h5>
            <p className="contact-line">
              <span className="text-muted">Дежурный инженер:</span><br />
              <strong className="text-white">@castleweb_lead</strong>
            </p>
            <p className="contact-line">
              <span className="text-muted">Почта для брифов:</span><br />
              <span className="font-mono text-cyan">engineering@castleweb.dev</span>
            </p>
            <div className="footer-badge-online">
              <span className="pulse-beacon" />
              <span>SLA Гарантия доступности 99.98%</span>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom">
          <div className="footer-copy">
            © {CURRENT_YEAR} CASTLEWEB Studio. Все права защищены. Разработано с фокусом на Highload & Security.
          </div>
          <button onClick={scrollToTop} className="scroll-top-btn" title="Наверх">
            <ArrowUp size={16} />
            <span>Наверх</span>
          </button>
        </div>
      </div>

      <style>{`
        .footer-wrap {
          background: #040508;
          border-top: 1px solid var(--border-subtle);
          padding: 60px 0 30px;
          position: relative;
          z-index: 1;
        }
        .footer-cta-banner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 36px 44px;
          border-radius: 20px;
          margin-bottom: 60px;
          border: 1px solid var(--border-glow);
          gap: 30px;
          background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(14, 18, 28, 0.8) 100%);
        }
        .footer-cta-text h3 {
          font-size: 1.6rem;
          margin-bottom: 8px;
        }
        .footer-cta-text p {
          color: var(--text-secondary);
          font-size: 0.95rem;
          max-width: 600px;
        }
        .footer-grid {
          display: grid;
          grid-template-columns: 1.5fr 1fr 1fr 1fr;
          gap: 40px;
          padding-bottom: 50px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .footer-logo {
          margin-bottom: 16px;
        }
        .footer-bio {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.6;
          margin-bottom: 20px;
          max-width: 320px;
        }
        .footer-socials {
          display: flex;
          gap: 10px;
        }
        .social-btn {
          width: 38px;
          height: 38px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-secondary);
          transition: all var(--transition-fast);
        }
        .social-btn:hover {
          color: #ffffff;
          background: rgba(99, 102, 241, 0.2);
          border-color: var(--accent-indigo);
          transform: translateY(-2px);
        }
        .footer-heading {
          font-size: 0.95rem;
          color: #ffffff;
          font-weight: 700;
          margin-bottom: 18px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .footer-links {
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .footer-links a {
          color: var(--text-secondary);
          font-size: 0.88rem;
          transition: color var(--transition-fast);
        }
        .footer-links a:hover {
          color: #ffffff;
        }
        .link-with-icon {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .contact-line {
          font-size: 0.88rem;
          margin-bottom: 14px;
          line-height: 1.4;
        }
        .footer-badge-online {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.78rem;
          color: var(--accent-emerald);
          font-family: var(--font-mono);
          margin-top: 18px;
        }
        .footer-bottom {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 24px;
          font-size: 0.82rem;
          color: var(--text-muted);
        }
        .scroll-top-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          color: var(--text-secondary);
          font-size: 0.82rem;
          transition: color var(--transition-fast);
        }
        .scroll-top-btn:hover {
          color: #ffffff;
        }

        @media (max-width: 960px) {
          .footer-cta-banner {
            flex-direction: column;
            align-items: flex-start;
            padding: 24px;
          }
          .footer-grid {
            grid-template-columns: 1fr 1fr;
            gap: 30px;
          }
        }
        @media (max-width: 640px) {
          .footer-grid {
            grid-template-columns: 1fr;
          }
          .footer-bottom {
            flex-direction: column;
            gap: 16px;
            text-align: center;
          }
        }
      `}</style>
    </footer>
  );
}
