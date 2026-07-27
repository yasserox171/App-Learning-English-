import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev proxy → Django backend. In production, serve the built dist/ behind
// nginx on the same origin as the API (see backend/nginx.conf).
export default defineConfig({
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
