import React from 'react';
import DottedBackground from './DottedBackground';
import './Hero.css';

export const Hero: React.FC = () => {
  const scrollToSection = (id: string) => {
    if (window.__lenis) {
      window.__lenis.scrollTo(id, { duration: 1.2 });
    } else {
      document.querySelector(id)?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="hero-section" id="hero">
      {/* --- Ambient Effect Background --- */}
      <div className="hero-video-wrapper" aria-hidden="true">
        <DottedBackground bgColor="#0b0b0c" />
        <div className="hero-video-overlay" />
      </div>

      {/* --- Bottom Hero Content matching reference --- */}
      <div className="hero-bottom">
        <h1 className="hero-display-title">Castleweb</h1>

        <div className="hero-bottom-right">
          <p className="hero-bottom-desc">
            Студия разработки цифровых продуктов по&nbsp;всему миру. Понимаем рынок и&nbsp;задачи бизнеса, гибко подходим к&nbsp;проекту и&nbsp;создаем надежные решения без&nbsp;лишней сложности.
          </p>

          <button
            className="hero-pill-btn hero-bottom-btn"
            type="button"
            onClick={() => scrollToSection('#contact')}
            aria-label="Get Started"
          >
            <span className="hero-btn-text">Get Started</span>
            <span className="hero-btn-arrow" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path
                  d="M5 12h14M13 5l7 7-7 7"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </button>
        </div>
      </div>
    </section>
  );
};
