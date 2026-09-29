// Web crop-problem check: backend/api/triage.py (the keypad menu's deterministic table).
import { apiUrl } from './client.js'

async function call(path, options = {}) {
  const response = await fetch(apiUrl(path), { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
  return body
}

export const triageOptions = () => call('/api/triage/options')
export const triageCheck = (answers) => call('/api/triage/check', { method: 'POST', body: JSON.stringify(answers) })
