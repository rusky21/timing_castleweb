import React, { useState } from 'react';
import { Plus, Minus } from 'lucide-react';

const FAQS = [
  {
    q: 'Как происходит разработка и сдача этапов по спринтам?',
    a: 'Мы работаем двухнедельными спринтами. В конце каждого спринта вы получаете осязаемый рабочий релиз на тестовом контуре (staging) с автоматическими тестами и демонстрацией функционала.'
  },
  {
    q: 'Почему в вашей архитектуре 0 ₽ расходов на CRM и Cloudflare R2?',
    a: 'Мы исключаем лицензионные подписки на сторонние SaaS-системы: вместо amoCRM/Битрикс24 развертывается Telegram Headless CRM в закрытом канале команды, а Cloudflare R2 предоставляет 10 ГБ хранилища с нулевой стоимостью исходящего трафика.'
  },
  {
    q: 'Кому принадлежат права на код и серверную инфраструктуру?',
    a: '100% прав на исходный код, репозитории Git, Docker-образы и конфигурационные файлы передаются заказчику по договору сразу после завершения проекта. Никаких привязок к закрытым конструкторам.'
  },
  {
    q: 'Какие гарантии производительности и SLA вы фиксируете?',
    a: 'Мы гарантируем Uptime 99.98% в SLA договоре, среднее время отклика API < 50 миллисекунд и выдерживание пиковых нагрузок свыше 10 000 RPS благодаря пулу asyncpg и кэшированию Redis.'
  },
  {
    q: 'Возможна ли интеграция с 1С, ЮKassa и внешними API?',
    a: 'Да. Мы разрабатываем асинхронные очереди сообщений и брокеры очередей, которые безопасно синхронизируют каталог, остатки, номенклатуру 1С и обрабатывают вебхуки платежей без задержек для клиентов.'
  }
];

export default function FAQ() {
  const [openIdx, setOpenIdx] = useState(0);

  const toggle = (idx) => {
    setOpenIdx(openIdx === idx ? -1 : idx);
  };

  return (
    <section className="faq-section" id="faq">
      <div className="container">
        <div className="faq-head text-center">
          <div className="badge-capsule">
            <span className="badge-icon">?</span>
            <span>FAQS</span>
          </div>
          <h2 className="faq-title">
            Frequently asked questions
          </h2>
          <p className="faq-sub">
            Все детали по стеку, процессам разработки и гарантиям надежности.
          </p>
        </div>

        <div className="faq-list">
          {FAQS.map((item, idx) => {
            const isOpen = openIdx === idx;
            return (
              <div 
                key={idx} 
                className={`dark-card faq-card ${isOpen ? 'open' : ''}`}
                onClick={() => toggle(idx)}
              >
                <div className="faq-question-row">
                  <span className="faq-q-text">{item.q}</span>
                  <div className="faq-toggle-btn">
                    {isOpen ? <Minus size={16} /> : <Plus size={16} />}
                  </div>
                </div>
                {isOpen && (
                  <p className="faq-a-text">{item.a}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        .faq-section {
          padding: 80px 0 110px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .faq-head {
          max-width: 660px;
          margin: 0 auto 50px;
        }
        .faq-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
        }
        .faq-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }
        .faq-list {
          max-width: 780px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .faq-card {
          padding: 22px 28px;
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .faq-card.open {
          border-color: rgba(255, 255, 255, 0.2);
          background: #11141c;
        }
        .faq-question-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }
        .faq-q-text {
          font-size: 1.05rem;
          font-weight: 600;
          color: #ffffff;
        }
        .faq-toggle-btn {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #ffffff;
        }
        .faq-a-text {
          font-size: 0.95rem;
          color: var(--text-secondary);
          line-height: 1.6;
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid var(--border-subtle);
        }

        @media (max-width: 640px) {
          .faq-title {
            font-size: 2.2rem;
          }
          .faq-q-text {
            font-size: 0.95rem;
          }
        }
      `}</style>
    </section>
  );
}
