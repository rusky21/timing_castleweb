import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Features from './components/Features';
import Integrations from './components/Integrations';
import Cases from './components/Cases';
import Calculator from './components/Calculator';
import Architecture from './components/Architecture';
import FAQ from './components/FAQ';
import ContactForm from './components/ContactForm';
import Footer from './components/Footer';

export default function App() {
  const [estimateData, setEstimateData] = useState({
    budget: '',
    summary: '',
    projectType: ''
  });

  const [modalOpen, setModalOpen] = useState(false);

  const handleApplyConfig = (config) => {
    setEstimateData({
      budget: config.budget,
      summary: config.summary,
      projectType: config.projectType
    });

    const contactElem = document.getElementById('contact');
    if (contactElem) {
      contactElem.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleOpenContactModal = () => {
    const contactElem = document.getElementById('contact');
    if (contactElem) {
      contactElem.scrollIntoView({ behavior: 'smooth' });
    } else {
      setModalOpen(true);
    }
  };

  return (
    <div className="app-layout">
      {/* Fixed Navbar with live latency */}
      <Navbar onOpenContact={handleOpenContactModal} />

      <main id="main-content">
        {/* 1. Hero with 3D Chrome Sculpture & Stats */}
        <Hero 
          onOpenContact={handleOpenContactModal} 
          onExploreCases={() => {
            const casesElem = document.getElementById('cases');
            if (casesElem) casesElem.scrollIntoView({ behavior: 'smooth' });
          }} 
        />

        {/* 2. Features: 3 Cards + Split Rows + Analytics Card */}
        <Features onOpenContact={handleOpenContactModal} />

        {/* 3. Orbit Integration Constellation */}
        <Integrations />

        {/* 4. Recent Works & Projects (3 Cards with 3D Artworks) */}
        <Cases />

        {/* 5. Pricing Tiers & Interactive Calculator */}
        <Calculator onApplyConfig={handleApplyConfig} />

        {/* 6. Clean Architecture & Cost Comparison Table */}
        <Architecture />

        {/* 7. Frequently Asked Questions */}
        <FAQ />

        {/* 8. Contact Form with Telegram CRM & File Upload */}
        <section className="contact-section" id="contact">
          <div className="container">
            <div className="contact-wrapper">
              <ContactForm 
                prefillBudget={estimateData.budget}
                prefillSummary={estimateData.summary}
                prefillType={estimateData.projectType}
              />
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <Footer onOpenContact={handleOpenContactModal} />

      {/* Modal Backdrop */}
      {modalOpen && (
        <div className="modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="modal-inner" onClick={e => e.stopPropagation()}>
            <ContactForm 
              prefillBudget={estimateData.budget}
              prefillSummary={estimateData.summary}
              prefillType={estimateData.projectType}
              isModal={true}
              onClose={() => setModalOpen(false)}
            />
          </div>
        </div>
      )}

      <style>{`
        .app-layout {
          position: relative;
          min-height: 100vh;
          background: #000000;
        }
        .contact-section {
          padding: 80px 0 120px;
          position: relative;
        }
        .contact-wrapper {
          max-width: 820px;
          margin: 0 auto;
        }
        .modal-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(14px);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .modal-inner {
          position: relative;
          z-index: 1001;
        }
      `}</style>
    </div>
  );
}
