// Юридические страницы: граница у шапки при скролле и подсветка текущего раздела в содержании.

const header = document.querySelector('.lheader');
const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

const links = [...document.querySelectorAll('.toc a')];
const io = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    links.forEach((a) => a.classList.toggle('is-active', a.getAttribute('href') === `#${entry.target.id}`));
  });
}, { rootMargin: '-30% 0px -60% 0px' });
document.querySelectorAll('.clause').forEach((s) => io.observe(s));
