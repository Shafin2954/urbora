import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// AgriSense frontend config.
//
// Two things here are load-bearing and should not be "tidied up" later:
//
// 1. THE /api PROXY. In dev the browser talks only to :5173, and Vite forwards
//    /api to the FastAPI process. One origin means zero CORS — NOTES.md #13
//    lists SSE+CORS friction as an hour-eater, and this is how it dies at H0
//    instead of at H14. It also matches production, where both are served from
//    one origin, so dev and prod exercise the same request path.
//
// 2. NO SERVICE WORKER. PRD.md §9 says manifest-only PWA; NOTES.md #8 says a
//    stale SW cache is a stale-JS ghost hunt nobody has time for. So the PWA
//    plugin here generates a manifest and NOTHING ELSE. See the comments on
//    injectRegister/devOptions below before changing either.
export default defineConfig({
  // The API and browser share one ignored root `.env`. Vite otherwise looks
  // beside this config (`frontend/.env`) and silently leaves VITE_* values
  // undefined, which turns the login screen into a false "not configured"
  // error even though FastAPI has loaded its copy correctly.
  envDir: '..',
  plugins: [
    react(),
    VitePWA({
      // Emit the manifest, never a registration script. This is what makes
      // this a "manifest-only PWA" rather than a real one: the app is
      // installable and themed, but no SW ever touches our JS.
      injectRegister: null,
      // Belt to that brace: no SW is generated or served in dev either.
      devOptions: { enabled: false },
      // And a third guard, because a dormant sw.js sitting in dist/ is a loaded
      // gun. selfDestroying makes the emitted worker do exactly one thing if
      // anything ever registers it — unregister itself and drop every cache.
      // It also cleans up after any worker a previous deploy left on the
      // origin. Cost: a ~1KB stub instead of the whole workbox runtime.
      selfDestroying: true,
      manifest: {
        name: 'AgriSense — কৃষি পরামর্শ',
        short_name: 'AgriSense',
        description:
          'Bangla-first farm planning: costed, weather-grounded season plans with sources for every number.',
        lang: 'bn',
        start_url: '/',
        display: 'standalone',
        orientation: 'portrait',
        // Earthy, not SaaS — CLAUDE.md frontend rules. This green is the
        // single source of the brand colour; index.html and CSS read from it.
        background_color: '#f7f4ec',
        theme_color: '#2f6b3f',
        icons: [
          {
            src: '/icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any',
          },
          {
            src: '/icon-maskable.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    strictPort: true, // fail loudly rather than drifting to :5174 mid-demo
    proxy: {
      '/api': {
        // 8000 is the documented port (README.md, backend/api/config.py
        // API_PORT default, backend/.env.example): `uvicorn backend.api.main:app
        // --port 8000`. Production remains same-origin and does not use this
        // dev-only proxy.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // SSE dies if anything buffers or rewrites it. The backend already
        // sends no-transform + X-Accel-Buffering: no; leaving compression off
        // here keeps the proxy from re-introducing a buffer in the middle.
        ws: false,
      },
    },
  },
})
