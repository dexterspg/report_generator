import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/upload': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/download': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/cleanup': 'http://localhost:8000',
      '/docs': 'http://localhost:8000'
    }
  },
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name].[hash].[ext]',
        chunkFileNames: 'assets/[name].[hash].js',
        entryFileNames: 'assets/[name].[hash].js'
      }
    }
  }
})