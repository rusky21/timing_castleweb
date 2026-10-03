import React, { useEffect } from 'react';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { TheoShowcase } from './components/TheoShowcase';
import { DuoBenefits } from './components/DuoBenefits';
import { WorkProcess } from './components/WorkProcess';
import { FaqSection } from './components/FaqSection';
import { FinalCta } from './components/FinalCta';

declare global {
  interface Window {
    __lenis?: Lenis;
  }
}

export const App: React.FC = () => {
  useEffect(() => {
    // 1. Ultra-smooth physics scrolling for the entire application
    const lenis = new Lenis({
      duration: 1.15,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.2,
      wheelMultiplier: 0.9,
    });

    window.__lenis = lenis;

    let rafId: number;
    const raf = (time: number) => {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    };
    rafId = requestAnimationFrame(raf);

    // 2. Smooth anchor navigation with Lenis (with offset for fixed pinned navbar)
    const handleAnchorClick = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest('a[href^="#"]');
      if (target) {
        const href = target.getAttribute('href');
        if (href && href.length > 1) {
          const el = document.querySelector(href);
          if (el) {
            e.preventDefault();
            lenis.scrollTo(el as HTMLElement, { offset: -70, duration: 1.2 });
          }
        }
      }
    };
    document.addEventListener('click', handleAnchorClick);

    // 3. Studio Void Reveal Observer (appearing smoothly from the void)
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed');
            revealObserver.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.08,
        rootMargin: '0px 0px -40px 0px',
      }
    );

    const observeReveals = () => {
      document
        .querySelectorAll('.reveal-void:not(.is-revealed), .reveal-void-left:not(.is-revealed), .reveal-void-right:not(.is-revealed)')
        .forEach((el) => revealObserver.observe(el));
    };

    observeReveals();

    // Re-check periodically or on DOM mutations for complete robustness
    const mutationObserver = new MutationObserver(() => {
      observeReveals();
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });

    return () => {
      cancelAnimationFrame(rafId);
      document.removeEventListener('click', handleAnchorClick);
      revealObserver.disconnect();
      mutationObserver.disconnect();
      lenis.destroy();
      delete window.__lenis;
    };
  }, []);

  return (
    <>
      {/* Global Fixed Pinned Navbar */}
      <Navbar />
      <main>
        <Hero />
        <WorkProcess />
        <TheoShowcase />
        <DuoBenefits />
        <FaqSection />
        <FinalCta />
      </main>
    </>
  );
};

export default App;

