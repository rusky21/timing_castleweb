/**
 * 🏰 CASTLEWEB — Cloudflare Worker: Telegram API Reverse Proxy
 * 
 * Назначение:
 * Проксирует запросы от вашего бэкенда к api.telegram.org.
 * Обходит любые блокировки IP, сетевые задержки провайдеров и таймауты.
 * Тариф: 100% бесплатный (до 100 000 запросов/день).
 * 
 * Как развернуть:
 * 1. Зайдите в панель Cloudflare -> Workers & Pages -> Create Worker.
 * 2. Вставьте этот код и нажмите "Deploy".
 * 3. Скопируйте полученный URL (например, https://tg-proxy.your-name.workers.dev)
 * 4. Укажите его в .env: TELEGRAM_API_BASE_URL="https://tg-proxy.your-name.workers.dev/bot"
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Заменяем хост на официальный api.telegram.org
    const telegramUrl = new URL(`https://api.telegram.org${url.pathname}${url.search}`);

    // Копируем исходные заголовки
    const newHeaders = new Headers(request.headers);
    newHeaders.set('Host', 'api.telegram.org');

    try {
      const response = await fetch(telegramUrl.toString(), {
        method: request.method,
        headers: newHeaders,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
        redirect: 'follow',
      });
      return response;
    } catch (err) {
      return new Response(JSON.stringify({ ok: false, error: err.message }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
