import { useEffect, useMemo, useState } from 'react'
import GraphPanel from './GraphPanel.jsx'
import { fetchSession, fetchSessions } from '../api/channels.js'

const CHANNEL_BN = { sms: 'SMS', ussd: 'USSD', voice: 'কল' }

/**
 * Live channels: every conversation a button phone had with the agent, and
 * the same provenance graph the web chat shows, rebuilt from the redacted
 * events saved per turn (backend/api/channels.py). Numbers are masked.
 *
 * `follow` keeps the newest conversation selected, which is what a judge
 * watching the emulator next to it wants.
 */
export default function ChannelMonitor({ follow = true }) {
  const [sessions, setSessions] = useState([])
  const [selected, setSelected] = useState(null)
  const [turns, setTurns] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    const tick = () =>
      fetchSessions()
        .then((body) => {
          if (!alive) return
          setSessions(body.sessions)
          setError('')
          if (body.sessions.length && (follow || !selected)) {
            setSelected((current) => (follow ? body.sessions[0].session_id : current ?? body.sessions[0].session_id))
          }
        })
        .catch((err) => alive && setError(err.message))
    tick()
    const id = setInterval(tick, 2500)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [follow, selected])

  useEffect(() => {
    if (!selected) return undefined
    let alive = true
    const tick = () =>
      fetchSession(selected)
        .then((body) => alive && setTurns(body.turns))
        .catch(() => {})
    tick()
    const id = setInterval(tick, 2500)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [selected])

  // GraphPanel reads the same event shapes useChat.js accumulates.
  const trace = useMemo(
    () =>
      turns
        .flatMap((turn) => turn.events.filter((e) => e.type === 'tool_call' || e.type === 'tool_result'))
        .map((event, seq) => ({ ...event, seq })),
    [turns],
  )

  return (
    <section className="monitor">
      <header className="monitor-head">
        <h2>লাইভ চ্যানেল</h2>
        {error && <p className="error">{error}</p>}
      </header>
      <ul className="monitor-sessions">
        {sessions.length === 0 && <li className="muted">এখনো কোনো ফোন কথোপকথন নেই।</li>}
        {sessions.map((s) => (
          <li key={s.session_id}>
            <button
              className={s.session_id === selected ? 'active' : ''}
              onClick={() => setSelected(s.session_id)}
            >
              <span className="chip">{CHANNEL_BN[s.channel] ?? s.channel}</span>
              <span className="mono">{s.masked}</span>
              <span className="muted">{s.turns} বার</span>
            </button>
          </li>
        ))}
      </ul>
      {turns.length > 0 && (
        <ol className="monitor-turns">
          {turns.map((turn) => (
            <li key={turn.turn_id}>
              <p className="turn-q">{turn.user_text}</p>
              <p className="turn-a">{turn.reply_text}</p>
            </li>
          ))}
        </ol>
      )}
      <div className="monitor-graph">
        <GraphPanel trace={trace} usage={null} streaming={false} />
      </div>
    </section>
  )
}
