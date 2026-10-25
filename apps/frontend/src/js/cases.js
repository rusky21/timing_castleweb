// Кейсы: вертикальный скролл двигает ленту проектов по горизонтали,
// фон секции перетекает в цвет текущего проекта, скриншоты слегка смещаются (параллакс).
import { onScroll, clamp } from './scroll.js';

export function initCases(section, { reduced = false } = {}) {
  if (!section) return;
  const stage = section.querySelector('[data-cases-stage]');
  const track = section.querySelector('[data-cases-track]');
  const panels = [...track.children];
  const imgs = panels.map((p) => p.querySelector('.cs__media img'));
  const numEl = section.querySelector('[data-cases-num]');
  const barEl = section.querySelector('[data-cases-bar]');
  const desktop = window.matchMedia('(min-width: 900px)');
  const total = panels.filter((p) => p.classList.contains('cs')).length;

  let dist = 0;
  let active = -1;

  const measure = () => {
    if (!desktop.matches || reduced) {
      dist = 0;
      stage.style.height = '';
      track.style.transform = '';
      imgs.forEach((img) => img && (img.style.transform = ''));
      return;
    }
    dist = Math.max(0, track.scrollWidth - window.innerWidth);
    stage.style.height = `${dist + window.innerHeight}px`;
  };

  const setActive = (i) => {
    if (i === active) return;
    active = i;
    section.style.setProperty('--cbg', panels[i].dataset.bg);
    if (numEl) numEl.textContent = String(Math.min(i + 1, total)).padStart(2, '0');
  };

  onScroll((vh) => {
    if (!dist) {
      // Телефон: фон меняется по проекту, который ближе к центру экрана
      let best = 0, bestD = Infinity;
      panels.forEach((p, i) => {
        const r = p.getBoundingClientRect();
        const d = Math.abs(r.top + r.height / 2 - vh / 2);
        if (d < bestD) { bestD = d; best = i; }
      });
      setActive(best);
      return;
    }
    const r = stage.getBoundingClientRect();
    const p = clamp(-r.top / dist);
    const x = p * dist;
    const vw = window.innerWidth;
    track.style.transform = `translate3d(${-x.toFixed(1)}px, 0, 0)`;
    if (barEl) barEl.style.setProperty('--cp', p.toFixed(4));

    let best = 0, bestD = Infinity;
    panels.forEach((panel, i) => {
      const left = panel.offsetLeft - x;
      const d = Math.abs(left + panel.offsetWidth * 0.35 - vw * 0.35);
      if (d < bestD) { bestD = d; best = i; }
      const img = imgs[i];
      if (img) {
        const off = clamp(left / vw, -1, 1);
        img.style.transform = `translate3d(${(-2.8 - off * 2.6).toFixed(2)}%, 0, 0)`;
      }
    });
    setActive(best);
  });

  measure();
  window.addEventListener('resize', measure);
  desktop.addEventListener('change', measure);
  window.addEventListener('load', measure);
}
