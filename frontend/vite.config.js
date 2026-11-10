import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// Urbora (উর্বরা) frontend config.
//
// Two things here are load-bearing and should not be "tidied up" later:
//
// 1. THE /api PROXY. In dev the browser talks only to :5173, and Vite forwards
//    /api to the FastAPI process. One origin means zero CORS — docs/NOTES.md #13
//    lists SSE+CORS friction as an hour-eater, and this is how it dies at H0
//    instead of at H14. It also matches production, where both are served from
//    one origin, so dev and prod exercise the same request path.
//
// 2. NO SERVICE WORKER. docs/product/PRD.md §9 says manifest-only PWA; docs/NOTES.md #8 says a
//    stale SW cache is a stale-JS ghost hunt nobody has time for. So the PWA
//    plugin here generates a manifest and NOTHING ELSE. See the comments on
//    injectRegister/devOptions below before changing either.
// Product name, read from the same root .env the app uses (src/branding.js).
const brandName = loadEnv(process.env.NODE_ENV ?? 'development', '..', 'VITE_').VITE_BRAND_NAME || 'Urbora'

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
        name: `উর্বরা ${brandName} · স্বপ্ন ফলুক`,
        short_name: brandName,
        description:
          'উর্বরা: ফসলের সমস্যা চিনে, জমির মাপে সমাধান, যেকোনো ফোনে। Expert farm advice in Bangla on any phone.',
        lang: 'bn',
        start_url: '/',
        display: 'standalone',
        orientation: 'portrait',
        // Earthy, not SaaS — CLAUDE.md frontend rules. This green is the
        // single source of the brand colour; index.html and CSS read from it.
        background_color: '#f5eee0',
        theme_color: '#0d3b2e',
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
    // VITE_PORT / API_PROXY_TARGET let a second dev pair run beside the first (.claude/launch.json).
    port: Number(process.env.VITE_PORT || 5000),
    strictPort: true, // fail loudly rather than drifting to another port
    // Replit's preview pane proxies through a different origin; allow all hosts.
    allowedHosts: true,
    proxy: {
      '/api': {
        // 8000 is the documented port (README.md, backend/api/config.py
        // API_PORT default, backend/.env.example): `uvicorn backend.api.main:app
        // --port 8000`. Production remains same-origin and does not use this
        // dev-only proxy.
        target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        // SSE dies if anything buffers or rewrites it. The backend already
        // sends no-transform + X-Accel-Buffering: no; leaving compression off
        // here keeps the proxy from re-introducing a buffer in the middle.
        ws: false,
      },
    },
  },
})
