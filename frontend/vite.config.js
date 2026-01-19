import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // 允许外部访问 (Docker必需)
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000', // Docker内部网络的主机名
        changeOrigin: true,
      }
    }
  }
})
