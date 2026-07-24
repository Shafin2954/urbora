import { useState } from 'react'
import { apiUrl } from '../api/client.js'

export default function AlertPanel({ farmId, alerts, onAlerts }) {
  const [busy, setBusy] = useState(false)
  const check = async () => {
    setBusy(true)
    try {
      const response = await fetch(apiUrl(`/api/plan/${farmId}/check`), { method: 'POST' })
      const body = await response.json()
      if (response.ok) onAlerts(body.alerts ?? [])
    } finally { setBusy(false) }
  }
  return <section className="alerts">
    <button className="secondary" onClick={check} disabled={busy}>{busy ? 'পরীক্ষা হচ্ছে…' : 'আমার প্ল্যান চেক করুন'}</button>
    {alerts.map((alert) => <article className="alert-card" key={alert.alert_id}>
      <strong>{alert.task_date} · {alert.task}</strong><p>{alert.conflict}</p><p>{alert.suggestion}</p>
    </article>)}
  </section>
}
