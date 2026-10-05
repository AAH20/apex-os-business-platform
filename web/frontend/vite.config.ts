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
        // The backend mixes two route conventions: /api/users/ and /api/leads/
        // are registered WITH a trailing slash, while /api/products, /api/invoices,
        // /api/employees, /api/tasks and /api/projects are registered WITHOUT one.
        // Starlette's redirect_slashes then answers the non-canonical form with a
        // 307 whose Location points straight at :8000.
        //
        // That is why this proxy must not simply pass those redirects through:
        // the browser would leave the Vite origin, the request becomes cross-origin,
        // and it fails preflight/CORS on every page.
        //
        // Do NOT re-add a rewrite() that strips trailing slashes - it rewrites
        // /api/products/ to /api/products, which the backend answers with a 307
        // back to /api/products/, i.e. a redirect loop.
        //
        // Instead, resolve the canonical URL inside the proxy (followRedirects)
        // so the browser only ever sees a same-origin 200.
        followRedirects: true,
        maxRedirects: 5,
      },
    },
  },
})
