// Счётчики: число «докручивается» до значения, когда появляется на экране.

const fmt = (n) => n.toLocaleString('ru-RU');

export function countUp(el, { reduced = false, duration = 1400 } = {}) {
  const to = +el.dataset.count;
  const suffix = el.dataset.suffix || '';
  if (reduced) { el.textContent = fmt(to) + suffix; return; }
  const t0 = performance.now();
  const tick = (now) => {
    const t = Math.min(1, (now - t0) / duration);
    const e = 1 - Math.pow(1 - t, 4);
    el.textContent = fmt(Math.round(to * e)) + suffix;
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

export function initCounters(nodes, { reduced = false } = {}) {
  if (reduced) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      io.unobserve(entry.target);
      countUp(entry.target, { duration: 1600 });
    });
  }, { threshold: 0.8 });
  nodes.forEach((el) => {
    el.textContent = '0' + (el.dataset.suffix || '');
    io.observe(el);
  });
}
