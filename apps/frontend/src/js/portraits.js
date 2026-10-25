// Портреты основателей скрыты «спойлером», как в Telegram: фото размыто, поверх мерцают частицы.
// Наведение (или нажатие на телефоне) разгоняет частицы от точки касания и снимает размытие.

const DENSITY = 90; // CSS-пикселей площади на одну частицу

export function initPortraits(nodes, { reduced = false } = {}) {
  nodes.forEach((node) => {
    const canvas = node.querySelector('canvas');
    const ctx = canvas.getContext('2d');

    let W = 0, H = 0, dpr = 1, n = 0;
    let x, y, vx, vy, size, phase, speed;
    let cover = 1;          // 1 — спойлер на месте, 0 — частицы разлетелись
    let revealed = false;   // текущее состояние
    let pinned = false;     // открыто нажатием и не закрывается при уходе курсора
    let visible = false, raf = 0, last = 0;
    let ox = 0, oy = 0;     // точка, от которой разлетаются частицы

    const seed = () => {
      for (let i = 0; i < n; i++) {
        x[i] = Math.random() * W;
        y[i] = Math.random() * H;
        const a = Math.random() * Math.PI * 2;
        const v = (0.04 + Math.random() * 0.12) * dpr;
        vx[i] = Math.cos(a) * v;
        vy[i] = Math.sin(a) * v;
      }
    };

    const build = () => {
      const rect = node.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = Math.round(rect.width * dpr);
      H = Math.round(rect.height * dpr);
      if (!W || !H) return;
      canvas.width = W;
      canvas.height = H;
      n = Math.round((rect.width * rect.height) / DENSITY);
      x = new Float32Array(n); y = new Float32Array(n);
      vx = new Float32Array(n); vy = new Float32Array(n);
      size = new Float32Array(n); phase = new Float32Array(n); speed = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        size[i] = (Math.random() < 0.8 ? 1 : 1.6) * dpr;
        phase[i] = Math.random() * Math.PI * 2;
        speed[i] = 1.5 + Math.random() * 3;
      }
      seed();
      draw(performance.now());
    };

    const draw = (now) => {
      ctx.clearRect(0, 0, W, H);
      if (cover < 0.01) return;
      const t = now / 1000;
      ctx.fillStyle = '#FFFFFF';
      for (let i = 0; i < n; i++) {
        // мерцание каждой частицы со своей частотой
        const a = (0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * speed[i] + phase[i]))) * cover;
        if (a < 0.03) continue;
        ctx.globalAlpha = a;
        ctx.fillRect(x[i], y[i], size[i], size[i]);
      }
      ctx.globalAlpha = 1;
    };

    const step = (dt) => {
      const k = Math.min(3, dt / 16.7);
      if (revealed) {
        // разлёт от точки наведения
        for (let i = 0; i < n; i++) {
          const dx = x[i] - ox, dy = y[i] - oy;
          const d = Math.hypot(dx, dy) || 1;
          const push = (0.9 * dpr * k) / Math.max(0.35, d / (W * 0.5));
          vx[i] += (dx / d) * push * 0.08;
          vy[i] += (dy / d) * push * 0.08;
          x[i] += vx[i] * k;
          y[i] += vy[i] * k;
        }
        cover += (0 - cover) * 0.06 * k;
      } else {
        // броуновское движение, частицы не выходят за края
        for (let i = 0; i < n; i++) {
          vx[i] = (vx[i] + (Math.random() - 0.5) * 0.04 * dpr) * 0.985;
          vy[i] = (vy[i] + (Math.random() - 0.5) * 0.04 * dpr) * 0.985;
          x[i] += vx[i] * k;
          y[i] += vy[i] * k;
          if (x[i] < 0) x[i] += W; else if (x[i] > W) x[i] -= W;
          if (y[i] < 0) y[i] += H; else if (y[i] > H) y[i] -= H;
        }
        cover += (1 - cover) * 0.05 * k;
      }
    };

    const frame = (now) => {
      raf = 0;
      const dt = last ? now - last : 16.7;
      last = now;
      step(dt);
      draw(now);
      const settled = revealed && cover < 0.01;
      if (visible && !settled) raf = requestAnimationFrame(frame);
      else last = 0;
    };
    const start = () => { if (!raf && !reduced) raf = requestAnimationFrame(frame); };

    const setRevealed = (on, e) => {
      if (on === revealed) return;
      revealed = on;
      node.classList.toggle('is-revealed', on);
      node.setAttribute('aria-pressed', String(on));
      if (on) {
        if (e && 'clientX' in e && e.clientX) {
          const r = node.getBoundingClientRect();
          ox = (e.clientX - r.left) * dpr;
          oy = (e.clientY - r.top) * dpr;
        } else {
          ox = W / 2;
          oy = H / 2;
        }
      } else {
        seed(); // частицы возвращаются из случайных мест
      }
      if (reduced) { cover = on ? 0 : 1; draw(0); } else start();
    };

    node.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') setRevealed(true, e); });
    node.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && !pinned) setRevealed(false); });
    node.addEventListener('click', (e) => {
      if (e.pointerType === 'mouse') { pinned = !pinned; if (!pinned) setRevealed(false); else setRevealed(true, e); return; }
      pinned = !revealed;
      setRevealed(!revealed, e);
    });
    node.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      e.preventDefault();
      pinned = !revealed;
      setRevealed(!revealed);
    });

    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
    }, { rootMargin: '100px 0px' }).observe(node);

    let lastW = 0;
    new ResizeObserver(([entry]) => {
      const w = Math.round(entry.contentRect.width);
      if (w === lastW) return;
      lastW = w;
      build();
    }).observe(node);
  });
}
