// Квиз на лендинге «Сайт под ключ»: пять шагов, вилка цены и срока обновляется после каждого ответа.
// Цены и сроки те же, что в калькуляторе на главной: база типа проекта + опции.
// Без JS все шаги видны подряд как обычная форма.
import { formatTerm } from './calculator.js';

// Опции, из которых складывается верхняя граница вилки: [цена, дни, название]
const OPTIONS = {
  design: [15000, 2, 'уникальный дизайн с нуля'],
  crm: [12000, 2, 'интеграция с CRM'],
  pay: [10000, 1, 'приём оплаты онлайн'],
  admin: [20000, 3, 'админ-панель для контента'],
};

const money = (n) => n.toLocaleString('ru-RU');
const list = (str) => (str ? str.split(',') : []);

export function initQuiz(form, { reduced = false } = {}) {
  if (!form) return;
  const steps = [...form.querySelectorAll('[data-step]')];
  const last = steps.length - 1;
  const back = form.querySelector('[data-quiz-back]');
  const next = form.querySelector('[data-quiz-next]');
  const submit = form.querySelector('[type="submit"]');
  const count = form.querySelector('[data-quiz-count]');
  const bar = form.querySelector('[data-quiz-bar]');
  const status = form.querySelector('[data-form-status]');
  const out = document.querySelector('[data-quiz-out]');
  const priceEl = out.querySelector('[data-quiz-price]');
  const termEl = out.querySelector('[data-quiz-term]');
  const noteEl = out.querySelector('[data-quiz-note]');
  let index = 0;

  const picked = (name) => form.querySelector(`input[name="${name}"]:checked`);
  const say = (text) => {
    status.textContent = text;
    if (text) status.dataset.state = 'error';
    else delete status.dataset.state;
  };

  // Вилка: нижняя граница — базовый состав, верхняя — с опциями, которые обычно нужны под выбранную задачу
  const estimate = () => {
    const type = picked('q-type');
    const goal = picked('q-goal');
    const base = type ? type.dataset : { low: 30000, high: 60000, days: 3, daysMax: 10 };
    const must = list(goal?.dataset.must).map((k) => OPTIONS[k]);
    const extra = list(goal?.dataset.opts || 'design').map((k) => OPTIONS[k]);
    const sum = (items, i) => items.reduce((acc, item) => acc + item[i], 0);
    return {
      low: +base.low + sum(must, 0),
      high: +base.high + sum(must, 0) + sum(extra, 0),
      lo: +base.days + sum(must, 1),
      hi: +base.daysMax + sum(must, 1) + sum(extra, 1),
      must: must.map((o) => o[2]),
      extra: extra.map((o) => o[2]),
    };
  };

  const render = () => {
    const e = estimate();
    priceEl.textContent = `${money(e.low)} – ${money(e.high)} ₽`;
    termEl.textContent = formatTerm(e.lo, e.hi);
    const lower = e.must.length ? `базовый состав и ${e.must.join(', ')}` : 'базовый состав';
    noteEl.textContent = `Нижняя граница: ${lower}. Верхняя: то же плюс ${e.extra.join(', ')}.`;
    return e;
  };

  const answered = (step) => !step.querySelector('input[type="radio"]') || step.querySelector('input[type="radio"]:checked');

  const show = (n, focus = true) => {
    index = n;
    steps.forEach((step, k) => { step.hidden = k !== index; });
    back.hidden = index === 0;
    next.hidden = index === last;
    submit.hidden = index !== last;
    count.textContent = `Вопрос ${index + 1} из ${steps.length}`;
    bar.style.transform = `scaleX(${(index + 1) / steps.length})`;
    if (focus) steps[index].querySelector('legend').focus({ preventScroll: true });
  };

  const forward = () => {
    if (!answered(steps[index])) { say('Выберите один из вариантов.'); return; }
    say('');
    if (index < last) show(index + 1);
  };

  next.addEventListener('click', forward);
  back.addEventListener('click', () => { say(''); show(index - 1); });
  form.addEventListener('change', render);

  // Выбор мышью или пальцем сразу ведёт дальше; с клавиатуры — только по кнопке «Дальше»,
  // иначе стрелки, которыми перебирают варианты, перелистывали бы шаги
  form.addEventListener('pointerup', (e) => {
    const step = e.target.closest('[data-step]');
    if (!e.target.closest('.quiz__opts label') || step !== steps[index] || index === last) return;
    setTimeout(() => { if (step === steps[index] && answered(step)) forward(); }, reduced ? 0 : 260);
  });

  // Этот обработчик стоит раньше обработчика form.js: Enter на промежуточном шаге листает квиз,
  // на последнем шаге ответы собираются в текст заявки
  form.addEventListener('submit', (e) => {
    if (index < last) {
      e.preventDefault();
      e.stopImmediatePropagation();
      forward();
      return;
    }
    const e2 = estimate();
    const fork = `${money(e2.low)}–${money(e2.high)} ₽, ${formatTerm(e2.lo, e2.hi)}`;
    const value = (name) => picked(name)?.value || 'не указано';
    const comment = form.elements.comment.value.trim();
    form.elements.direction.value = value('q-type');
    form.elements.budget.value = `${value('q-budget')}; вилка ${fork}`.slice(0, 100);
    form.elements.task.value = [
      `Задача: ${value('q-goal')}`,
      `Срок: ${value('q-deadline')}`,
      `Бюджет: ${value('q-budget')}`,
      `Вилка из квиза: ${fork}`,
      comment && `Комментарий: ${comment}`,
    ].filter(Boolean).join('\n');
  });

  form.classList.add('is-ready');
  render();
  show(0, false);
}
