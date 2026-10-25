import { initMosaic } from './mosaic.js';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
initMosaic(document.querySelector('[data-mosaic]'), { reduced });

// Показываем адрес, который не нашёлся
const path = document.querySelector('[data-path]');
if (path && location.pathname !== '/404.html') path.textContent = decodeURIComponent(location.pathname);
