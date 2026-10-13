import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendHost = process.env.BACKEND_URL || 'http://localhost:8000'
const wsHost = process.env.WS_URL || backendHost.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      // Proxy REST API calls to FastAPI backend
      '/api': {
        target: backendHost,
        changeOrigin: true,
      },
      // Proxy WebSocket connections
      '/ws': {
        target: wsHost,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
