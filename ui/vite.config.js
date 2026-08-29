import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'

// Custom debounced logger to eliminate multiple proxy error spam messages in the terminal
const logger = createLogger()
const originalError = logger.error.bind(logger)
const originalWarn = logger.warn.bind(logger)

let lastProxyErrorLog = 0

function filterProxyMessage(msg, originalFn, options) {
  const text = typeof msg === 'string' ? msg : (msg && msg.message) || ''
  if (text.includes('http proxy error') || text.includes('ECONNREFUSED')) {
    const now = Date.now()
    if (now - lastProxyErrorLog > 20000) {
      lastProxyErrorLog = now
      console.log('\x1b[33m%s\x1b[0m', '⚡ [PalEngine] Backend server (http://127.0.0.1:8000) is initializing/offline. Waiting for connection...')
    }
    return
  }
  originalFn(msg, options)
}

logger.error = (msg, options) => filterProxyMessage(msg, originalError, options)
logger.warn = (msg, options) => filterProxyMessage(msg, originalWarn, options)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  customLogger: logger,
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            if (err.code === 'ECONNREFUSED') {
              const now = Date.now()
              if (now - lastProxyErrorLog > 20000) {
                lastProxyErrorLog = now
                console.log('\x1b[33m%s\x1b[0m', '⚡ [PalEngine] Backend server (http://127.0.0.1:8000) is initializing/offline. Waiting for connection...')
              }
              if (res && !res.headersSent && res.writeHead) {
                res.writeHead(503, { 'Content-Type': 'application/json' })
                res.end(JSON.stringify({ error: 'Backend server initializing...' }))
              }
            }
          })
        },
      },
      '/assets': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            if (err.code === 'ECONNREFUSED' && res && !res.headersSent && res.writeHead) {
              res.writeHead(503)
              res.end()
            }
          })
        },
      },
    },
  },
})
