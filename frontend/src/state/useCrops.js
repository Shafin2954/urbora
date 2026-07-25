import { useCallback, useEffect, useState } from 'react'
import { apiUrl } from '../api/client.js'

async function request(path, token, options = {}) {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  })
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? `HTTP ${response.status}`)
  return response.status === 204 ? null : response.json()
}

export function useCrops(session) {
  const [crops, setCrops] = useState([])
  const [activeCropId, setActiveCropId] = useState(null)
  const [loading, setLoading] = useState(Boolean(session))
  const [error, setError] = useState(null)
  const token = session?.access_token

  const refresh = useCallback(async () => {
    if (!token) { setCrops([]); setActiveCropId(null); setLoading(false); return }
    setLoading(true)
    try {
      const next = await request('/api/crops', token)
      setCrops(next)
      setActiveCropId((current) => next.some((crop) => crop.id === current) ? current : next[0]?.id ?? null)
      setError(null)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }, [token])

  useEffect(() => { refresh() }, [refresh])
  const create = useCallback(async () => {
    try {
      const crop = await request('/api/crops', token, { method: 'POST' })
      setCrops((old) => [crop, ...old]); setActiveCropId(crop.id); setError(null); return crop
    } catch (err) {
      setError(err.message)
      return null
    }
  }, [token])
  const update = useCallback(async (id, changes) => {
    const crop = await request(`/api/crops/${id}`, token, { method: 'PATCH', body: JSON.stringify(changes) })
    setCrops((old) => old.map((item) => item.id === id ? crop : item)); return crop
  }, [token])
  const remove = useCallback(async (id) => {
    await request(`/api/crops/${id}`, token, { method: 'DELETE' })
    setCrops((old) => old.filter((item) => item.id !== id)); setActiveCropId((current) => current === id ? null : current)
  }, [token])
  return { crops, activeCropId, setActiveCropId, activeCrop: crops.find((crop) => crop.id === activeCropId) ?? null, loading, error, refresh, create, update, remove }
}
