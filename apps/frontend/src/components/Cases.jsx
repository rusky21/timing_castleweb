import React, { useState, useEffect } from 'react';
import { ArrowUpRight, X } from 'lucide-react';

const STATIC_CASES = [
  {
    id: 1,
    title: 'FinTrack AI — B2B платформа для финтеха',
    category: 'SAAS',
    short_description: 'Высоконагруженная система обработки финансовых транзакций в реальном времени с автоматической генерацией отчетности.',
    problem: 'Клиент терял пользователей из-за медленной отрисовки графиков при загрузке более 1 000 000 строк транзакций.',
    solution_fe: 'Виртуализированный Canvas/WebGL рендеринг графиков, кэширование на клиенте через IndexedDB, мгновенный отклик.',
    solution_be: 'Асинхронный бэкенд на FastAPI с пулом asyncpg, шардирование таблиц PostgreSQL, L2 кэш Redis.',
    metrics: { 'speed_up': '75x быстрее', 'tps_handled': '12 500 TPS', 'latency_p99': '180ms' },
    cover_image: '/case1.jpg',
    author: 'Александр Воронов',
    author_role: 'Lead Architect'
  },
  {
    id: 2,
    title: 'Vanguard Living — Премиальный 3D E-commerce',
    category: 'ECOMMERCE 3D',
    short_description: 'E-commerce платформа с интерактивным конфигурированием материалов в реальном времени и синхронизацией с 1С.',
    problem: 'Старый сайт зависал при одновременном открытии 3D-моделей на мобильных устройствах и не справлялся с 5 000 SKU.',
    solution_fe: 'Гидратация Three.js компонентов только при попадании во вьюпорт, мгновенный поиск с автодополнением.',
    solution_be: 'Каталог на PostgreSQL с полнотекстовым поиском, фоновая синхронизация с 1C через очереди сообщений.',
    metrics: { 'lighthouse': '97/100', 'conversion': '+68%', 'sync_speed': '1.2s' },
    cover_image: '/case2.jpg',
    author: 'Елена Романова',
    author_role: 'Creative Director'
  },
  {
    id: 3,
    title: 'CyberShield — Центр мониторинга киберинцидентов',
    category: 'HIGHLOAD',
    short_description: 'Внутренний портал мониторинга сетевых аномалий и DDoS-атак для аналитиков информационной безопасности.',
    problem: 'Разрозненные инструменты мониторинга не позволяли оперативно реагировать на всплески трафика.',
    solution_fe: 'Интерфейс высокой информационной плотности с WebSocket-стримингом событий в реальном времени.',
    solution_be: 'FastAPI с Redis Pub/Sub шиной данных, асинхронный консьюмер сетевых логов, интеграция с Telegram.',
    metrics: { 'mttr': '-94%', 'throughput': '50K msg/sec', 'uptime': '100%' },
    cover_image: '/case3.jpg',
    author: 'Михаил Краснов',
    author_role: 'Head of Security'
  }
];

export default function Cases() {
  const [cases, setCases] = useState(STATIC_CASES);
  const [selectedCase, setSelectedCase] = useState(null);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const res = await fetch('/api/v1/cases');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length >= 3) {
            setCases(data.map((c, idx) => ({
              ...c,
              cover_image: `/case${(idx % 3) + 1}.jpg`,
              author: c.client_author || 'Lead Architect',
              author_role: 'CASTLEWEB Studio'
            })));
          }
        }
      } catch {
        // Fallback
      }
    };
    fetchCases();
  }, []);

  return (
    <section className="cases-section" id="cases">
      <div className="container">
        {/* Section Header */}
        <div className="cases-head text-center">
          <div className="badge-capsule">
            <span className="badge-icon">✦</span>
            <span>PORTFOLIO & CASES</span>
          </div>
          <h2 className="cases-title">
            Read our most recent projects
          </h2>
          <p className="cases-sub">
            Архитектурные разборы проектов, которые работают под реальной нагрузкой в продакшне.
          </p>
        </div>

        {/* 3-Column Card Grid (Salesrocket style) */}
        <div className="cases-grid">
          {cases.slice(0, 3).map((item) => (
            <div 
              key={item.id} 
              className="dark-card case-card"
              onClick={() => setSelectedCase(item)}
            >
              <div className="case-img-box">
                <img src={item.cover_image} alt={item.title} className="case-img" />
                <div className="case-arrow-btn">
                  <ArrowUpRight size={18} />
                </div>
              </div>

              <div className="case-body">
                <span className="case-category-pill">{item.category}</span>
                <h3 className="case-card-title">{item.title}</h3>
                <p className="case-card-desc">{item.short_description}</p>
                
                {/* Author footer */}
                <div className="case-author-strip">
                  <div className="author-avatar-circ">
                    {item.author.charAt(0)}
                  </div>
                  <div>
                    <span className="author-name">{item.author}</span>
                    <span className="author-role">{item.author_role}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Modal for Full Architecture Details */}
        {selectedCase && (
          <div className="case-modal-backdrop" onClick={() => setSelectedCase(null)}>
            <div className="case-modal-box dark-card" onClick={e => e.stopPropagation()}>
              <button className="case-modal-close" onClick={() => setSelectedCase(null)}>
                <X size={20} />
              </button>

              <div className="modal-head">
                <span className="case-category-pill">{selectedCase.category}</span>
                <h2 className="modal-title">{selectedCase.title}</h2>
              </div>

              <div className="modal-grid">
                <div className="modal-section">
                  <h4 className="modal-sub">Проблема и вызов:</h4>
                  <p>{selectedCase.problem}</p>
                </div>
                <div className="modal-section">
                  <h4 className="modal-sub">Инженерное решение (Frontend):</h4>
                  <p>{selectedCase.solution_fe}</p>
                </div>
                <div className="modal-section">
                  <h4 className="modal-sub">Инженерное решение (Backend):</h4>
                  <p>{selectedCase.solution_be}</p>
                </div>
              </div>

              {selectedCase.metrics && (
                <div className="modal-metrics-strip">
                  {Object.entries(selectedCase.metrics).map(([k, v]) => (
                    <div key={k} className="metric-pill">
                      <span className="metric-key">{k}:</span>
                      <span className="metric-val">{v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`
        .cases-section {
          padding: 80px 0 110px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .cases-head {
          max-width: 660px;
          margin: 0 auto 50px;
        }
        .cases-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
        }
        .cases-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }
        .cases-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        .case-card {
          padding: 16px;
          cursor: pointer;
        }
        .case-img-box {
          position: relative;
          width: 100%;
          height: 220px;
          border-radius: 14px;
          overflow: hidden;
          margin-bottom: 20px;
          background: #000000;
        }
        .case-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.4s ease;
        }
        .case-card:hover .case-img {
          transform: scale(1.05);
        }
        .case-arrow-btn {
          position: absolute;
          top: 14px;
          right: 14px;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: rgba(0, 0, 0, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          backdrop-filter: blur(8px);
          transition: all 0.2s ease;
        }
        .case-card:hover .case-arrow-btn {
          background: #ffffff;
          color: #000000;
          transform: rotate(45deg);
        }
        .case-body {
          padding: 6px 8px 12px;
        }
        .case-category-pill {
          display: inline-block;
          font-size: 0.72rem;
          font-weight: 700;
          color: var(--accent-emerald);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 10px;
        }
        .case-card-title {
          font-size: 1.15rem;
          line-height: 1.4;
          margin-bottom: 10px;
          color: #ffffff;
        }
        .case-card-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.55;
          margin-bottom: 20px;
        }
        .case-author-strip {
          display: flex;
          align-items: center;
          gap: 12px;
          padding-top: 16px;
          border-top: 1px solid var(--border-subtle);
        }
        .author-avatar-circ {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.85rem;
          color: #ffffff;
        }
        .author-name {
          display: block;
          font-size: 0.85rem;
          font-weight: 600;
          color: #ffffff;
        }
        .author-role {
          display: block;
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        /* Modal */
        .case-modal-backdrop {
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
        .case-modal-box {
          max-width: 680px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          position: relative;
          padding: 40px;
        }
        .case-modal-close {
          position: absolute;
          top: 20px;
          right: 20px;
          color: var(--text-secondary);
          transition: color 0.2s;
        }
        .case-modal-close:hover {
          color: #ffffff;
        }
        .modal-title {
          font-size: 1.8rem;
          margin: 10px 0 24px;
        }
        .modal-grid {
          display: flex;
          flex-direction: column;
          gap: 18px;
          margin-bottom: 24px;
        }
        .modal-sub {
          font-size: 0.95rem;
          color: #ffffff;
          margin-bottom: 6px;
        }
        .modal-metrics-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          padding-top: 20px;
          border-top: 1px solid var(--border-subtle);
        }
        .metric-pill {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 0.8rem;
          font-family: var(--font-mono);
        }
        .metric-val {
          color: var(--accent-emerald);
          font-weight: 600;
          margin-left: 6px;
        }

        @media (max-width: 960px) {
          .cases-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  );
}
