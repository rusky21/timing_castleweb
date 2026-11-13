import { defineConfig } from 'vite';
import { resolve } from 'node:path';
import { existsSync } from 'node:fs';

const page = (name) => resolve(import.meta.dirname, name);

// Адреса без расширения (/chat-boty, /oferta) отдаём как на проде, где nginx делает try_files $uri.html
const cleanUrls = () => {
  const rewrite = (root) => (req, _res, next) => {
    const [path, query = ''] = req.url.split('?');
    if (path !== '/' && !/\.[a-z0-9]+$/i.test(path) && existsSync(resolve(root, `.${path}.html`))) {
      req.url = `${path}.html${query && `?${query}`}`;
    }
    next();
  };
  return {
    name: 'clean-urls',
    configureServer(server) { server.middlewares.use(rewrite(import.meta.dirname)); },
    configurePreviewServer(server) { server.middlewares.use(rewrite(resolve(import.meta.dirname, 'dist'))); },
  };
};

export default defineConfig({
  plugins: [cleanUrls()],
  // Папка проекта лежит в OneDrive: нативные события файловой системы теряются, поэтому polling
  // /api проксируется на локальный FastAPI (uvicorn на :8000), как и на проде через nginx
  server: {
    port: 5173,
    strictPort: true,
    watch: { usePolling: true, interval: 300 },
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  preview: {
    port: 4173,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: {
    rollupOptions: {
      input: {
        main: page('index.html'),
        privacy: page('privacy.html'),
        terms: page('terms.html'),
        consent: page('consent.html'),
        cookies: page('cookies.html'),
        oferta: page('oferta.html'),
        cases: page('cases.html'),
        aria: page('cases/aria.html'),
        onyx: page('cases/onyx.html'),
        hytte: page('cases/hytte.html'),
        sport: page('cases/sport.html'),
        photo: page('cases/photo.html'),
        vegas: page('cases/vegas.html'),
        chatBoty: page('chat-boty.html'),
        saytPodKlyuch: page('sayt-pod-klyuch.html'),
        lichnyjKabinet: page('lichnyj-kabinet.html'),
        spasibo: page('spasibo.html'),
        notFound: page('404.html'),
      },
    },
  },
});
