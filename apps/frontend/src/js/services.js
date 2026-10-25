// Услуги: у каждого направления живая иллюстрация.
// Иллюстрация — сцена с таймлайном: data-seq="on@0.4 press@4.1 -on@6" (класс@секунда, минус — снять класс).
import { countUp } from './counters.js';

const fmt = (n) => n.toLocaleString('ru-RU');

const parseSeq = (str) => str.trim().split(/\s+/).map((token) => {
  const [name, time] = token.split('@');
  const remove = name.startsWith('-');
  return { cls: remove ? name.slice(1) : name, remove, t: parseFloat(time) * 1000 };
});

function createScene(viz, reduced) {
  const items = [...viz.querySelectorAll('[data-seq]')].map((el) => ({ el, steps: parseSeq(el.dataset.seq) }));
  const loop = parseFloat(viz.dataset.loop || 8) * 1000;
  let timers = [];

  const stop = () => { timers.forEach(clearTimeout); timers = []; };

  const reset = () => {
    viz.classList.add('no-tr');
    items.forEach(({ el, steps }) => {
      steps.forEach((s) => s.cls !== 'count' && el.classList.remove(s.cls));
      if (el.dataset.count) el.textContent = '0' + (el.dataset.suffix || '');
    });
    void viz.offsetWidth;
    viz.classList.remove('no-tr');
  };

  const apply = (el, s) => {
    if (s.cls === 'count') countUp(el, { duration: 1100 });
    else el.classList.toggle(s.cls, !s.remove);
  };

  const play = () => {
    stop();
    reset();
    items.forEach(({ el, steps }) => steps.forEach((s) => timers.push(setTimeout(() => apply(el, s), s.t))));
    timers.push(setTimeout(play, loop));
  };

  // Без анимаций показываем финальный кадр сцены
  const still = () => {
    stop();
    viz.classList.add('no-tr');
    items.forEach(({ el, steps }) => {
      [...steps].sort((a, b) => a.t - b.t).forEach((s) => {
        if (s.cls === 'count') el.textContent = fmt(+el.dataset.count) + (el.dataset.suffix || '');
        else el.classList.toggle(s.cls, !s.remove);
      });
    });
    void viz.offsetWidth;
    viz.classList.remove('no-tr');
  };

  return { play: reduced ? still : play, stop, loop };
}

// Каждая иллюстрация проигрывается по кругу, пока её направление на экране
export function initServices(root, { reduced = false } = {}) {
  if (!root) return;
  root.querySelectorAll('[data-viz]').forEach((viz) => {
    const scene = createScene(viz, reduced);
    if (reduced) { scene.play(); return; }
    new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) scene.play();
      else scene.stop();
    }, { threshold: 0.35 }).observe(viz);
  });
}
