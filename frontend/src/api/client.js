/**
 * API base resolution.
 *
 * Empty base = same origin, which in dev means the Vite proxy forwards /api to
 * FastAPI (see vite.config.js). That is the intended path: same origin, no
 * CORS, and identical to production. VITE_API_BASE exists only as an escape
 * hatch for hitting a backend on another host (e.g. a phone on the LAN during
 * the PWA install test).
 */
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export const apiUrl = (path) => `${API_BASE}${path}`

/** GET /api/health — used for the connection indicator. */
export async function fetchHealth(signal) {
  const response = await fetch(apiUrl('/api/health'), { signal })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
