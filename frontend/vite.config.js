import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development the API runs on http://127.0.0.1:8000 and is proxied,
// so the browser only ever talks to one origin (no CORS needed).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: {
    sourcemap: false,
    // Never inline assets as data: URIs - the Content-Security-Policy only
    // allows fonts and scripts from our own origin.
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ['recharts'],
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  test: {
    environment: 'node',
  },
})
