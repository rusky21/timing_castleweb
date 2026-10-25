// Круглый курсор с подписью над скриншотами кейсов (только мышь).

export function initCursor() {
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  const el = document.querySelector('[data-cursor-el]');
  const label = el.querySelector('span');
  const pos = { x: -200, y: -200, tx: -200, ty: -200, s: 0, ts: 0 };
  let raf = 0;

  const loop = () => {
    raf = 0;
    pos.x += (pos.tx - pos.x) * 0.22;
    pos.y += (pos.ty - pos.y) * 0.22;
    pos.s += (pos.ts - pos.s) * 0.18;
    el.style.transform = `translate3d(${pos.x.toFixed(1)}px, ${pos.y.toFixed(1)}px, 0) scale(${pos.s.toFixed(3)})`;
    if (Math.abs(pos.tx - pos.x) > 0.2 || Math.abs(pos.ty - pos.y) > 0.2 || Math.abs(pos.ts - pos.s) > 0.002) {
      raf = requestAnimationFrame(loop);
    }
  };
  const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };

  window.addEventListener('pointermove', (e) => {
    pos.tx = e.clientX;
    pos.ty = e.clientY;
    if (pos.s < 0.02) { pos.x = pos.tx; pos.y = pos.ty; }
    kick();
  }, { passive: true });

  document.querySelectorAll('[data-cursor]').forEach((target) => {
    target.addEventListener('pointerenter', () => {
      label.textContent = target.dataset.cursor;
      pos.ts = 1;
      kick();
    });
    target.addEventListener('pointerleave', () => {
      pos.ts = 0;
      kick();
    });
  });
}
