import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    watch: {
      usePolling: true, // Better for Docker/WSL2 file watching
      interval: 1000, // Poll interval in ms
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    environment: 'happy-dom',
    setupFiles: './src/test/setupTests.js',
    globals: true,
  },
})
