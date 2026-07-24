/**
 * Checkout API (bdapps CaaS, PRD.md §8 Tier2.1).
 *
 * Two calls, in this order, always:
 *   POST /api/checkout/quote  — prices the basket, charges nothing, returns the
 *                               Bangla confirmation prompt and the balance
 *   POST /api/checkout        — charges, and is refused (409) unless that quote
 *                               was registered first
 *
 * The confirmation gate is enforced on the server, so this order is not a
 * convention the UI could get away with breaking — see backend/payments/
 * service.py. The UI's job is to make the confirmation *legible*, not to be
 * the thing that prevents an unwanted charge.
 */
import { apiUrl } from './client.js'

/** An HTTP failure with the status kept, because the UI reacts to 409 vs 400. */
export class CheckoutHttpError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`)
    this.name = 'CheckoutHttpError'
    this.status = status
    this.detail = detail
  }
}

async function post(path, body, signal) {
  const response = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    // FastAPI puts the reason in `detail`; keep it for the technical line
    // under the Bangla message, so a judge can see what actually happened.
    let detail = ''
    try {
      detail = (await response.json())?.detail ?? ''
    } catch {
      detail = ''
    }
    throw new CheckoutHttpError(response.status, detail)
  }

  return response.json()
}

/** GET /api/checkout/mode — live or simulator. Never assumed by the client. */
export async function fetchCheckoutMode(signal) {
  const response = await fetch(apiUrl('/api/checkout/mode'), { signal })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export const requestQuote = (body, signal) =>
  post('/api/checkout/quote', body, signal)

export const chargeConfirmed = (body, signal) => post('/api/checkout', body, signal)
