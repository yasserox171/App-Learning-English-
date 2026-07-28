import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev proxy → Django backend. In production, serve the built dist/ behind
// nginx on the same origin as the API (see backend/nginx.conf).
export default defineConfig({
  // Served from /admin-panel/ behind nginx, so assets must resolve there.
  // Routing itself is hash-based, so no server-side rewrite is needed.
  base: '/admin-panel/',
  plugins: [react()],
  server: {
    port: Number(process.env.PORT) || 5173,
    proxy: {
      '/api': {
        target: process.env.API_ORIGIN || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
