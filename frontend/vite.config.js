import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const BACKEND_PORT = process.env.ARGUS_PORT || process.env.API_PORT || '8080'
const BACKEND_HOST = process.env.ARGUS_HOST || '127.0.0.1'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: `http://${BACKEND_HOST}:${BACKEND_PORT}`,
        changeOrigin: true,
        secure: false,
        configure: (proxy, options) => {
        }
      }
    }
  }
})
