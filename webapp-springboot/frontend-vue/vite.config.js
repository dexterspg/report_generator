import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3001,  // Different from Python version (3000)
    proxy: {
      '/upload': 'http://localhost:8080',
      '/status': 'http://localhost:8080',
      '/download': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
      '/cleanup': 'http://localhost:8080',
      '/extract-company-codes': 'http://localhost:8080',
      '/docs': 'http://localhost:8080'
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
