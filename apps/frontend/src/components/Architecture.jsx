import React, { useState } from 'react';
import { 
  Server, 
  Database, 
  Layers, 
  Zap, 
  ShieldCheck, 
  Cpu, 
  Cloud, 
  Send, 
  CheckCircle2, 
  Lock, 
  Activity, 
  Terminal,
  Code2
} from 'lucide-react';

const ARCH_LAYERS = [
  {
    id: 'presentation',
    name: '1. Presentation Layer (API & Gateway)',
    icon: Server,
    color: '#06b6d4',
    desc: 'Чистые контроллеры FastAPI, валидация входных данных через Pydantic v2, Swagger/OpenAPI спецификация.',
    points: [
      'Асинхронные роуты без блокировки event loop',
      'Встроенный Token Bucket Rate Limiter (защита от спама и парсеров)',
      'Автоматическая генерация клиентских SDK через OpenAPI'
    ]
  },
  {
    id: 'domain',
    name: '2. Domain & Application Core',
    icon: Layers,
    color: '#8b5cf6',
    desc: 'Бизнес-логика, изолированная от фреймворков и баз данных. Чистые сущности и DTO.',
    points: [
      'Полная тестируемость (Unit тесты выполняются за миллисекунды)',
      'Строгая типизация Python 3.12 (mypy strict)',
      'Независимость от поставщиков сторонних решений'
    ]
  },
  {
    id: 'infrastructure',
    name: '3. Infrastructure & Highload Cache',
    icon: Database,
    color: '#10b981',
    desc: 'Высокоскоростная персистентность на PostgreSQL 16 + Redis 7 L2 кэш.',
    points: [
      'Пул неблокирующих соединений asyncpg (до 15 000 RPS)',
      'Асинхронные миграции БД через Alembic с версионированием',
      'Redis LRU кэширование горячих выборок с субмиллисекундным пингом'
    ]
  },
  {
    id: 'crm',
    name: '4. Telegram Headless CRM & Storage',
    icon: Send,
    color: '#ec4899',
    desc: 'Управление лидами прямо в защищенном Telegram-чате команды с нулевой стоимостью лицензий.',
    points: [
      'Асинхронный воркер доставки заявок с автоповторами (exponential backoff)',
      'Интерактивные Inline-кнопки для смены статусов (В работе / Завершено)',
      'Cloudflare R2 хранилище ТЗ и файлов с 0 ₽ за исходящий трафик'
    ]
  }
];

const COMPARISON_METRICS = [
  {
    metric: 'Месячные расходы на SaaS/CRM',
    studio: '0 ₽ / мес',
    others: 'от 12 000 ₽ / мес (Битрикс24 / AmoCRM)',
    benefit: 'Telegram CRM без абонентской платы'
  },
  {
    metric: 'Раздача файлов и медиа (CDN)',
    studio: '0 ₽ (Cloudflare R2, 0 egress fee)',
    others: 'от 3 000 ₽ / мес за каждый терабайт',
    benefit: 'Бесплатный исходящий трафик'
  },
  {
    metric: 'Время холодного старта API',
    studio: '< 80 ms (FastAPI + Uvicorn)',
    others: '1 500 — 3 000 ms (тяжелые CMS/Django)',
    benefit: 'Мгновенный отклик для пользователей'
  },
  {
    metric: 'Владение кодом и развертывание',
    studio: '100% On-Premise Docker на вашем сервере',
    others: 'Привязка к закрытым конструкторам',
    benefit: 'Никакой блокировки или привязки'
  }
];

export default function Architecture() {
  const [activeLayer, setActiveLayer] = useState('presentation');

  return (
    <section className="arch-section" id="architecture">
      <div className="container">
        {/* Section Header */}
        <div className="section-head text-center">
          <div className="badge badge-glow">ИНЖЕНЕРНАЯ ФИЛОСОФИЯ</div>
          <h2 className="section-title">
            Архитектура, созданная для <span className="gradient-text">Highload & 0 ₽ издержек</span>
          </h2>
          <p className="section-desc">
            Никаких перегруженных конструкторов или раздутых подписок. 
            Только чистый код, асинхронные микросервисы и серверные технологии мирового класса.
          </p>
        </div>

        {/* Clean Architecture Visual Layers */}
        <div className="arch-interactive-box glass-card">
          <div className="arch-tabs-nav">
            {ARCH_LAYERS.map(layer => {
              const Icon = layer.icon;
              const isActive = activeLayer === layer.id;
              return (
                <button
                  key={layer.id}
                  onClick={() => setActiveLayer(layer.id)}
                  className={`arch-tab-btn ${isActive ? 'active' : ''}`}
                  style={{
                    '--tab-color': layer.color
                  }}
                >
                  <Icon size={18} />
                  <span>{layer.name.split(' (')[0]}</span>
                </button>
              );
            })}
          </div>

          <div className="arch-tab-content">
            {ARCH_LAYERS.map(layer => {
              if (layer.id !== activeLayer) return null;
              const Icon = layer.icon;
              return (
                <div key={layer.id} className="arch-detail-card">
                  <div className="arch-detail-header">
                    <div 
                      className="arch-icon-wrap" 
                      style={{ background: `${layer.color}15`, borderColor: `${layer.color}40`, color: layer.color }}
                    >
                      <Icon size={26} />
                    </div>
                    <div>
                      <h3 className="arch-layer-title">{layer.name}</h3>
                      <p className="arch-layer-desc">{layer.desc}</p>
                    </div>
                  </div>

                  <div className="arch-points-grid">
                    {layer.points.map((pt, i) => (
                      <div key={i} className="arch-point-item">
                        <CheckCircle2 size={16} style={{ color: layer.color }} className="point-icon" />
                        <span>{pt}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Zero-Cost Comparison Table */}
        <div className="comparison-wrap">
          <h3 className="comparison-title text-center">
            Экономика проекта: <span className="gradient-text-cyan">CASTLEWEB vs Типовые веб-студии</span>
          </h3>

          <div className="comparison-table-card glass-card">
            <div className="table-header-row">
              <div className="th-cell th-metric">Параметр архитектуры</div>
              <div className="th-cell th-studio">CASTLEWEB Architecture</div>
              <div className="th-cell th-others">Обычные студии / CMS</div>
              <div className="th-cell th-benefit">Ваша выгода</div>
            </div>

            <div className="table-body">
              {COMPARISON_METRICS.map((row, idx) => (
                <div key={idx} className="table-row">
                  <div className="td-cell td-metric">
                    <strong>{row.metric}</strong>
                  </div>
                  <div className="td-cell td-studio">
                    <span className="badge-highlight-green">{row.studio}</span>
                  </div>
                  <div className="td-cell td-others">
                    <span className="text-muted">{row.others}</span>
                  </div>
                  <div className="td-cell td-benefit">
                    <span className="text-benefit">
                      <Zap size={13} className="inline-icon text-cyan" /> {row.benefit}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Tech Stack Grid */}
        <div className="stack-grid">
          <div className="stack-card glass-card">
            <div className="stack-head">
              <Server size={20} className="text-cyan" />
              <h4>Backend & Data</h4>
            </div>
            <p className="stack-desc">Python 3.12, FastAPI, SQLAlchemy 2.0 Async, PostgreSQL 16, Redis 7, Alembic</p>
            <div className="stack-tags">
              <span className="tag">FastAPI</span>
              <span className="tag">PostgreSQL 16</span>
              <span className="tag">Redis 7</span>
              <span className="tag">Pydantic v2</span>
              <span className="tag">Asyncpg</span>
            </div>
          </div>

          <div className="stack-card glass-card">
            <div className="stack-head">
              <Code2 size={20} className="text-indigo" />
              <h4>Frontend & 3D Web</h4>
            </div>
            <p className="stack-desc">React 19, Vite, Three.js / WebGL, CSS Design Tokens, Lucide Icons, Vanilla Architecture</p>
            <div className="stack-tags">
              <span className="tag">React 19</span>
              <span className="tag">Vite 6</span>
              <span className="tag">Three.js</span>
              <span className="tag">Vanilla CSS</span>
              <span className="tag">Lighthouse 95+</span>
            </div>
          </div>

          <div className="stack-card glass-card">
            <div className="stack-head">
              <ShieldCheck size={20} className="text-emerald" />
              <h4>DevOps, WAF & Storage</h4>
            </div>
            <p className="stack-desc">Docker Compose, Nginx, Certbot SSL, Cloudflare Turnstile & R2, Telegram Bot API</p>
            <div className="stack-tags">
              <span className="tag">Docker</span>
              <span className="tag">Nginx</span>
              <span className="tag">Cloudflare R2</span>
              <span className="tag">Telegram API</span>
              <span className="tag">Certbot SSL</span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .arch-section {
          padding: 100px 0;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .section-head {
          max-width: 760px;
          margin: 0 auto 50px;
        }
        .section-title {
          font-size: 2.5rem;
          margin-top: 14px;
          margin-bottom: 16px;
        }
        .section-desc {
          font-size: 1.1rem;
          color: var(--text-secondary);
          line-height: 1.6;
        }
        .arch-interactive-box {
          padding: 30px;
          border-radius: 20px;
          margin-bottom: 70px;
          border: 1px solid var(--border-glow);
        }
        .arch-tabs-nav {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 28px;
          padding-bottom: 20px;
          border-bottom: 1px solid var(--border-subtle);
        }
        .arch-tab-btn {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 18px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          color: var(--text-secondary);
          font-size: 0.9rem;
          font-weight: 600;
          text-align: left;
          transition: all var(--transition-fast);
        }
        .arch-tab-btn:hover {
          background: rgba(255, 255, 255, 0.06);
          color: #ffffff;
        }
        .arch-tab-btn.active {
          background: rgba(99, 102, 241, 0.15);
          border-color: var(--tab-color, var(--accent-indigo));
          color: #ffffff;
          box-shadow: 0 0 20px -5px rgba(99, 102, 241, 0.4);
        }
        .arch-tab-btn.active svg {
          color: var(--tab-color, var(--accent-indigo));
        }
        .arch-detail-header {
          display: flex;
          align-items: flex-start;
          gap: 20px;
          margin-bottom: 24px;
        }
        .arch-icon-wrap {
          width: 56px;
          height: 56px;
          border-radius: 14px;
          border: 1px solid;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .arch-layer-title {
          font-size: 1.4rem;
          margin-bottom: 6px;
        }
        .arch-layer-desc {
          font-size: 0.95rem;
          color: var(--text-secondary);
          line-height: 1.5;
        }
        .arch-points-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
        }
        .arch-point-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 14px 16px;
          background: rgba(8, 10, 16, 0.6);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          font-size: 0.88rem;
          color: var(--text-primary);
          line-height: 1.4;
        }
        .point-icon {
          flex-shrink: 0;
          margin-top: 2px;
        }
        .comparison-wrap {
          margin-bottom: 70px;
        }
        .comparison-title {
          font-size: 1.8rem;
          margin-bottom: 30px;
        }
        .comparison-table-card {
          border-radius: 20px;
          overflow: hidden;
          border: 1px solid var(--border-subtle);
        }
        .table-header-row {
          display: grid;
          grid-template-columns: 1.4fr 1.2fr 1.4fr 1.2fr;
          padding: 16px 24px;
          background: rgba(14, 18, 28, 0.9);
          border-bottom: 1px solid var(--border-subtle);
          font-weight: 700;
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--text-muted);
        }
        .table-row {
          display: grid;
          grid-template-columns: 1.4fr 1.2fr 1.4fr 1.2fr;
          padding: 18px 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.04);
          align-items: center;
          font-size: 0.9rem;
          transition: background var(--transition-fast);
        }
        .table-row:last-child {
          border-bottom: none;
        }
        .table-row:hover {
          background: rgba(255, 255, 255, 0.02);
        }
        .badge-highlight-green {
          font-family: var(--font-mono);
          font-weight: 700;
          color: var(--accent-emerald);
          background: rgba(16, 185, 129, 0.12);
          border: 1px solid rgba(16, 185, 129, 0.3);
          padding: 4px 10px;
          border-radius: 8px;
          display: inline-block;
        }
        .text-benefit {
          color: var(--text-primary);
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .stack-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        .stack-card {
          padding: 28px;
          border-radius: 18px;
          border: 1px solid var(--border-subtle);
          transition: transform var(--transition-fast), border-color var(--transition-fast);
        }
        .stack-card:hover {
          transform: translateY(-4px);
          border-color: var(--border-glow);
        }
        .stack-head {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }
        .stack-head h4 {
          font-size: 1.2rem;
          color: #ffffff;
        }
        .stack-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          margin-bottom: 18px;
          line-height: 1.5;
        }
        .stack-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .tag {
          font-size: 0.75rem;
          font-family: var(--font-mono);
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          padding: 4px 10px;
          border-radius: 6px;
          color: var(--text-secondary);
        }
        .text-cyan { color: var(--accent-cyan); }
        .text-indigo { color: var(--accent-indigo); }
        .text-emerald { color: var(--accent-emerald); }

        @media (max-width: 1024px) {
          .arch-tabs-nav {
            grid-template-columns: repeat(2, 1fr);
          }
          .arch-points-grid {
            grid-template-columns: 1fr;
          }
          .table-header-row, .table-row {
            grid-template-columns: 1fr 1fr;
            gap: 12px;
          }
          .th-others, .td-others, .th-benefit, .td-benefit {
            display: none;
          }
          .stack-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 640px) {
          .arch-tabs-nav {
            grid-template-columns: 1fr;
          }
          .section-title {
            font-size: 1.8rem;
          }
          .arch-detail-header {
            flex-direction: column;
            gap: 14px;
          }
        }
      `}</style>
    </section>
  );
}
