import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api/gc': { target: 'http://localhost:5001', rewrite: (p) => p.replace(/^\/api\/gc/, ''), changeOrigin: true },
      '/api/tr': { target: 'http://localhost:5002', rewrite: (p) => p.replace(/^\/api\/tr/, ''), changeOrigin: true },
      '/api/lb': { target: 'http://localhost:5008', rewrite: (p) => p.replace(/^\/api\/lb/, ''), changeOrigin: true },
      '/api/vr': { target: 'http://localhost:5009', rewrite: (p) => p.replace(/^\/api\/vr/, ''), changeOrigin: true },
      '/api/fd': { target: 'http://localhost:5010', rewrite: (p) => p.replace(/^\/api\/fd/, ''), changeOrigin: true },
      '/api/zn': { target: 'http://localhost:5003', rewrite: (p) => p.replace(/^\/api\/zn/, ''), changeOrigin: true },
      '/api/zs': { target: 'http://localhost:5004', rewrite: (p) => p.replace(/^\/api\/zs/, ''), changeOrigin: true },
      '/api/ze': { target: 'http://localhost:5005', rewrite: (p) => p.replace(/^\/api\/ze/, ''), changeOrigin: true },
      '/api/zw': { target: 'http://localhost:5006', rewrite: (p) => p.replace(/^\/api\/zw/, ''), changeOrigin: true },
      '/api/zc': { target: 'http://localhost:5007', rewrite: (p) => p.replace(/^\/api\/zc/, ''), changeOrigin: true },
    }
  }
})
