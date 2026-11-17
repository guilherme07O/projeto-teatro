import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Permite apontar para outro backend sem editar o arquivo:
//   PowerShell: $env:VITE_API_TARGET="http://localhost:8010"; npm run dev
const backendTarget = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
