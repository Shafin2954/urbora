// Phone-channel API: the browser phone emulator and the live-channels monitor.
// See backend/api/channels.py. Emulator routes answer 404 unless the backend
// runs its SMS provider in simulator mode (or CHANNEL_EMULATOR_ENABLED=true).
import { apiUrl } from './client.js'

async function call(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
  return body
}

const post = (path, body) => call(path, { method: 'POST', body: JSON.stringify(body) })

export const channelStatus = () => call('/api/channels/status')
export const ussdStep = (sessionId, msisdn, text, init = false) =>
  post('/api/channels/emulator/ussd', { session_id: sessionId, msisdn, text, init })
export const sendSms = (msisdn, text) => post('/api/channels/emulator/sms', { msisdn, text })
export const missedCall = (msisdn) => post('/api/channels/emulator/missed-call', { msisdn })
export const fetchInbox = (msisdn) =>
  call(`/api/channels/emulator/inbox?msisdn=${encodeURIComponent(msisdn)}`)
export const fetchSessions = () => call('/api/channels/sessions')
export const fetchSession = (id) => call(`/api/channels/sessions/${encodeURIComponent(id)}`)
