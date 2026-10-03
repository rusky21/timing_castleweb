import React from 'react';
import './Navbar.css';

export const Navbar: React.FC = () => {
  const scrollToSection = (id: string) => {
    if (window.__lenis) {
      window.__lenis.scrollTo(id, { offset: -70, duration: 1.2 });
    } else {
      const el = document.querySelector(id);
      if (el) {
        const top = el.getBoundingClientRect().top + window.scrollY - 70;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    }
  };

  return (
    <header className="hero-navbar-wrapper" role="banner">
      <div className="hero-navbar">
        <nav className="hero-nav-links" aria-label="Main Navigation">
          <a
            href="#showcase"
            className="hero-nav-link"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection('#showcase');
            }}
          >
            Solutions
          </a>
          <a
            href="#benefits"
            className="hero-nav-link"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection('#benefits');
            }}
          >
            Insight
          </a>
          <a
            href="#process"
            className="hero-nav-link"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection('#process');
            }}
          >
            About
          </a>
          <a
            href="#contact"
            className="hero-nav-link"
            onClick={(e) => {
              e.preventDefault();
              scrollToSection('#contact');
            }}
          >
            Contact
          </a>
        </nav>

        <div className="hero-nav-logo">Castleweb</div>

        <button
          className="hero-pill-btn hero-nav-btn"
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
    </header>
  );
};

export default Navbar;
