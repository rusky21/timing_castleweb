import React from 'react';
import { 
  TrendingUp, 
  Layers, 
  Send, 
  ShieldCheck, 
  Zap, 
  ArrowRight,
  Lock
} from 'lucide-react';

export default function Features({ onOpenContact }) {
  return (
    <section className="features-section" id="features">
      <div className="container">
        {/* Section 1: 3 Top Feature Cards (like reference) */}
        <div className="features-head text-center">
          <div className="badge-capsule">
            <span className="badge-icon">✦</span>
            <span>EXPLORE FEATURES</span>
          </div>
          <h2 className="features-title">
            Effortlessly customize <br />for your unique projects.
          </h2>
          <p className="features-sub">
            Инженерные решения, которые снимают ограничения платформ и выводят ваш бизнес на уровень глобального масштаба.
          </p>
        </div>

        <div className="feature-cards-grid">
          <div className="dark-card feature-card">
            <div className="squircle-icon">
              <TrendingUp size={22} />
            </div>
            <h3 className="card-heading">Масштабируемость & Highload</h3>
            <p className="card-paragraph">
              Архитектура с пулом соединений asyncpg, шардированием и кэшированием Redis выдерживает пиковые всплески трафика без падений.
            </p>
          </div>

          <div className="dark-card feature-card">
            <div className="squircle-icon">
              <Layers size={22} />
            </div>
            <h3 className="card-heading">Кастомные 3D & WebGL интерфейсы</h3>
            <p className="card-paragraph">
              Интерактивные конфигураторы товаров, графики данных в реальном времени и плавная анимация 60 FPS на любых устройствах.
            </p>
          </div>

          <div className="dark-card feature-card">
            <div className="squircle-icon">
              <Send size={22} />
            </div>
            <h3 className="card-heading">Telegram Headless CRM</h3>
            <p className="card-paragraph">
              Управление заявками и лидами прямо в закрытом чате команды. Полная независимость от дорогих ежемесячных подписок (0 ₽/мес).
            </p>
          </div>
        </div>

        {/* Section 2: Split Row (Left items / Right headline) */}
        <div className="split-feature-row">
          {/* Left: 3 Stacked Mini Cards */}
          <div className="stacked-items">
            <div className="dark-card mini-item-card">
              <div className="mini-icon-wrap">
                <Lock size={18} />
              </div>
              <div>
                <h4 className="mini-title">100% Secured</h4>
                <p className="mini-desc">Строгий WAF, Cloudflare Turnstile, шифрование и отсутствие утечек данных.</p>
              </div>
            </div>

            <div className="dark-card mini-item-card">
              <div className="mini-icon-wrap">
                <Zap size={18} />
              </div>
              <div>
                <h4 className="mini-title">Субсекундный отклик &lt; 50ms</h4>
                <p className="mini-desc">Оптимизированный асинхронный event loop и кэширование на клиенте.</p>
              </div>
            </div>

            <div className="dark-card mini-item-card">
              <div className="mini-icon-wrap">
                <ShieldCheck size={18} />
              </div>
              <div>
                <h4 className="mini-title">Гарантия SLA и Uptime 99.98%</h4>
                <p className="mini-desc">Zero-downtime деплои через изолированные Docker контейнеры.</p>
              </div>
            </div>
          </div>

          {/* Right: Headline & CTA */}
          <div className="split-text-content">
            <div className="badge-capsule badge-capsule-emerald">
              <span className="badge-icon">✓</span>
              <span>BENEFITS</span>
            </div>
            <h2 className="split-headline">
              Streamline complex <br />business processes with Highload
            </h2>
            <p className="split-desc">
              Мы проектируем архитектуру, которая не требует переписывания через год. 
              Чистый код, покрытие автоматическими тестами и детальная документация Swagger API для вашей команды.
            </p>
            <button className="btn-primary" onClick={onOpenContact}>
              <span>Обсудить задачу</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>

        {/* Section 3: Split Row (Left text / Right live analytics graph) */}
        <div className="split-feature-row reverse">
          <div className="split-text-content">
            <div className="badge-capsule">
              <span className="badge-icon">⚡</span>
              <span>FEATURES YOU'LL NEED</span>
            </div>
            <h2 className="split-headline">
              Powerful solutions for <br />your high-growth business
            </h2>
            <p className="split-desc">
              Прямой контроль всех модулей и метрик. Мы измеряем производительность каждого эндпоинта и гарантируем стабильную работу базы данных под нагрузкой.
            </p>
            <div className="split-proof-strip">
              <button className="btn-primary" onClick={onOpenContact}>
                <span>Начать проект</span>
              </button>
              <div className="avatar-proof">
                <div className="avatar-group">
                  <div className="avatar-circle">CTO</div>
                  <div className="avatar-circle">FE</div>
                  <div className="avatar-circle">BE</div>
                </div>
                <span className="avatar-proof-text">Команда Senior инженеров</span>
              </div>
            </div>
          </div>

          {/* Right: Dark Dashboard Card with Live Graph */}
          <div className="dashboard-preview-card dark-card">
            <div className="dash-head">
              <div>
                <span className="dash-label">API Latency (p99)</span>
                <div className="dash-metric">13.5 ms <span className="dash-delta">-84%</span></div>
              </div>
              <span className="dash-badge">Live Telemetry</span>
            </div>

            {/* SVG Line Chart */}
            <div className="dash-chart-wrap">
              <svg viewBox="0 0 400 120" className="dash-chart-svg">
                <defs>
                  <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ffffff" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path 
                  d="M 0 90 Q 60 70 100 45 T 200 30 T 300 15 T 400 10 L 400 120 L 0 120 Z" 
                  fill="url(#chartGrad)" 
                />
                <path 
                  d="M 0 90 Q 60 70 100 45 T 200 30 T 300 15 T 400 10" 
                  fill="none" 
                  stroke="#ffffff" 
                  strokeWidth="2.5" 
                />
                <circle cx="400" cy="10" r="4" fill="#ffffff" />
              </svg>
            </div>

            <div className="dash-footer-metrics">
              <div className="dash-metric-item">
                <span className="m-title">Throughput</span>
                <span className="m-val">12 500 TPS</span>
              </div>
              <div className="dash-metric-item">
                <span className="m-title">DB Connections</span>
                <span className="m-val">28 / 30 active</span>
              </div>
              <div className="dash-metric-item">
                <span className="m-title">Exceptions</span>
                <span className="m-val text-emerald">0 unhandled</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .features-section {
          padding: 80px 0 100px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .features-head {
          max-width: 680px;
          margin: 0 auto 50px;
        }
        .features-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
          line-height: 1.15;
        }
        .features-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }
        .feature-cards-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
          margin-bottom: 100px;
        }
        .feature-card {
          padding: 36px 30px;
        }
        .card-heading {
          font-size: 1.25rem;
          margin-bottom: 12px;
          color: #ffffff;
        }
        .card-paragraph {
          font-size: 0.92rem;
          color: var(--text-secondary);
          line-height: 1.6;
        }

        /* Split Rows */
        .split-feature-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 60px;
          align-items: center;
          margin-bottom: 110px;
        }
        .stacked-items {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .mini-item-card {
          display: flex;
          align-items: center;
          gap: 20px;
          padding: 22px 26px;
        }
        .mini-icon-wrap {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #ffffff;
        }
        .mini-title {
          font-size: 1.05rem;
          margin-bottom: 4px;
          color: #ffffff;
        }
        .mini-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
        }
        .split-text-content {
          padding: 10px 0;
        }
        .split-headline {
          font-size: 2.6rem;
          margin-top: 18px;
          margin-bottom: 18px;
          line-height: 1.2;
        }
        .split-desc {
          font-size: 1.05rem;
          color: var(--text-secondary);
          line-height: 1.65;
          margin-bottom: 28px;
        }
        .split-proof-strip {
          display: flex;
          align-items: center;
          gap: 24px;
        }
        .avatar-proof {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .avatar-group {
          display: flex;
        }
        .avatar-circle {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: #181c26;
          border: 2px solid #000000;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.65rem;
          font-weight: 700;
          color: var(--text-secondary);
          margin-left: -8px;
        }
        .avatar-circle:first-child {
          margin-left: 0;
        }
        .avatar-proof-text {
          font-size: 0.82rem;
          color: var(--text-secondary);
          font-weight: 500;
        }

        /* Dashboard Preview Card */
        .dashboard-preview-card {
          padding: 32px;
        }
        .dash-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 24px;
        }
        .dash-label {
          font-size: 0.8rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .dash-metric {
          font-family: var(--font-display);
          font-size: 2rem;
          font-weight: 800;
          color: #ffffff;
          margin-top: 4px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .dash-delta {
          font-size: 0.85rem;
          color: var(--accent-emerald);
          font-family: var(--font-body);
          font-weight: 600;
        }
        .dash-badge {
          padding: 4px 10px;
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          border-radius: 9999px;
          color: var(--accent-emerald);
          font-size: 0.75rem;
          font-family: var(--font-mono);
        }
        .dash-chart-wrap {
          margin: 10px 0 24px;
        }
        .dash-chart-svg {
          width: 100%;
          height: 100px;
        }
        .dash-footer-metrics {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
          padding-top: 20px;
          border-top: 1px solid var(--border-subtle);
        }
        .dash-metric-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .m-title {
          font-size: 0.75rem;
          color: var(--text-muted);
        }
        .m-val {
          font-size: 0.9rem;
          font-weight: 600;
          font-family: var(--font-mono);
          color: #ffffff;
        }
        .text-emerald {
          color: var(--accent-emerald);
        }

        @media (max-width: 960px) {
          .feature-cards-grid {
            grid-template-columns: 1fr;
          }
          .split-feature-row {
            grid-template-columns: 1fr;
            gap: 40px;
          }
          .split-feature-row.reverse {
            display: flex;
            flex-direction: column-reverse;
          }
          .features-title {
            font-size: 2.2rem;
          }
          .split-headline {
            font-size: 2rem;
          }
        }
      `}</style>
    </section>
  );
}
