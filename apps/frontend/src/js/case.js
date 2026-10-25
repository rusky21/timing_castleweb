// Страницы кейсов: граница у шапки при скролле и фильтры на странице всех кейсов.

const header = document.querySelector('.lheader');
const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

const filters = document.querySelector('[data-filters]');
if (filters) {
  const buttons = [...filters.querySelectorAll('button')];
  const cards = [...document.querySelectorAll('[data-kind]')];
  const status = document.querySelector('[data-filter-status]');
  filters.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const kind = btn.dataset.filter;
    buttons.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
    let shown = 0;
    cards.forEach((card) => {
      const match = kind === 'all' || card.dataset.kind === kind;
      card.hidden = !match;
      if (match) shown += 1;
    });
    status.textContent = `Показано концептов: ${shown}`;
  });
}
