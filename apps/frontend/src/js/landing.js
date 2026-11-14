// Рекламные лендинги (/chat-boty и другие).
// Блоки взяты с главной: появление при прокрутке, живая сцена с чатом, вопросы-переписка, форма заявки.
// Цель «заявка» отправляет страница «спасибо» (thanks.js), куда форма уводит после отправки.
import { reachGoal } from './analytics.js';
import { initReveal } from './reveal.js';
import { initServices } from './services.js';
import { initFaq } from './faq.js';
import { initForm } from './form.js';
import { initQuiz } from './quiz.js';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const html = document.documentElement;
html.classList.add('js');
if (reduced) html.classList.add('rm');

// Заголовок первого экрана выезжает, когда загрузился шрифт
Promise.race([document.fonts?.ready, new Promise((r) => setTimeout(r, 1200))])
  .then(() => requestAnimationFrame(() => html.classList.add('is-loaded')));

/* Шапка: граница при скролле, тёмная над тёмными блоками */
const header = document.querySelector('[data-header]');
const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

const darkUnderHeader = new Set();
const darkIo = new IntersectionObserver((entries) => {
  entries.forEach((e) => (e.isIntersecting ? darkUnderHeader.add(e.target) : darkUnderHeader.delete(e.target)));
  header.classList.toggle('is-dark', darkUnderHeader.size > 0);
}, { rootMargin: '0px 0px -94% 0px' });
document.querySelectorAll('[data-dark]').forEach((el) => darkIo.observe(el));

/* Мобильное меню: то же поведение, что на главной */
const nav = document.querySelector('[data-nav]');
const menuBtn = document.querySelector('[data-menu-btn]');
if (nav && menuBtn) {
  const setMenu = (open) => {
    nav.classList.toggle('is-open', open);
    header.classList.toggle('is-menu', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    html.style.overflow = open ? 'hidden' : '';
  };
  menuBtn.addEventListener('click', () => setMenu(!nav.classList.contains('is-open')));
  // Ссылка внутри страницы (кнопка заявки) закрывает меню и ведёт к блоку
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a[href^="#"]')) setMenu(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('is-open')) {
      setMenu(false);
      menuBtn.focus();
    }
  });
  window.matchMedia('(min-width: 900px)').addEventListener('change', () => setMenu(false));
  // Возврат кнопкой «Назад» с другой страницы: браузер восстанавливает лендинг с открытым меню
  window.addEventListener('pageshow', (e) => {
    if (e.persisted && nav.classList.contains('is-open')) setMenu(false);
  });
}

/* Переход к форме: после прокрутки ставим курсор в первое поле */
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="#"]');
  const field = link && document.querySelector(`${link.getAttribute('href')} [data-autofocus]`);
  if (field) setTimeout(() => field.focus({ preventScroll: true }), reduced ? 0 : 700);
});

/* Цели Метрики на клики: data-goal="demo_bot" */
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-goal]');
  if (el) reachGoal(el.dataset.goal);
});

initReveal({ reduced });
initServices(document.querySelector('[data-scenes]'), { reduced });
initFaq(document.querySelector('[data-faq]'), { reduced });
// Квиз подключается раньше формы: его обработчик отправки должен сработать первым
initQuiz(document.querySelector('[data-quiz]'), { reduced });
initForm(document.querySelector('[data-form]'));
