import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Prevent chunk size warnings on Vercel
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          react:    ['react', 'react-dom', 'react-router-dom'],
          query:    ['@tanstack/react-query'],
          flow:     ['reactflow'],
          ui:       ['lucide-react', 'clsx', 'framer-motion'],
        },
      },
    },
  },
  server: {
    port: 5173,
    // Dev proxy — not active in production build
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
