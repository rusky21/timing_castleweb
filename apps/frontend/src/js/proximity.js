// Слово в подвале: буквы рядом с курсором становятся жирнее (переменный Manrope 200–800).

export function initProximity(el, { reduced = false } = {}) {
  if (!el || reduced || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

  const text = el.textContent;
  el.textContent = '';
  const letters = [...text].map((ch) => {
    const span = document.createElement('span');
    span.textContent = ch;
    el.append(span);
    return span;
  });

  let mx = -1e4, my = -1e4, raf = 0, visible = false;

  const update = () => {
    raf = 0;
    const centers = letters.map((l) => {
      const r = l.getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2];
    });
    const reach = Math.max(260, window.innerWidth * 0.22);
    letters.forEach((l, i) => {
      const d = Math.hypot(centers[i][0] - mx, centers[i][1] - my);
      const t = Math.max(0, 1 - d / reach);
      const s = t * t * (3 - 2 * t);
      l.style.fontWeight = String(Math.round(250 + 550 * s));
    });
  };

  new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }).observe(el);
  window.addEventListener('pointermove', (e) => {
    if (!visible) return;
    mx = e.clientX;
    my = e.clientY;
    if (!raf) raf = requestAnimationFrame(update);
  }, { passive: true });
}
