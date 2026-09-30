import { useCallback, useState } from 'react'

// A guest's chats, remembered in this browser only (no account, nothing on a server but the
// conversation itself, which the backend keeps under the g-<uuid> id). One farm id per
// browser, so the land details a guest gave once are recalled in their next chat too.
const KEY = 'urbora.guest.v1'
const MAX = 30

function load() {
  try {
    const data = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    if (data && typeof data.farmId === 'string' && Array.isArray(data.sessions)) return data
  } catch { /* private window or blocked storage: start fresh */ }
  return { farmId: `gf-${crypto.randomUUID()}`, sessions: [] }
}

function save(data) {
  try { localStorage.setItem(KEY, JSON.stringify(data)) } catch { /* not fatal */ }
}

export const newGuestSessionId = () => `g-${crypto.randomUUID()}`

export function useGuestSessions() {
  const [data, setData] = useState(load)
  const update = useCallback((fn) => setData((old) => { const next = fn(old); save(next); return next }), [])

  /** Put a chat at the top of the list (on its first message), or refresh its title. */
  const touch = useCallback((id, title) => update((old) => {
    const existing = old.sessions.find((s) => s.id === id)
    const row = { id, title: title || existing?.title || '', updated: new Date().toISOString() }
    return { ...old, sessions: [row, ...old.sessions.filter((s) => s.id !== id)].slice(0, MAX) }
  }), [update])

  const rename = useCallback((id, title) => update((old) => ({
    ...old, sessions: old.sessions.map((s) => (s.id === id ? { ...s, title } : s)),
  })), [update])

  const remove = useCallback((id) => update((old) => ({ ...old, sessions: old.sessions.filter((s) => s.id !== id) })), [update])

  return { farmId: data.farmId, sessions: data.sessions, touch, rename, remove }
}
