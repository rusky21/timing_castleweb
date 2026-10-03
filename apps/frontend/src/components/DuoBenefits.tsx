import React from 'react';
import './DuoBenefits.css';
import frontendPhoto from '../assets/team/frontend-dev.jpg';
import backendPhoto from '../assets/team/backend-dev.jpg';

export const DuoBenefits: React.FC = () => {
  return (
    <>
      {/* First Developer Block (Frontend: Emil Gerasimov) */}
      <section className="designer-intro-section" id="blog">
        {/* Anchor alias to support existing #benefits links */}
        <div id="benefits" style={{ position: 'absolute', top: 0, left: 0 }} aria-hidden="true" />

        <div className="designer-intro-container">
          {/* Left Column: Massive Condensed Name, Bio */}
          <div className="designer-intro-left reveal-void">
            <h2 className="designer-name">
              ЭМИЛЬ
              <br />
              ГЕРАСИМОВ
            </h2>
            <p className="designer-bio">
              Современный веб-интерфейс, адаптивность под любые устройства и чистый фронтенд.
            </p>
          </div>

          {/* Right Column: Location/Role Above Photo & Portrait Photo */}
          <div className="designer-intro-right reveal-void delay-200">
            <div className="designer-location">
              <span>Москва</span>
              <span>Frontend</span>
            </div>

            <div className="designer-photo-wrap">
              <img
                src={frontendPhoto}
                alt="Эмиль Герасимов"
                className="designer-photo"
                loading="lazy"
                draggable={false}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Second Developer Block (Backend: Oleg Sudakov - Reversed Composition) */}
      <section className="designer-intro-section designer-intro-section-second">
        <div className="designer-intro-container designer-intro-container-reversed">
          {/* Left Column: Location/Role Above Photo & Portrait Photo */}
          <div className="designer-intro-photo-col reveal-void">
            <div className="designer-location">
              <span>Москва</span>
              <span>Backend</span>
            </div>

            <div className="designer-photo-wrap">
              <img
                src={backendPhoto}
                alt="Олег Судаков"
                className="designer-photo"
                loading="lazy"
                draggable={false}
              />
            </div>
          </div>

          {/* Right Column: Massive Condensed Name, Bio */}
          <div className="designer-intro-text-col reveal-void delay-200">
            <h2 className="designer-name">
              ОЛЕГ
              <br />
              СУДАКОВ
            </h2>
            <p className="designer-bio">
              Чистая серверная архитектура, быстрые SQL-запросы и чистый код без костылей.
            </p>
          </div>
        </div>
      </section>
    </>
  );
};

export default DuoBenefits;
