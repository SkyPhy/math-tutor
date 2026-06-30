import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The FastAPI backend (consensus grading / diagnosis / tags / memory) stays as-is
// and serves on :8000 with open CORS, so the SPA calls it directly. Override the
// base URL with VITE_API_BASE (see src/config.ts). A dev proxy is also wired for
// teams that prefer a same-origin `/api` prefix.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
});
