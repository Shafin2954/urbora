// Marketplace API (backend/api/market.py). Farmers act by phone number so
// order/offer SMS reach them; dealers and buyers act with their token.
import { apiUrl } from './client.js'

async function call(path, { method = 'GET', body, headers = {} } = {}) {
  const response = await fetch(apiUrl(path), {
    method,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
  return data
}

const q = (params) => new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString()

export const fetchDistricts = () => call('/api/market/districts')
export const fetchCatalog = () => call('/api/market/catalog')
export const findInputs = (product, district, quantity) =>
  call(`/api/market/inputs?${q({ product, district, quantity })}`)
export const placeOrder = (msisdn, productId, packs) =>
  call('/api/market/orders', { method: 'POST', body: { msisdn, product_id: productId, packs, payment: 'cod' } })
export const myOrders = (msisdn) => call(`/api/market/orders?${q({ msisdn })}`)
export const cancelOrder = (msisdn, orderId) =>
  call(`/api/market/orders/${orderId}/cancel`, { method: 'POST', body: { msisdn } })
export const priceGuide = (crop) => call(`/api/market/price-guide?${q({ crop })}`)
export const createListing = (body) => call('/api/market/listings', { method: 'POST', body })
export const myListings = (msisdn) => call(`/api/market/listings?${q({ msisdn })}`)
export const respondOffer = (msisdn, offerId, accept) =>
  call(`/api/market/offers/${offerId}/respond`, { method: 'POST', body: { msisdn, accept } })

export const registerDealer = (body) => call('/api/market/dealers', { method: 'POST', body })
export const dealerHome = (token) => call('/api/market/dealer', { headers: { 'X-Dealer-Token': token } })
export const saveProduct = (token, body) =>
  call('/api/market/dealer/products', { method: 'PUT', body, headers: { 'X-Dealer-Token': token } })
export const setOrderStatus = (token, orderId, status) =>
  call(`/api/market/dealer/orders/${orderId}/status`, {
    method: 'POST', body: { status }, headers: { 'X-Dealer-Token': token },
  })

export const registerBuyer = (body) => call('/api/market/buyers', { method: 'POST', body })
export const buyerHome = (token) => call('/api/market/buyer', { headers: { 'X-Buyer-Token': token } })
export const makeOffer = (token, body) =>
  call('/api/market/buyer/offers', { method: 'POST', body, headers: { 'X-Buyer-Token': token } })

// Per-viewer convenience only (remembered phone number / token); the page
// works without it, so every access is guarded.
export function remember(key, value) {
  try {
    if (value === undefined) return window.localStorage.getItem(key) ?? ''
    window.localStorage.setItem(key, value)
  } catch {
    return ''
  }
  return value
}
