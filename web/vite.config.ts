import { defineConfig } from 'vite'

// In development, Vite serves the page and forwards /api to the FastAPI server.
export default defineConfig({
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8765' },
  },
})
