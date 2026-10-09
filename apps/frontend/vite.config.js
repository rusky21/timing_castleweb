import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        cases: resolve(__dirname, 'cases.html'),
        brief: resolve(__dirname, 'brief.html'),
        policy: resolve(__dirname, 'policy.html'),
        instagram: resolve(__dirname, 'instagram.html'),
      },
    },
  },
});
