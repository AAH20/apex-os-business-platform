import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'url'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => {
          // Remove trailing slash to match backend route definitions (avoids 307 redirect → CORS)
          if (path.endsWith('/') && !path.includes('?')) {
            return path.slice(0, -1)
          }
          return path
        },
      },
    },
  },
})
