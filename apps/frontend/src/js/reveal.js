// Появление блоков при прокрутке: один IntersectionObserver на всю страницу.
// Слова заголовков с data-split оборачиваются в маски, чтобы выезжать по очереди.

function splitWords(el) {
  let i = 0;
  const walk = (node) => {
    [...node.childNodes].forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        const frag = document.createDocumentFragment();
        child.textContent.split(/(\s+)/).forEach((part) => {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.append(' '); return; }
          const outer = document.createElement('span');
          outer.className = 'sw';
          const inner = document.createElement('span');
          inner.className = 'sw__i';
          inner.style.setProperty('--d', i++);
          inner.textContent = part;
          outer.append(inner);
          frag.append(outer);
        });
        child.replaceWith(frag);
      } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== 'BR') {
        walk(child);
      }
    });
  };
  walk(el);
}

export function initReveal({ reduced = false } = {}) {
  if (reduced) return;
  const targets = document.querySelectorAll('[data-split], [data-reveal], [data-line]');
  document.querySelectorAll('[data-split]').forEach(splitWords);

  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      io.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -10% 0px' });
  targets.forEach((el) => io.observe(el));
}
