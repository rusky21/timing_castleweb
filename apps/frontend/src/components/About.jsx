import React from 'react';
import { Shield, Target, Award, Code, CheckCircle2, HeartHandshake, GitBranch, Terminal } from 'lucide-react';

const PRINCIPLES = [
  {
    icon: Code,
    title: 'Прямой контакт с Lead Architect',
    desc: 'Вы обсуждаете архитектуру и фичи напрямую с инженерами, которые пишут код. Никаких менеджеров с испорченным телефоном.'
  },
  {
    icon: Target,
    title: 'Спринты с осязаемым результатом',
    desc: 'Каждые 7–10 дней вы получаете рабочий релиз на тестовом стенде. Полная прозрачность задач в Notion/Telegram.'
  },
  {
    icon: GitBranch,
    title: '100% владение исходным кодом',
    desc: 'Никаких закрытых конструкторов или лицензионных ловушек. Все репозитории, Dockerfile и CI/CD скрипты принадлежат вам.'
  },
  {
    icon: Shield,
    title: 'SLA и нулевые утечки данных',
    desc: 'Строгий NDA, шифрование конфигураций, отсутствие сторонних аналитических трекеров, сливающих пользовательские данные.'
  }
];

export default function About() {
  return (
    <section className="about-section" id="about">
      <div className="container">
        <div className="about-grid">
          {/* Left Column */}
          <div className="about-info">
            <div className="badge badge-glow">О СТУДИИ CASTLEWEB</div>
            <h2 className="about-title">
              Разрабатываем не просто сайты, а <span className="gradient-text">инженерные системы</span>
            </h2>
            <p className="about-lead">
              Мы объединили опыт работы в Highload-финтехе, криптографии и 3D-графике, чтобы строить веб-решения 
              без технического долга и компромиссов в безопасности.
            </p>
            <p className="about-text">
              В отличие от потоковых агентств, мы берем в работу не более 2 проектов одновременно. 
              Это гарантирует глубокое погружение в бизнес-логику и математическую точность архитектуры.
            </p>

            <div className="about-stats-row">
              <div className="stat-card">
                <span className="stat-number gradient-text">48+</span>
                <span className="stat-label">Проектов в проде</span>
              </div>
              <div className="stat-card">
                <span className="stat-number gradient-text-cyan">&lt; 15 мин</span>
                <span className="stat-label">Реакция в Telegram</span>
              </div>
              <div className="stat-card">
                <span className="stat-number text-emerald">100%</span>
                <span className="stat-label">Сдача в срок</span>
              </div>
            </div>
          </div>

          {/* Right Column: Principles Cards */}
          <div className="about-principles">
            <div className="principles-grid">
              {PRINCIPLES.map((p, idx) => {
                const Icon = p.icon;
                return (
                  <div key={idx} className="principle-card glass-card">
                    <div className="principle-icon-wrap">
                      <Icon size={22} className="principle-icon" />
                    </div>
                    <div>
                      <h4 className="principle-title">{p.title}</h4>
                      <p className="principle-desc">{p.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .about-section {
          padding: 100px 0;
          position: relative;
        }
        .about-grid {
          display: grid;
          grid-template-columns: 1.1fr 1.2fr;
          gap: 60px;
          align-items: center;
        }
        .about-title {
          font-size: 2.5rem;
          margin-top: 14px;
          margin-bottom: 20px;
          line-height: 1.2;
        }
        .about-lead {
          font-size: 1.15rem;
          color: var(--text-primary);
          line-height: 1.6;
          margin-bottom: 16px;
        }
        .about-text {
          font-size: 0.98rem;
          color: var(--text-secondary);
          line-height: 1.6;
          margin-bottom: 32px;
        }
        .about-stats-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
        }
        .stat-card {
          padding: 18px;
          background: rgba(14, 18, 28, 0.6);
          border: 1px solid var(--border-subtle);
          border-radius: 14px;
        }
        .stat-number {
          display: block;
          font-family: var(--font-display);
          font-size: 1.8rem;
          font-weight: 800;
          margin-bottom: 4px;
        }
        .stat-label {
          font-size: 0.78rem;
          color: var(--text-muted);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .principles-grid {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .principle-card {
          display: flex;
          align-items: flex-start;
          gap: 18px;
          padding: 22px;
          border-radius: 16px;
          border: 1px solid var(--border-subtle);
          transition: transform var(--transition-fast), border-color var(--transition-fast);
        }
        .principle-card:hover {
          transform: translateX(6px);
          border-color: var(--border-glow);
        }
        .principle-icon-wrap {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          background: rgba(99, 102, 241, 0.12);
          border: 1px solid rgba(99, 102, 241, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: var(--accent-indigo);
        }
        .principle-title {
          font-size: 1.05rem;
          color: #ffffff;
          margin-bottom: 6px;
        }
        .principle-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.5;
        }

        @media (max-width: 960px) {
          .about-grid {
            grid-template-columns: 1fr;
            gap: 40px;
          }
          .about-title {
            font-size: 2rem;
          }
        }
      `}</style>
    </section>
  );
}
