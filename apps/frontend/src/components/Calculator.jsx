import React, { useState } from 'react';
import { Check, ArrowRight, ShieldCheck, Zap, Sparkles } from 'lucide-react';

const TIERS = [
  {
    id: 'mvp',
    name: 'MVP Sprint',
    price: '180 000 ₽',
    days: '14 дней',
    desc: 'Быстрый запуск продукта для проверки гипотез на рынке с чистой архитектурой.',
    features: ['React 19 + FastAPI ядро', 'PostgreSQL 16 база данных', 'Telegram CRM оповещения', 'Базовый WAF & SSL']
  },
  {
    id: 'saas',
    name: 'SaaS Platform',
    badge: 'ПОПУЛЯРНЫЙ ВЫБОР',
    price: '340 000 ₽',
    days: '30 дней',
    desc: 'Полнофункциональная платформа с личными кабинетами, биллингом и L2 кэшем.',
    features: ['Всё из MVP Sprint', 'Redis 7 высокоскоростной кэш', 'Прием платежей / подписки', 'Cloudflare R2 хранилище', 'SLA 99.98% гарантия']
  },
  {
    id: 'enterprise',
    name: 'Highload & 3D Web',
    price: '580 000 ₽',
    days: '45 дней',
    desc: 'Премиальные решения с миллионной пропускной способностью и 3D WebGL интерфейсами.',
    features: ['Всё из SaaS Platform', 'Интерактивный 3D WebGL / Three.js', 'Шардирование PostgreSQL', 'Очереди брокеров сообщений', 'Выделенный Lead Architect']
  }
];

const ADDONS = [
  { id: 'tg_bot', name: 'Telegram Headless CRM', price: 35000, desc: 'Управление лидами в закрытом чате команды (0 ₽/мес)' },
  { id: 'redis', name: 'Redis Highload кэширование', price: 25000, desc: 'Снижение нагрузки на базу и отклик < 40ms' },
  { id: 'payments', name: 'Платежный шлюз (ЮKassa / Crypto)', price: 30000, desc: 'Прием платежей, чеки, рекуррентные подписки' },
  { id: 'r2', name: 'Cloudflare R2 S3 хранилище', price: 20000, desc: 'Раздача файлов и фото с 0 ₽ за исходящий трафик' }
];

export default function Calculator({ onApplyConfig }) {
  const [selectedTier, setSelectedTier] = useState('saas');
  const [selectedAddons, setSelectedAddons] = useState(['tg_bot', 'redis']);

  const toggleAddon = (id) => {
    setSelectedAddons(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const currentTierObj = TIERS.find(t => t.id === selectedTier) || TIERS[1];

  const handleTransfer = () => {
    const activeAddonsNames = selectedAddons
      .map(id => ADDONS.find(a => a.id === id)?.name)
      .filter(Boolean)
      .join(', ');

    const summary = `План: ${currentTierObj.name} (${currentTierObj.price})\nСрок реализации: ~${currentTierObj.days}\nДополнительные модули: ${activeAddonsNames || 'Базовые'}`;

    onApplyConfig({
      summary,
      budget: currentTierObj.price,
      projectType: currentTierObj.name
    });
  };

  return (
    <section className="calc-section" id="calculator">
      <div className="container">
        {/* Section Head */}
        <div className="calc-head text-center">
          <div className="badge-capsule">
            <span className="badge-icon">✦</span>
            <span>PRICING & ESTIMATOR</span>
          </div>
          <h2 className="calc-title">
            Choose your plan & scope
          </h2>
          <p className="calc-sub">
            Прозрачная стоимость этапов разработки без скрытых переплат и комиссий.
          </p>
        </div>

        {/* 3 Tier Cards (Salesrocket style) */}
        <div className="tiers-grid">
          {TIERS.map((tier) => {
            const isSelected = selectedTier === tier.id;
            return (
              <div 
                key={tier.id} 
                className={`dark-card tier-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setSelectedTier(tier.id)}
              >
                {tier.badge && (
                  <div className="tier-popular-badge">{tier.badge}</div>
                )}
                
                <h3 className="tier-name">{tier.name}</h3>
                <div className="tier-price-row">
                  <span className="tier-price">{tier.price}</span>
                  <span className="tier-days">/ ~{tier.days}</span>
                </div>
                <p className="tier-desc">{tier.desc}</p>

                <div className="tier-features-list">
                  {tier.features.map((feat, i) => (
                    <div key={i} className="tier-feature-item">
                      <div className="feat-check">
                        <Check size={13} />
                      </div>
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>

                <button 
                  className={`tier-btn ${isSelected ? 'btn-primary' : 'btn-secondary'} w-full`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTier(tier.id);
                    handleTransfer();
                  }}
                >
                  <span>{isSelected ? 'Выбрать этот план' : 'Выбрать'}</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            );
          })}
        </div>

        {/* Add-ons checkboxes */}
        <div className="addons-card dark-card">
          <div className="addons-head">
            <h4 className="addons-title">Дополнительные архитектурные модули:</h4>
            <span className="addons-sub">Кастомизируйте конфигурацию под ваши требования</span>
          </div>

          <div className="addons-grid">
            {ADDONS.map((addon) => {
              const checked = selectedAddons.includes(addon.id);
              return (
                <div 
                  key={addon.id} 
                  className={`addon-chip ${checked ? 'checked' : ''}`}
                  onClick={() => toggleAddon(addon.id)}
                >
                  <div className={`addon-checkbox ${checked ? 'active' : ''}`}>
                    {checked && <Check size={12} />}
                  </div>
                  <div>
                    <span className="addon-name">{addon.name}</span>
                    <span className="addon-price">+{addon.price.toLocaleString('ru-RU')} ₽</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="addons-footer">
            <button className="btn-primary" onClick={handleTransfer} id="calc-transfer-btn">
              <span>Перенести смету в заявку</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>

      <style>{`
        .calc-section {
          padding: 80px 0 100px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .calc-head {
          max-width: 660px;
          margin: 0 auto 50px;
        }
        .calc-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
        }
        .calc-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }

        /* 3 Tier Grid */
        .tiers-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
          margin-bottom: 40px;
        }
        .tier-card {
          padding: 34px 28px;
          display: flex;
          flex-direction: column;
          cursor: pointer;
          position: relative;
        }
        .tier-card.selected {
          border-color: rgba(255, 255, 255, 0.4);
          box-shadow: 0 0 30px rgba(255, 255, 255, 0.1);
          background: #10131b;
        }
        .tier-popular-badge {
          position: absolute;
          top: 18px;
          right: 20px;
          background: #ffffff;
          color: #000000;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          padding: 4px 10px;
          border-radius: 9999px;
        }
        .tier-name {
          font-size: 1.3rem;
          margin-bottom: 14px;
          color: #ffffff;
        }
        .tier-price-row {
          display: flex;
          align-items: baseline;
          gap: 8px;
          margin-bottom: 14px;
        }
        .tier-price {
          font-family: var(--font-display);
          font-size: 2.2rem;
          font-weight: 800;
          color: #ffffff;
        }
        .tier-days {
          font-size: 0.85rem;
          color: var(--text-muted);
        }
        .tier-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.5;
          margin-bottom: 24px;
          min-height: 42px;
        }
        .tier-features-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 30px;
          flex-grow: 1;
        }
        .tier-feature-item {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.85rem;
          color: var(--text-secondary);
        }
        .feat-check {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #ffffff;
        }
        .tier-btn {
          width: 100%;
        }

        /* Addons Card */
        .addons-card {
          padding: 30px;
        }
        .addons-head {
          margin-bottom: 20px;
        }
        .addons-title {
          font-size: 1.15rem;
          color: #ffffff;
          margin-bottom: 4px;
        }
        .addons-sub {
          font-size: 0.85rem;
          color: var(--text-muted);
        }
        .addons-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 14px;
          margin-bottom: 24px;
        }
        .addon-chip {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px 18px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .addon-chip:hover {
          background: rgba(255, 255, 255, 0.06);
        }
        .addon-chip.checked {
          border-color: rgba(255, 255, 255, 0.3);
          background: rgba(255, 255, 255, 0.08);
        }
        .addon-checkbox {
          width: 20px;
          height: 20px;
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #000000;
        }
        .addon-checkbox.active {
          background: #ffffff;
          border-color: #ffffff;
        }
        .addon-name {
          display: block;
          font-size: 0.9rem;
          font-weight: 600;
          color: #ffffff;
        }
        .addon-price {
          font-size: 0.75rem;
          color: var(--accent-emerald);
          font-family: var(--font-mono);
        }
        .addons-footer {
          display: flex;
          justify-content: flex-end;
          padding-top: 16px;
          border-top: 1px solid var(--border-subtle);
        }
        .w-full {
          width: 100%;
        }

        @media (max-width: 960px) {
          .tiers-grid {
            grid-template-columns: 1fr;
          }
          .addons-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  );
}
