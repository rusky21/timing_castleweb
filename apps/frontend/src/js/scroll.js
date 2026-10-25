// Один планировщик на все эффекты, привязанные к скроллу: не больше одного пересчёта за кадр.

const subscribers = new Set();
let queued = false;

const run = () => {
  queued = false;
  const vh = window.innerHeight;
  subscribers.forEach((fn) => fn(vh));
};

export function requestFrame() {
  if (queued) return;
  queued = true;
  requestAnimationFrame(run);
}

export function onScroll(fn) {
  subscribers.add(fn);
  requestFrame();
  return () => subscribers.delete(fn);
}

export const clamp = (v, min = 0, max = 1) => Math.min(max, Math.max(min, v));

window.addEventListener('scroll', requestFrame, { passive: true });
window.addEventListener('resize', requestFrame);
