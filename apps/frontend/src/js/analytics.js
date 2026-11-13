// Яндекс Метрика и согласие на cookie.
// Счётчик подключается только после того, как посетитель нажал «Принять» на плашке.
// Код счётчика вынесен из HTML в этот модуль: на проде действует CSP script-src 'self',
// встроенные скрипты она блокирует.

const COUNTER = 114237282;
const KEY = 'cw-cookie-consent'; // 'granted' | 'denied'
const TAG = `https://mc.yandex.ru/metrika/tag.js?id=${COUNTER}`;

const read = () => {
  try { return localStorage.getItem(KEY); } catch { return null; }
};
const write = (value) => {
  try { localStorage.setItem(KEY, value); } catch { /* приватный режим: выбор живёт до закрытия вкладки */ }
};

let loaded = false;

function loadMetrika() {
  if (loaded) return;
  loaded = true;
  window.ym = window.ym || function ym() { (window.ym.a = window.ym.a || []).push(arguments); };
  window.ym.l = Date.now();
  const script = document.createElement('script');
  script.async = true;
  script.src = TAG;
  document.head.append(script);
  window.ym(COUNTER, 'init', {
    ssr: true,
    webvisor: true,
    clickmap: true,
    ecommerce: 'dataLayer',
    referrer: document.referrer,
    url: location.href,
    accurateTrackBounce: true,
    trackLinks: true,
  });
}

// Цель в Метрике. Без согласия счётчика нет, и цель молча не отправляется.
export function reachGoal(name, params) {
  if (loaded) window.ym(COUNTER, 'reachGoal', name, params);
}

// При отзыве согласия удаляем cookie и записи localStorage, которые Метрика оставила на нашем домене
function dropMetrikaCookies() {
  try {
    Object.keys(localStorage).filter((k) => k.startsWith('_ym')).forEach((k) => localStorage.removeItem(k));
  } catch { /* хранилище недоступно */ }
  const host = location.hostname;
  const domains = ['', host, `.${host}`, `.${host.split('.').slice(-2).join('.')}`];
  document.cookie.split(';').forEach((pair) => {
    const name = pair.split('=')[0].trim();
    if (!name.startsWith('_ym')) return;
    domains.forEach((d) => {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${d ? `; domain=${d}` : ''}`;
    });
  });
}

let banner = null;

function closeBanner() {
  banner?.remove();
  banner = null;
}

function openBanner() {
  if (banner) return;
  banner = document.createElement('section');
  banner.className = 'cookie';
  banner.setAttribute('aria-label', 'Файлы cookie');
  banner.innerHTML = `
    <p class="cookie__text">С вашего согласия подключим Яндекс Метрику: она сохранит cookie, чтобы мы видели, как пользуются сайтом и работает ли реклама. <a href="/cookies.html">Политика cookie</a></p>
    <div class="cookie__actions">
      <button class="btn btn--light" type="button" data-cookie="granted">Принять</button>
      <button class="btn cookie__decline" type="button" data-cookie="denied">Отказаться</button>
    </div>`;
  banner.addEventListener('click', (e) => {
    const choice = e.target.closest('[data-cookie]')?.dataset.cookie;
    if (!choice) return;
    const was = read();
    write(choice);
    closeBanner();
    if (choice === 'granted') {
      loadMetrika();
    } else if (was === 'granted') {
      // Счётчик уже работает на этой странице: убираем его cookie и перезагружаем без него
      dropMetrikaCookies();
      location.reload();
    }
  });
  document.body.append(banner);
}

const choice = read();
if (choice === 'granted') loadMetrika();
else if (choice !== 'denied') openBanner();

// Кнопка «Изменить выбор» в политике cookie
document.addEventListener('click', (e) => {
  if (!e.target.closest('[data-cookie-settings]')) return;
  e.preventDefault();
  openBanner();
  banner.querySelector('button').focus();
});
