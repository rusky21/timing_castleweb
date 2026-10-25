// Hero «Замок во фьорде»: процедурная сцена, пересобранная из символов кода.
// Сцена рисуется в офскрин-canvas, усредняется по сетке ячеек и превращается в мозаику.
// Под курсором линза показывает исходную картину, по краю линзы символы перебираются.

const RAMP = [
  ['@', '#', '%', '&', '$', '0', '8', 'B', 'W'],
  ['{', '}', '[', ']', '=', '+', '*', '0', '1'],
  ['<', '>', '/', '\\', '(', ')', ';', '!', '?'],
  [':', '-', '~', '_', '"', '^', 'i', 'l', 'r'],
  ['.', ',', "'", '`', ':', '-'],
];
const SCRAMBLE = '{}[]<>/\\=+*;:01#%&$@?!';

function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ---------- Сцена: сумеречный фьорд с замком ---------- */

// Плавный одномерный шум для хребтов и облаков
function makeNoise(seed) {
  const r = mulberry32(seed);
  const pts = Array.from({ length: 512 }, () => r());
  return (x) => {
    const i = Math.floor(x);
    const f = x - i;
    const a = pts[((i % 512) + 512) % 512];
    const b = pts[(((i + 1) % 512) + 512) % 512];
    const t = f * f * (3 - 2 * f);
    return a + (b - a) * t;
  };
}
const fbm = (noise, x, octaves = 5) => {
  let v = 0, amp = 0.5, freq = 1, norm = 0;
  for (let o = 0; o < octaves; o++) {
    v += noise(x * freq) * amp;
    norm += amp;
    amp *= 0.5;
    freq *= 2.07;
  }
  return v / norm;
};

// Острые хребты: «гребневой» шум с резкими вершинами
const ridged = (noise, x, octaves = 6) => {
  let v = 0, amp = 0.5, freq = 1, norm = 0;
  for (let o = 0; o < octaves; o++) {
    let n = 1 - Math.abs(2 * noise(x * freq) - 1);
    n *= n;
    v += n * amp;
    norm += amp;
    amp *= 0.5;
    freq *= 2.1;
  }
  return v / norm;
};

// Возвращает маску воды (белым), чтобы мозаика знала, где мерцать
function paintScene(ctx, W, H) {
  const rand = mulberry32(11);
  const narrow = W / H < 1.35;
  const hY = Math.round(H * 0.66);
  // масштаб деталей; в вертикальном кадре телефона считаем от ширины, иначе замок теряется
  const u = narrow ? W / 420 : Math.min(H, W * 0.75) / 600;
  const vh = narrow ? Math.min(H, W * 1.1) : H; // высота гор не растягивается в вертикальном кадре

  // Всё, что выше линии воды, рисуем отдельно — потом это же отразится в воде
  const above = document.createElement('canvas');
  above.width = W;
  above.height = hY;
  const a = above.getContext('2d');

  // Небо: синий час, без солнца
  const sky = a.createLinearGradient(0, 0, 0, hY);
  sky.addColorStop(0, '#1F2940');
  sky.addColorStop(0.45, '#3D4B68');
  sky.addColorStop(0.8, '#76809A');
  sky.addColorStop(1, '#A3A3AF');
  a.fillStyle = sky;
  a.fillRect(0, 0, W, hY);

  // Остаток заката у горизонта, очень приглушённый
  const ember = a.createLinearGradient(0, hY - H * 0.25, 0, hY);
  ember.addColorStop(0, 'rgba(196, 160, 158, 0)');
  ember.addColorStop(1, 'rgba(196, 160, 158, 0.3)');
  a.fillStyle = ember;
  a.fillRect(0, hY - H * 0.25, W, H * 0.25);

  // Луна за облаками
  const mx = W * (narrow ? 0.24 : 0.2), my = H * 0.17, mr = 26 * u;
  const halo = a.createRadialGradient(mx, my, mr * 0.5, mx, my, mr * 6);
  halo.addColorStop(0, 'rgba(225, 228, 238, 0.45)');
  halo.addColorStop(1, 'rgba(225, 228, 238, 0)');
  a.fillStyle = halo;
  a.fillRect(0, 0, W, hY);
  a.fillStyle = '#E8E6DE';
  a.beginPath();
  a.arc(mx, my, mr, 0, Math.PI * 2);
  a.fill();
  a.fillStyle = 'rgba(160, 165, 180, 0.35)';
  a.beginPath();
  a.arc(mx - mr * 0.3, my - mr * 0.2, mr * 0.28, 0, Math.PI * 2);
  a.arc(mx + mr * 0.35, my + mr * 0.25, mr * 0.18, 0, Math.PI * 2);
  a.fill();

  // Слоистые облака: вытянутые полосы с подсвеченными краями
  const cloudNoise = makeNoise(5);
  for (let band = 0; band < 7; band++) {
    const by = H * (0.06 + band * 0.07) + rand() * H * 0.03;
    const thick = H * (0.025 + rand() * 0.035);
    const light = band < 3 ? 0.18 : 0.28;
    for (let x = -40; x < W + 40; x += 6 * u) {
      const n = fbm(cloudNoise, x / (W * 0.18) + band * 7.3, 4);
      if (n < 0.46) continue;
      const k = (n - 0.46) / 0.54;
      const h = thick * (0.4 + k * 1.4);
      const g = a.createLinearGradient(0, by - h, 0, by + h);
      g.addColorStop(0, `rgba(196, 202, 218, ${light * k})`);
      g.addColorStop(0.55, `rgba(110, 120, 145, ${0.35 * k})`);
      g.addColorStop(1, 'rgba(60, 70, 95, 0)');
      a.fillStyle = g;
      a.fillRect(x, by - h, 7 * u, h * 2);
    }
  }

  // Горы: четыре слоя, дальние светлее и туманнее
  const ridge = (seed, base, amp, scale, color, snow, peakX, peakH) => {
    const noise = makeNoise(seed);
    const pts = [];
    for (let x = 0; x <= W; x += 2) {
      let y = base - ridged(noise, x / scale) * amp;
      if (peakX !== undefined) {
        const d = (x / W - peakX) / 0.09;
        y -= Math.exp(-d * d) * peakH;
      }
      pts.push([x, y]);
    }
    const fillRidge = (dy, fill) => {
      a.beginPath();
      a.moveTo(0, hY);
      pts.forEach(([x, y]) => a.lineTo(x, y + dy));
      a.lineTo(W, hY);
      a.closePath();
      a.fillStyle = fill;
      a.fill();
    };
    const rock = a.createLinearGradient(0, base - amp, 0, hY);
    rock.addColorStop(0, color);
    rock.addColorStop(1, '#3A4258');
    fillRidge(0, rock);
    // снег только на самых высоких вершинах: мягкий переход и прожилки вниз по склонам
    if (snow) {
      const top = Math.min(...pts.map((pt) => pt[1]));
      const line = top + (base - top) * 0.45;
      a.save();
      fillRidge(0, 'rgba(0,0,0,0)');
      a.clip();
      const cap = a.createLinearGradient(0, top, 0, line);
      cap.addColorStop(0, 'rgba(208, 213, 226, 0.95)');
      cap.addColorStop(0.55, 'rgba(208, 213, 226, 0.45)');
      cap.addColorStop(1, 'rgba(208, 213, 226, 0)');
      a.fillStyle = cap;
      a.fillRect(0, top, W, line - top);
      const r = mulberry32(seed * 7);
      for (let i = 0; i < pts.length; i += 3) {
        const [x, y] = pts[i];
        if (y > line || r() < 0.5) continue;
        const len = (line - y) * (0.4 + r() * 1.1);
        const g = a.createLinearGradient(0, y, 0, y + len);
        g.addColorStop(0, 'rgba(214, 219, 232, 0.55)');
        g.addColorStop(1, 'rgba(214, 219, 232, 0)');
        a.fillStyle = g;
        a.fillRect(x, y, 2 + r() * 3, len);
      }
      a.restore();
    }
    // теневые грани склонов
    a.save();
    a.globalAlpha = 0.18;
    a.fillStyle = '#1C2232';
    for (let i = 1; i < pts.length - 1; i++) {
      if (pts[i + 1][1] > pts[i][1]) a.fillRect(pts[i][0], pts[i][1] + H * 0.01, 2, (hY - pts[i][1]) * 0.6);
    }
    a.restore();
  };
  const fog = (y, h, alpha) => {
    const g = a.createLinearGradient(0, y - h, 0, y + h);
    g.addColorStop(0, 'rgba(178, 184, 200, 0)');
    g.addColorStop(0.5, `rgba(178, 184, 200, ${alpha})`);
    g.addColorStop(1, 'rgba(178, 184, 200, 0)');
    a.fillStyle = g;
    a.fillRect(0, y - h, W, h * 2);
  };

  ridge(3, hY - vh * 0.14, vh * 0.3, W * 0.32, '#8590A8', true, narrow ? 0.4 : 0.52, vh * 0.1);
  fog(hY - H * 0.12, H * 0.06, 0.35);
  ridge(8, hY - vh * 0.07, vh * 0.2, W * 0.2, '#647089', true);
  fog(hY - H * 0.05, H * 0.05, 0.3);
  ridge(13, hY - vh * 0.015, vh * 0.11, W * 0.11, '#4A5470', false);
  fog(hY - H * 0.01, H * 0.035, 0.28);

  // Скала с замком: верх рисуется над водой, низ — поверх воды
  const cliffX = W * (narrow ? 0.5 : 0.58);
  const plateau = hY - vh * 0.14;
  const castleX = W * (narrow ? 0.73 : 0.76);
  const cliffPath = (c) => {
    const n = makeNoise(21);
    c.beginPath();
    c.moveTo(cliffX - W * 0.05, H);
    c.lineTo(cliffX - W * 0.02, hY + H * 0.03);
    // скальный склон с неровной кромкой
    for (let t = 0; t <= 1; t += 0.02) {
      const x = cliffX + t * (castleX - W * 0.14 - cliffX);
      const y = hY - t * (hY - plateau) - (n(t * 9) - 0.5) * H * 0.03;
      c.lineTo(x, y);
    }
    c.lineTo(castleX + W * 0.12, plateau - H * 0.005);
    for (let t = 0; t <= 1; t += 0.05) {
      const x = castleX + W * 0.12 + t * (W - castleX - W * 0.12);
      c.lineTo(x, plateau + t * H * 0.08 + (n(t * 7 + 3) - 0.5) * H * 0.02);
    }
    c.lineTo(W, H);
    c.closePath();
  };
  const paintCliff = (c, clipTop, clipBottom) => {
    c.save();
    c.beginPath();
    c.rect(0, clipTop, W, clipBottom - clipTop);
    c.clip();
    cliffPath(c);
    const rock = c.createLinearGradient(0, plateau, 0, H);
    rock.addColorStop(0, '#3E4658');
    rock.addColorStop(0.4, '#2C3342');
    rock.addColorStop(1, '#181D27');
    c.fillStyle = rock;
    c.fill();
    c.clip();
    // пласты породы и холодный блик по верхней кромке
    const r = mulberry32(31);
    for (let i = 0; i < 160; i++) {
      const x = cliffX - W * 0.05 + r() * (W - cliffX + W * 0.05);
      const y = plateau + r() * (H - plateau);
      c.fillStyle = r() > 0.4 ? 'rgba(10, 13, 20, 0.35)' : 'rgba(120, 130, 155, 0.18)';
      c.fillRect(x, y, (2 + r() * 3) * u, (10 + r() * 40) * u);
    }
    const rim = c.createLinearGradient(0, plateau - H * 0.02, 0, plateau + H * 0.05);
    rim.addColorStop(0, 'rgba(150, 160, 185, 0.45)');
    rim.addColorStop(1, 'rgba(150, 160, 185, 0)');
    c.fillStyle = rim;
    c.fillRect(0, plateau - H * 0.02, W, H * 0.07);
    c.restore();
  };
  paintCliff(a, 0, hY);
  paintCastle(a, castleX, plateau + 2 * u, u * (narrow ? 1 : 1.7));

  // Основной холст: верх сцены, вода с отражением, низ скалы, деревья
  ctx.drawImage(above, 0, 0);

  const water = ctx.createLinearGradient(0, hY, 0, H);
  water.addColorStop(0, '#4A5470');
  water.addColorStop(0.35, '#2A3248');
  water.addColorStop(1, '#141925');
  ctx.fillStyle = water;
  ctx.fillRect(0, hY, W, H - hY);

  // Отражение: перевёрнутая верхняя часть, полосами с лёгкой рябью
  const strip = Math.max(2, Math.round(2 * u));
  for (let y = hY; y < H; y += strip) {
    const d = y - hY;
    const srcY = hY - d * 1.05;
    if (srcY < 0) break;
    const dx = Math.sin(d * 0.09) * (2 + d * 0.02) * u;
    ctx.globalAlpha = 0.42 * (1 - d / (H - hY));
    ctx.drawImage(above, 0, srcY, W, strip, dx, y, W, strip);
  }
  ctx.globalAlpha = 1;
  // туман над водой
  const mist = ctx.createLinearGradient(0, hY - H * 0.02, 0, hY + H * 0.05);
  mist.addColorStop(0, 'rgba(170, 176, 194, 0)');
  mist.addColorStop(0.4, 'rgba(170, 176, 194, 0.35)');
  mist.addColorStop(1, 'rgba(170, 176, 194, 0)');
  ctx.fillStyle = mist;
  ctx.fillRect(0, hY - H * 0.02, W, H * 0.07);
  // светлые штрихи ряби
  for (let i = 0; i < 220; i++) {
    const y = hY + Math.pow(rand(), 1.5) * (H - hY);
    const x = rand() * W;
    ctx.fillStyle = `rgba(190, 198, 220, ${0.08 + rand() * 0.14})`;
    ctx.fillRect(x, y, (8 + rand() * 40) * u, Math.max(1, u));
  }

  paintCliff(ctx, hY, H);

  // Маска воды: всё ниже горизонта, кроме скалы
  const mask = document.createElement('canvas');
  mask.width = W;
  mask.height = H;
  const m = mask.getContext('2d');
  m.fillStyle = '#FFFFFF';
  m.fillRect(0, hY, W, H - hY);
  m.globalCompositeOperation = 'destination-out';
  cliffPath(m);
  m.fill();

  // Ели по краям — тёмные силуэты, рамка для картины
  const pine = (x, baseY, h, w, color) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    const tiers = 9;
    ctx.moveTo(x, baseY - h);
    for (let i = 1; i <= tiers; i++) {
      const y = baseY - h + (h * i) / tiers;
      const half = (w * i) / tiers;
      ctx.lineTo(x + half, y);
      ctx.lineTo(x + half * 0.45, y - h / tiers * 0.15);
    }
    for (let i = tiers; i >= 1; i--) {
      const y = baseY - h + (h * i) / tiers;
      const half = (w * i) / tiers;
      ctx.lineTo(x - half * 0.45, y - h / tiers * 0.15);
      ctx.lineTo(x - half, y);
    }
    ctx.closePath();
    ctx.fill();
    ctx.fillRect(x - w * 0.04, baseY - h * 0.05, w * 0.08, h * 0.08);
  };
  const shoreY = H * 0.86;
  ctx.fillStyle = '#121720';
  ctx.beginPath();
  ctx.moveTo(0, H);
  ctx.lineTo(0, shoreY);
  ctx.quadraticCurveTo(W * 0.12, shoreY - H * 0.03, W * (narrow ? 0.3 : 0.24), H);
  ctx.closePath();
  ctx.fill();
  const trees = narrow
    ? [[0.03, 0.62, 0.09], [0.1, 0.48, 0.07], [0.17, 0.36, 0.05]]
    : [[0.025, 0.7, 0.07], [0.075, 0.55, 0.055], [0.12, 0.42, 0.045], [0.16, 0.3, 0.035]];
  trees.forEach(([tx, th, tw], i) => pine(W * tx, shoreY + H * 0.02, H * th, W * tw, i % 2 ? '#1A202C' : '#141922'));
  pine(W * 0.985, H * 1.02, H * 0.5, W * (narrow ? 0.08 : 0.05), '#10141C');

  return mask;
}

function paintCastle(ctx, cx, baseY, u) {
  const LIGHT = '#5A6480';
  const SHADE = '#3A4157';
  const DARK = '#262C3B';
  const ROOF = '#2B3245';
  const ROOF_LIT = '#465072';
  const WINDOW = '#F2C67F';
  const rand = mulberry32(77);

  const windows = [];
  const block = (x, w, h, { roof = null, merlons = true, rows = 3 } = {}) => {
    const left = cx + x * u;
    const top = baseY - h * u;
    ctx.fillStyle = LIGHT;
    ctx.fillRect(left, top, w * u * 0.58, h * u);
    ctx.fillStyle = SHADE;
    ctx.fillRect(left + w * u * 0.58, top, w * u * 0.42 + 0.5, h * u);
    if (merlons && !roof) {
      const n = Math.max(2, Math.round(w / 3.2));
      const mw = (w * u) / (n * 2 - 1);
      for (let i = 0; i < n; i++) {
        ctx.fillStyle = i / n < 0.58 ? LIGHT : SHADE;
        ctx.fillRect(left + i * mw * 2, top - mw * 1.2, mw, mw * 1.2);
      }
    }
    if (roof === 'cone') {
      const rh = w * u * 1.9;
      ctx.fillStyle = ROOF;
      ctx.beginPath();
      ctx.moveTo(left - u * 1.6, top);
      ctx.lineTo(left + (w * u) / 2, top - rh);
      ctx.lineTo(left + w * u + u * 1.6, top);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = ROOF_LIT;
      ctx.beginPath();
      ctx.moveTo(left - u * 1.6, top);
      ctx.lineTo(left + (w * u) / 2, top - rh);
      ctx.lineTo(left + (w * u) * 0.35, top);
      ctx.closePath();
      ctx.fill();
    }
    if (roof === 'gable') {
      ctx.fillStyle = ROOF;
      ctx.beginPath();
      ctx.moveTo(left - u, top);
      ctx.lineTo(left + w * u * 0.5, top - w * u * 0.55);
      ctx.lineTo(left + w * u + u, top);
      ctx.closePath();
      ctx.fill();
    }
    // окна рядами, часть горит тёплым светом
    for (let r = 0; r < rows; r++) {
      const wy = top + (h * u) * (0.18 + r * (0.62 / Math.max(1, rows)));
      const cols = Math.max(1, Math.floor(w / 7));
      for (let c = 0; c < cols; c++) {
        const wx = left + (w * u) * ((c + 0.5) / cols) - u * 1.1;
        const lit = rand() < 0.55;
        windows.push([wx, wy, lit]);
      }
    }
    return { left, top };
  };

  // мост-аркада к скале
  ctx.fillStyle = SHADE;
  ctx.fillRect(cx - 96 * u, baseY - 10 * u, 30 * u, 10 * u);
  ctx.fillStyle = DARK;
  for (let i = 0; i < 3; i++) {
    const ax = cx - 92 * u + i * 9 * u;
    ctx.beginPath();
    ctx.moveTo(ax, baseY);
    ctx.lineTo(ax, baseY - 5 * u);
    ctx.arc(ax + 2.5 * u, baseY - 5 * u, 2.5 * u, Math.PI, 0);
    ctx.lineTo(ax + 5 * u, baseY);
    ctx.fill();
  }

  block(-70, 132, 24, { rows: 1 });                 // крепостная стена
  block(-76, 13, 50, { roof: 'cone', rows: 2 });
  block(-54, 10, 38, { rows: 2 });
  block(-36, 22, 66, { rows: 4 });                   // донжон
  const spire = block(-10, 10, 98, { roof: 'cone', rows: 5 });
  block(4, 26, 54, { roof: 'gable', rows: 3 });      // главный зал
  block(32, 13, 78, { roof: 'cone', rows: 4 });
  block(50, 10, 44, { roof: 'cone', rows: 2 });

  // ворота
  ctx.fillStyle = DARK;
  ctx.beginPath();
  ctx.moveTo(cx + 12 * u, baseY);
  ctx.lineTo(cx + 12 * u, baseY - 9 * u);
  ctx.arc(cx + 17 * u, baseY - 9 * u, 5 * u, Math.PI, 0);
  ctx.lineTo(cx + 22 * u, baseY);
  ctx.closePath();
  ctx.fill();

  // окна: тёмные и горящие, у горящих — мягкое свечение
  windows.forEach(([wx, wy, lit]) => {
    if (lit) {
      const g = ctx.createRadialGradient(wx + u, wy + 2 * u, 0, wx + u, wy + 2 * u, 9 * u);
      g.addColorStop(0, 'rgba(242, 198, 127, 0.35)');
      g.addColorStop(1, 'rgba(242, 198, 127, 0)');
      ctx.fillStyle = g;
      ctx.fillRect(wx - 8 * u, wy - 7 * u, 18 * u, 18 * u);
    }
    ctx.fillStyle = lit ? WINDOW : DARK;
    ctx.fillRect(wx, wy, 2.2 * u, 3.6 * u);
  });

  // флаг на шпиле
  const fx = spire.left + 5 * u;
  const fy = spire.top - 10 * u * 1.9;
  ctx.fillStyle = DARK;
  ctx.fillRect(fx - 0.4 * u, fy - 12 * u, 0.8 * u, 12 * u);
  ctx.fillStyle = '#3D5BE0';
  ctx.beginPath();
  ctx.moveTo(fx + 0.4 * u, fy - 12 * u);
  ctx.lineTo(fx + 10 * u, fy - 9.5 * u);
  ctx.lineTo(fx + 0.4 * u, fy - 7 * u);
  ctx.closePath();
  ctx.fill();
}

/* ---------- Мозаика ---------- */

export function initMosaic(root, { reduced = false, watch = root } = {}) {
  const canvas = root.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const countEl = document.querySelector('[data-glyph-count]');

  let W, H, dpr, cell, cols, rows;
  let scene, base, bctx, data, glyphIdx, seaCells, delays, state;
  let introStart = 0, introDone = false;
  let visible = true, raf = 0;
  const lens = { x: 0, y: 0, tx: 0, ty: 0, r: 0, tr: 0, touchTimer: 0 };

  function build() {
    const rect = root.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.round(rect.width * dpr);
    H = Math.round(rect.height * dpr);
    if (!W || !H) return;
    canvas.width = W;
    canvas.height = H;

    cell = Math.round((rect.width < 640 ? 7 : 9) * dpr);
    cols = Math.ceil(W / cell);
    rows = Math.ceil(H / cell);

    scene = document.createElement('canvas');
    scene.width = W;
    scene.height = H;
    const waterMask = paintScene(scene.getContext('2d'), W, H);
    const msmall = document.createElement('canvas');
    msmall.width = cols;
    msmall.height = rows;
    const mctx2 = msmall.getContext('2d', { willReadFrequently: true });
    mctx2.drawImage(waterMask, 0, 0, cols, rows);
    const water = mctx2.getImageData(0, 0, cols, rows).data;

    // Усреднение по ячейкам в два шага, чтобы не было алиасинга
    const mid = document.createElement('canvas');
    mid.width = cols * 4;
    mid.height = rows * 4;
    const mctx = mid.getContext('2d');
    mctx.imageSmoothingQuality = 'high';
    mctx.drawImage(scene, 0, 0, mid.width, mid.height);
    const small = document.createElement('canvas');
    small.width = cols;
    small.height = rows;
    const sctx = small.getContext('2d', { willReadFrequently: true });
    sctx.imageSmoothingQuality = 'high';
    sctx.drawImage(mid, 0, 0, cols, rows);
    data = sctx.getImageData(0, 0, cols, rows).data;

    const rand = mulberry32(42);
    const n = cols * rows;
    glyphIdx = new Uint8Array(n);
    delays = new Float32Array(n);
    state = new Uint8Array(n);
    seaCells = [];
    for (let i = 0; i < n; i++) {
      glyphIdx[i] = Math.floor(rand() * 9);
      const c = i % cols;
      delays[i] = rand() * 0.5 + (c / cols) * 0.5;
      if (water[i * 4 + 3] > 200) seaCells.push(i);
    }

    base = document.createElement('canvas');
    base.width = W;
    base.height = H;
    bctx = base.getContext('2d');
    bctx.fillStyle = '#1C222E';
    bctx.fillRect(0, 0, W, H);
    const font = `600 ${Math.round(cell * 1.1)}px ${getComputedStyle(document.documentElement).getPropertyValue('--mono') || 'monospace'}`;
    bctx.font = font;
    bctx.textAlign = 'center';
    bctx.textBaseline = 'middle';
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (countEl) countEl.textContent = n.toLocaleString('ru-RU');

    if (reduced) {
      for (let i = 0; i < n; i++) drawCell(bctx, i, 0, null);
      introDone = true;
      compose();
    } else {
      introStart = performance.now();
      introDone = false;
      start();
    }
  }

  function glyphFor(i, lumShift) {
    const R = data[i * 4], G = data[i * 4 + 1], B = data[i * 4 + 2];
    const lum = (0.299 * R + 0.587 * G + 0.114 * B) / 255 + lumShift;
    const bucket = lum < 0.25 ? 0 : lum < 0.42 ? 1 : lum < 0.6 ? 2 : lum < 0.78 ? 3 : 4;
    const set = RAMP[bucket];
    return { ch: set[glyphIdx[i] % set.length], lum, R, G, B };
  }

  // shift: сдвиг яркости для мерцания моря; ghost: символ без цвета (фаза «набора»)
  function drawCell(target, i, shift, ghost) {
    const x = (i % cols) * cell;
    const y = ((i / cols) | 0) * cell;
    if (ghost) {
      target.fillStyle = '#1C222E';
      target.fillRect(x, y, cell, cell);
      target.fillStyle = '#56607A';
      target.fillText(ghost, x + cell / 2, y + cell / 2 + dpr * 0.5);
      return;
    }
    const { ch, lum, R, G, B } = glyphFor(i, shift);
    const k = 1 + shift * 1.6;
    target.fillStyle = `rgb(${Math.min(255, R * k)},${Math.min(255, G * k)},${Math.min(255, B * k)})`;
    target.fillRect(x, y, cell, cell);
    const m = lum > 0.55 ? 0.66 : 1.5;
    const add = m > 1 ? 28 : 0;
    target.fillStyle = `rgb(${Math.min(255, R * m * k + add)},${Math.min(255, G * m * k + add)},${Math.min(255, B * m * k + add)})`;
    target.fillText(ch, x + cell / 2, y + cell / 2 + dpr * 0.5);
  }

  function stepIntro(now) {
    const t = (now - introStart) / 1600;
    const n = cols * rows;
    for (let i = 0; i < n; i++) {
      if (state[i] === 2) continue;
      const d = delays[i];
      if (t >= d + 0.12) {
        drawCell(bctx, i, 0, null);
        state[i] = 2;
      } else if (t >= d && state[i] === 0) {
        drawCell(bctx, i, 0, SCRAMBLE[(Math.random() * SCRAMBLE.length) | 0]);
        state[i] = 1;
      }
    }
    if (t >= 1.12) introDone = true;
  }

  function stepSea(now) {
    const count = Math.min(seaCells.length, Math.ceil(seaCells.length * 0.015));
    const time = now / 1000;
    for (let k = 0; k < count; k++) {
      const i = seaCells[(Math.random() * seaCells.length) | 0];
      const c = i % cols;
      const r = (i / cols) | 0;
      const wave = Math.sin(time * 1.3 + c * 0.22 - r * 0.6) * 0.06 + Math.sin(time * 0.7 + c * 0.05) * 0.03;
      glyphIdx[i] = (glyphIdx[i] + 1) % 9;
      drawCell(bctx, i, wave, null);
    }
  }

  function compose() {
    ctx.drawImage(base, 0, 0);
    if (lens.r < 1) return;
    ctx.save();
    ctx.beginPath();
    ctx.arc(lens.x, lens.y, lens.r, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(scene, 0, 0);
    ctx.restore();

    // Кольцо перебираемых символов по краю линзы
    const reach = lens.r + cell * 1.5;
    const c0 = Math.max(0, Math.floor((lens.x - reach) / cell));
    const c1 = Math.min(cols - 1, Math.ceil((lens.x + reach) / cell));
    const r0 = Math.max(0, Math.floor((lens.y - reach) / cell));
    const r1 = Math.min(rows - 1, Math.ceil((lens.y + reach) / cell));
    for (let r = r0; r <= r1; r++) {
      for (let c = c0; c <= c1; c++) {
        const dx = c * cell + cell / 2 - lens.x;
        const dy = r * cell + cell / 2 - lens.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d > lens.r - cell * 1.2 && d < lens.r + cell * 0.6) {
          const i = r * cols + c;
          const R = data[i * 4], G = data[i * 4 + 1], B = data[i * 4 + 2];
          ctx.fillStyle = `rgb(${R},${G},${B})`;
          ctx.fillRect(c * cell, r * cell, cell, cell);
          ctx.fillStyle = 'rgba(255,255,255,0.9)';
          ctx.fillText(SCRAMBLE[(Math.random() * SCRAMBLE.length) | 0], c * cell + cell / 2, r * cell + cell / 2 + dpr * 0.5);
        }
      }
    }
  }

  function frame(now) {
    raf = 0;
    if (!introDone) stepIntro(now);
    else if (!reduced) stepSea(now);

    lens.x += (lens.tx - lens.x) * 0.22;
    lens.y += (lens.ty - lens.y) * 0.22;
    lens.r += (lens.tr - lens.r) * 0.16;

    compose();
    if (visible || !introDone || lens.tr > 0 || lens.r > 0.5) start();
  }

  function start() {
    if (!raf && !reduced) raf = requestAnimationFrame(frame);
  }

  function setLens(e, on) {
    const rect = canvas.getBoundingClientRect();
    lens.tx = (e.clientX - rect.left) * dpr;
    lens.ty = (e.clientY - rect.top) * dpr;
    if (on && lens.r < 1) { lens.x = lens.tx; lens.y = lens.ty; }
    lens.tr = on ? Math.min(150 * dpr, H * 0.3) : 0;
    if (reduced) {
      lens.x = lens.tx; lens.y = lens.ty; lens.r = lens.tr;
      compose();
    } else {
      start();
    }
  }

  canvas.addEventListener('pointermove', (e) => { if (e.pointerType === 'mouse') setLens(e, true); });
  canvas.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') setLens(e, false); });
  canvas.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse') return;
    setLens(e, true);
    clearTimeout(lens.touchTimer);
    lens.touchTimer = setTimeout(() => setLens(e, false), 1400);
  });

  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) start();
  }).observe(watch);

  // Перестраиваем при смене ширины или заметной смене высоты (мелкие скачки адресной строки на телефоне игнорируем)
  let lastWidth = 0;
  let lastHeight = 0;
  let resizeTimer = 0;
  new ResizeObserver(([entry]) => {
    const w = Math.round(entry.contentRect.width);
    const h = Math.round(entry.contentRect.height);
    if (w === lastWidth && Math.abs(h - lastHeight) < 120) return;
    const first = lastWidth === 0;
    lastWidth = w;
    lastHeight = h;
    clearTimeout(resizeTimer);
    if (first) build();
    else resizeTimer = setTimeout(build, 180);
  }).observe(root);
}
