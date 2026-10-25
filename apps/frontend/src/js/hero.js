// Первый экран: строки заголовка выезжают из-под маски, картина раскрывается до краёв при скролле.
import { onScroll, clamp } from './scroll.js';

const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

export function initHero({ reduced = false } = {}) {
  const root = document.documentElement;
  const reveal = () => root.classList.add('is-loaded');
  // Ждём шрифт, чтобы строки не перескакивали во время анимации
  Promise.race([document.fonts?.ready, new Promise((r) => setTimeout(r, 1200))]).then(() => requestAnimationFrame(reveal));

  const stage = document.querySelector('[data-stage]');
  if (!stage || reduced) return;

  onScroll((vh) => {
    const r = stage.getBoundingClientRect();
    // p: карточка → весь экран, пока сцена доезжает до верха; q: проявление цитаты после этого
    const p = easeInOut(clamp(1 - r.top / (vh * 0.75)));
    const q = clamp(-r.top / (vh * 0.45));
    stage.style.setProperty('--p', p.toFixed(4));
    stage.style.setProperty('--q', q.toFixed(4));
  });
}
