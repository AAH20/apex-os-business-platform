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
          // Add trailing slash to API paths to avoid backend redirect (CORS issue)
          if (!path.endsWith('/') && !path.includes('?')) {
            return path + '/'
          }
          return path
        },
      },
    },
  },
})
