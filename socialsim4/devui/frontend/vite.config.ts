import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/devui': {
        target: 'http://localhost:8090',
        changeOrigin: true,
      },
    },
  },
})

