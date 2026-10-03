import React from 'react';
import './WorkProcess.css';

interface StackCardData {
  id: number;
  titleLine1: string;
  titleLine2: string;
  tags: string[];
  description: string;
}

const STACK_CARDS: StackCardData[] = [
  {
    id: 1,
    titleLine1: 'Шаг 1: Аналитика',
    titleLine2: 'ТЗ и архитектура БД',
    tags: ['Бизнес-анализ', 'Техническое задание', 'Архитектура БД', 'Аудит требований', 'Роадмап'],
    description: 'Шаг 1: Аналитика, ТЗ и согласование архитектуры БД.',
  },
  {
    id: 2,
    titleLine1: 'Шаг 2: Прототипирование',
    titleLine2: 'Интерактивный UI/UX',
    tags: ['UI/UX дизайн', 'Прототипирование', 'Figma', 'User Flow', 'Дизайн-система'],
    description: 'Шаг 2: Прототипирование и интерактивный UI/UX дизайн.',
  },
  {
    id: 3,
    titleLine1: 'Шаг 3: Разработка',
    titleLine2: 'Спринты и демо на staging',
    tags: ['Frontend', 'Backend', 'Staging-сервер', 'Спринты', 'Регулярные демо', 'CI/CD'],
    description: 'Шаг 3: Разработка спринтами (регулярные демо на staging-сервере).',
  },
  {
    id: 4,
    titleLine1: 'Шаг 4: Тестирование',
    titleLine2: 'SEO и безопасность',
    tags: ['QA тестирование', 'SEO-оптимизация', 'Аудит безопасности', 'Оптимизация скорости'],
    description: 'Шаг 4: Тестирование, SEO-оптимизация и аудит безопасности.',
  },
  {
    id: 5,
    titleLine1: 'Шаг 5: Деплой',
    titleLine2: 'Исходники и поддержка',
    tags: ['Деплой в прод', 'Все исходники клиенту', 'Документация', 'Гарантийная поддержка'],
    description: 'Шаг 5: Деплой, передача всех исходников клиенту и гарантийная поддержка.',
  },
];

export const WorkProcess: React.FC = () => {
  return (
    <section className="work-process-section" id="process">
      <div className="stacking-cards-container">
        {STACK_CARDS.map((card, index) => {
          // Dynamic top offset so each subsequent card stacks slightly lower,
          // creating the layered deck effect at the top as shown in the video reference.
          const topOffset = `calc(65px + ${index} * 28px)`;

          return (
            <div
              key={card.id}
              className={`stack-card stack-card--${card.id} reveal-void`}
              style={{
                top: topOffset,
                zIndex: index + 1,
              }}
            >
              {/* Card Top: Large Two-Line Title */}
              <div className="stack-card-title-group">
                <h2 className="stack-card-line1">{card.titleLine1}</h2>
                <h3 className="stack-card-line2">{card.titleLine2}</h3>
              </div>

              {/* Card Bottom: Tags Row & Description */}
              <div className="stack-card-bottom-group">
                <div className="stack-card-tags-row">
                  {card.tags.map((tag, tagIdx) => (
                    <span key={tagIdx} className="stack-card-tag-item">
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="stack-card-desc-row">
                  <span className="stack-card-sparkle-icon" aria-hidden="true">
                    ✦
                  </span>
                  <p className="stack-card-desc-text">{card.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default WorkProcess;
