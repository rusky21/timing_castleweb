import { defineConfig } from 'vite';
import { resolve } from 'node:path';

const page = (name) => resolve(import.meta.dirname, name);

export default defineConfig({
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
        cases: page('cases.html'),
        aria: page('cases/aria.html'),
        onyx: page('cases/onyx.html'),
        hytte: page('cases/hytte.html'),
        sport: page('cases/sport.html'),
        photo: page('cases/photo.html'),
        vegas: page('cases/vegas.html'),
        notFound: page('404.html'),
      },
    },
  },
});
