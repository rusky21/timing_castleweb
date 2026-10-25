// Абзац «О студии» проявляется по словам по мере прокрутки.
import { onScroll, clamp } from './scroll.js';

export function initWords(el, { reduced = false } = {}) {
  if (!el) return;
  const words = [];

  [...el.childNodes].forEach((node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const frag = document.createDocumentFragment();
      node.textContent.split(/(\s+)/).forEach((part) => {
        if (!part) return;
        if (/^\s+$/.test(part)) { frag.append(' '); return; }
        const span = document.createElement('span');
        span.className = 'w';
        span.textContent = part;
        frag.append(span);
        words.push(span);
      });
      node.replaceWith(frag);
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      node.classList.add('w');
      words.push(node);
    }
  });

  if (reduced) return;
  const n = words.length;
  let last = -1;

  onScroll((vh) => {
    const r = el.getBoundingClientRect();
    const p = clamp((vh * 0.85 - r.top) / (r.height + vh * 0.3));
    const lit = p * n * 1.1;
    if (Math.abs(lit - last) < 0.01) return;
    last = lit;
    words.forEach((w, i) => {
      w.style.opacity = (0.14 + 0.86 * clamp(lit - i)).toFixed(3);
    });
  });
}
