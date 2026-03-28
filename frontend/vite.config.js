import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api/gc': { target: 'http://127.0.0.1:5001', rewrite: (p) => p.replace(/^\/api\/gc/, ''), changeOrigin: true },
      '/api/tr': { target: 'http://127.0.0.1:5002', rewrite: (p) => p.replace(/^\/api\/tr/, ''), changeOrigin: true },
      '/api/lb': { target: 'http://127.0.0.1:5008', rewrite: (p) => p.replace(/^\/api\/lb/, ''), changeOrigin: true },
      '/api/vr': { target: 'http://127.0.0.1:5009', rewrite: (p) => p.replace(/^\/api\/vr/, ''), changeOrigin: true },
      '/api/fd': { target: 'http://127.0.0.1:5010', rewrite: (p) => p.replace(/^\/api\/fd/, ''), changeOrigin: true },
      '/api/zn': { target: 'http://127.0.0.1:5003', rewrite: (p) => p.replace(/^\/api\/zn/, ''), changeOrigin: true },
      '/api/zs': { target: 'http://127.0.0.1:5004', rewrite: (p) => p.replace(/^\/api\/zs/, ''), changeOrigin: true },
      '/api/ze': { target: 'http://127.0.0.1:5005', rewrite: (p) => p.replace(/^\/api\/ze/, ''), changeOrigin: true },
      '/api/zw': { target: 'http://127.0.0.1:5006', rewrite: (p) => p.replace(/^\/api\/zw/, ''), changeOrigin: true },
      '/api/zc': { target: 'http://127.0.0.1:5007', rewrite: (p) => p.replace(/^\/api\/zc/, ''), changeOrigin: true },
      '/grafana': { target: 'http://127.0.0.1:3001', rewrite: (p) => p.replace(/^\/grafana/, ''), changeOrigin: true },
      '/prometheus': { target: 'http://127.0.0.1:9090', rewrite: (p) => p.replace(/^\/prometheus/, ''), changeOrigin: true },
    }
  }
})
