import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import { initMosaic } from './mosaic.js';
import { initHero } from './hero.js';
import { initWords } from './words.js';
import { initCounters } from './counters.js';
import { initCases } from './cases.js';
import { initCursor } from './cursor.js';
import { initServices } from './services.js';
import { initCalculator } from './calculator.js';
import { initPortraits } from './portraits.js';
import { initFaq } from './faq.js';
import { initProximity } from './proximity.js';
import { initForm } from './form.js';
import { initReveal } from './reveal.js';
import { initProcess } from './process.js';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const html = document.documentElement;
html.classList.add('js');
if (reduced) html.classList.add('rm');

/* Плавный скролл */
let lenis = null;
if (!reduced) {
  lenis = new Lenis({ lerp: 0.11 });
  const raf = (time) => {
    lenis.raf(time);
    requestAnimationFrame(raf);
  };
  requestAnimationFrame(raf);
}

/* Шапка: прячется при скролле вниз, возвращается при скролле вверх, темнеет над тёмными блоками */
const header = document.querySelector('[data-header]');
const nav = document.querySelector('[data-nav]');
const menuBtn = document.querySelector('[data-menu-btn]');
let lastY = window.scrollY;

const onScroll = () => {
  const y = window.scrollY;
  header.classList.toggle('is-scrolled', y > 8);
  if (!nav.classList.contains('is-open')) {
    const down = y > lastY + 4;
    const up = y < lastY - 4;
    if (down && y > 480) header.classList.add('is-hidden');
    else if (up || y < 480) header.classList.remove('is-hidden');
  }
  lastY = y;
};
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

// Полоса высотой с шапку сверху экрана: какие тёмные блоки сейчас под ней
const darkUnderHeader = new Set();
const darkIo = new IntersectionObserver((entries) => {
  entries.forEach((e) => (e.isIntersecting ? darkUnderHeader.add(e.target) : darkUnderHeader.delete(e.target)));
  header.classList.toggle('is-dark', darkUnderHeader.size > 0);
}, { rootMargin: '0px 0px -94% 0px' });
document.querySelectorAll('[data-dark]').forEach((el) => darkIo.observe(el));

/* Мобильное меню */
const setMenu = (open) => {
  nav.classList.toggle('is-open', open);
  header.classList.toggle('is-menu', open);
  menuBtn.setAttribute('aria-expanded', String(open));
  menuBtn.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
  html.style.overflow = open ? 'hidden' : '';
  if (open) header.classList.remove('is-hidden');
  if (lenis) open ? lenis.stop() : lenis.start();
};
menuBtn.addEventListener('click', () => setMenu(!nav.classList.contains('is-open')));
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && nav.classList.contains('is-open')) {
    setMenu(false);
    menuBtn.focus();
  }
});
window.matchMedia('(min-width: 900px)').addEventListener('change', () => setMenu(false));

/* Якорные ссылки */
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="#"]');
  if (!link) return;
  const id = link.getAttribute('href');
  const target = id === '#top' ? null : document.querySelector(id);
  if (id !== '#top' && !target) return;
  e.preventDefault();
  if (nav.classList.contains('is-open')) setMenu(false);
  if (lenis) lenis.scrollTo(target || 0, { offset: -24, duration: 1.4 });
  else window.scrollTo({ top: target ? target.getBoundingClientRect().top + window.scrollY - 24 : 0 });
  history.replaceState(null, '', id === '#top' ? location.pathname : id);
  if (id === '#contact') {
    setTimeout(() => document.querySelector('#f-name')?.focus({ preventScroll: true }), reduced ? 0 : 1500);
  }
});

/* Текущий раздел в навигации */
const navLinks = [...nav.querySelectorAll('a[href^="#"]:not(.btn)')];
const spy = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    navLinks.forEach((a) => {
      if (a.getAttribute('href') === `#${entry.target.id}`) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  });
}, { rootMargin: '-45% 0px -50% 0px' });
navLinks.forEach((a) => {
  const s = document.querySelector(a.getAttribute('href'));
  if (s) spy.observe(s);
});

/* Местное время студии */
const clocks = document.querySelectorAll('[data-clock]');
const fmt = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow' });
const tick = () => {
  const now = new Date();
  clocks.forEach((c) => {
    c.textContent = fmt.format(now);
    c.dateTime = now.toISOString();
  });
};
tick();
setInterval(tick, 15000);

/* Блоки */
initHero({ reduced });
initReveal({ reduced });
initMosaic(document.querySelector('[data-mosaic]'), { reduced });
initWords(document.querySelector('[data-words]'), { reduced });
initCounters(document.querySelectorAll('.figure [data-count]'), { reduced });
initCases(document.querySelector('[data-cases]'), { reduced });
initCursor();
initProcess(document.querySelector('[data-pr]'), { reduced });
initServices(document.querySelector('[data-niches]'), { reduced });
initCalculator(document.querySelector('[data-calc]'));
initPortraits(document.querySelectorAll('[data-portrait]'), { reduced });
initFaq(document.querySelector('[data-faq]'), { reduced });
initProximity(document.querySelector('[data-proximity]'), { reduced });
initForm(document.querySelector('[data-form]'));
