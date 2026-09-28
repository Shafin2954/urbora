import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import Root from './Root.jsx'
import { BRAND_NAME, BRAND_TAGLINE_BN } from './branding.js'

document.title = `${BRAND_NAME} — ${BRAND_TAGLINE_BN}`

// NOTES.md #8 — a stale service worker serves ghost JS, and you lose an hour
// debugging code that isn't running. We never register one (vite.config.js
// sets injectRegister: null), but localhost:5173 is shared ground: any other
// Vite project previously run on this port may have left a service worker and
// its caches behind, scoped to this origin. So in dev we actively evict them.
// If the frontend ever behaves impossibly, look for this warning in the
// console before suspecting your own code.
if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const registration of registrations) {
      registration.unregister()
      console.warn('[agrisense] evicted a stale service worker — see NOTES.md #8')
    }
  })
  if ('caches' in window) {
    caches.keys().then((keys) => keys.forEach((key) => caches.delete(key)))
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
