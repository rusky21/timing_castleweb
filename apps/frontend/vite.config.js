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
        case_alex_vance: resolve(__dirname, 'case-alex-vance.html'),
        case_apex: resolve(__dirname, 'case-apex.html'),
        case_aria: resolve(__dirname, 'case-aria.html'),
        case_hytte: resolve(__dirname, 'case-hytte.html'),
        case_onyx: resolve(__dirname, 'case-onyx.html'),
        case_sport_m: resolve(__dirname, 'case-sport-m.html'),
        case_vegas: resolve(__dirname, 'case-vegas.html'),
        privacy: resolve(__dirname, 'privacy.html'),
        terms: resolve(__dirname, 'terms.html'),
      },
    },
  },
});
