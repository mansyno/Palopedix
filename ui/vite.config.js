import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'

// Custom debounced logger to eliminate multiple proxy error spam messages in the terminal
const logger = createLogger()
const originalError = logger.error.bind(logger)
const originalWarn = logger.warn.bind(logger)

let lastProxyErrorLog = 0
const PROXY_RELOAD_PATTERNS = ['http proxy error', 'ECONNREFUSED', 'ECONNRESET', 'EPIPE', 'socket hang up', 'ETIMEDOUT']

function filterProxyMessage(msg, originalFn, options) {
  const text = typeof msg === 'string' ? msg : (msg && msg.message) || ''
  if (PROXY_RELOAD_PATTERNS.some(p => text.includes(p))) {
    const now = Date.now()
    if (now - lastProxyErrorLog > 20000) {
      lastProxyErrorLog = now
      console.log('\x1b[33m%s\x1b[0m', '⚡ [PalEngine] Backend server (http://127.0.0.1:8000) is initializing/reloading. Waiting for connection...')
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
            const now = Date.now()
            if (now - lastProxyErrorLog > 20000) {
              lastProxyErrorLog = now
              console.log('\x1b[33m%s\x1b[0m', '⚡ [PalEngine] Backend server (http://127.0.0.1:8000) is initializing/reloading. Waiting for connection...')
            }
            if (res && !res.headersSent && typeof res.writeHead === 'function') {
              try {
                res.writeHead(503, { 'Content-Type': 'application/json' })
                res.end(JSON.stringify({ error: 'Backend server is initializing or reloading...', code: err.code }))
              } catch {
                // socket already destroyed, ignore
              }
            }
          })
        },
      },
      '/assets': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (_err, _req, res) => {
            if (res && !res.headersSent && typeof res.writeHead === 'function') {
              try {
                res.writeHead(503)
                res.end()
              } catch {
                // socket already destroyed, ignore
              }
            }
          })
        },
      },
    },
  },
})
