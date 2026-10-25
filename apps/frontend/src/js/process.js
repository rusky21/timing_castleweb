// Процесс: сцена закреплена на экране. Как только она доезжает до верха, фон сменяется
// на цвет первого этапа; дальше скролл переключает этапы, и каждый появляется заново.
import { onScroll, clamp } from './scroll.js';

function splitWords(el) {
  const words = el.textContent.trim().split(/\s+/);
  el.textContent = '';
  words.forEach((word, i) => {
    const outer = document.createElement('span');
    outer.className = 'w';
    const inner = document.createElement('span');
    inner.style.setProperty('--d', i);
    inner.textContent = word;
    outer.append(inner);
    el.append(outer, i < words.length - 1 ? ' ' : '');
  });
}

export function initProcess(root, { reduced = false } = {}) {
  if (!root) return;
  const stages = [...root.querySelectorAll('.pr__stage')];
  const navItems = [...root.querySelectorAll('.pr__nav li')];
  const countEl = root.querySelector('[data-pr-count]');
  const header = document.querySelector('[data-header]');
  root.querySelectorAll('[data-pr-split]').forEach(splitWords);

  let current = -1;
  const setStage = (n) => {
    if (n === current) return;
    current = n;
    root.dataset.stage = String(n);
    stages.forEach((s) => s.classList.toggle('is-active', +s.dataset.n === n));
    navItems.forEach((li) => li.classList.toggle('is-on', +li.dataset.n === n));
    if (countEl && n > 0) countEl.textContent = String(n).padStart(2, '0');
  };

  if (reduced) {
    stages.forEach((s) => s.classList.add('is-active'));
    return;
  }

  let darkHeader = false;
  onScroll((vh) => {
    const r = root.getBoundingClientRect();
    const dist = root.offsetHeight - vh;
    let n = 0;
    // первый этап включается, когда сцена заняла большую часть экрана
    if (r.top < vh * 0.35) {
      const p = clamp(-r.top / dist);
      n = Math.min(4, 1 + Math.floor(p * 4));
    }
    setStage(n);

    // На синем и чёрном фоне шапка тоже переходит в тёмный режим
    const covering = r.top <= 0 && r.bottom > 60;
    const dark = covering && n >= 3;
    if (dark !== darkHeader) {
      darkHeader = dark;
      header.classList.toggle('is-dark', dark);
    }
  });
}
