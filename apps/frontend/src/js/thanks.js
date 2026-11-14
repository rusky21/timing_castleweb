// Страница «спасибо» после отправки формы: та же картина, что на 404, но в замке горят все окна.
import { reachGoal } from './analytics.js';
import { initMosaic } from './mosaic.js';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
initMosaic(document.querySelector('[data-mosaic]'), { reduced, lit: true });

/* Цели Метрики на клики: data-goal="tg_click" */
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-goal]');
  if (el) reachGoal(el.dataset.goal);
});

/* Цель «заявка» один раз, только после реальной отправки формы (её отмечает form.js) */
let source = null;
try {
  source = sessionStorage.getItem('cw-lead');
  sessionStorage.removeItem('cw-lead');
} catch { /* хранилище недоступно */ }

if (source) {
  reachGoal('lead', { page: source });
  const received = document.querySelector('[data-received]');
  const time = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date());
  received.textContent = `Заявка принята в ${time}`;
  received.hidden = false;
}
