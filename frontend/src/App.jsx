import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { apiUrl, fetchHealth } from './api/client.js'
import { streamSSE } from './api/sse.js'

/**
 * H0-H1 connection self-test.
 *
 * This screen is scaffolding with a job: prove browser -> Vite proxy ->
 * FastAPI -> SSE works, and keeps working. It is deliberately NOT a mock of
 * the farmer UI — CLAUDE.md bans placeholder content, and a fake chat window
 * full of invented advice is exactly the thing that later gets mistaken for a
 * working feature. The real chat UI replaces this at H1-H3; the event list
 * below is the direct ancestor of the Trace panel.
 *
 * Arrival offsets are in milliseconds because they are the actual evidence:
 * events ~400ms apart prove the stream is streaming. All of them landing at
 * once would mean something buffered the response — better to learn that now
 * than on stage.
 */

const HEALTH_POLL_MS = 10000

function StatusDot({ state }) {
  return <span className={`dot dot-${state}`} aria-hidden="true" />
}

export default function App() {
  const [health, setHealth] = useState({ state: 'checking', text: 'checking…' })
  const [events, setEvents] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  // Poll health so the indicator reflects a backend that dies mid-session —
  // uvicorn --reload falling over on a syntax error is the common case.
  useEffect(() => {
    const controller = new AbortController()
    let timer

    const check = async () => {
      try {
        const body = await fetchHealth(controller.signal)
        setHealth({ state: 'ok', text: `${body.service} · ${body.status}` })
      } catch {
        if (controller.signal.aborted) return
        setHealth({ state: 'down', text: 'API unreachable' })
      }
      if (!controller.signal.aborted) timer = setTimeout(check, HEALTH_POLL_MS)
    }

    check()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [])

  const runSelfTest = useCallback(async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setEvents([])
    setError(null)
    setStreaming(true)

    const startedAt = performance.now()
    let seq = 0

    try {
      // POST on purpose: same verb and body shape as the real /api/chat, so
      // this exercises the transport we ship rather than a GET stand-in.
      await streamSSE(apiUrl('/api/hello/stream'), {
        method: 'POST',
        body: { source: 'frontend-selftest' },
        signal: controller.signal,
        onEvent: (payload) => {
          setEvents((prev) => [
            ...prev,
            { seq: seq++, atMs: Math.round(performance.now() - startedAt), payload },
          ])
        },
      })
    } catch (err) {
      if (!controller.signal.aborted) setError(err.message)
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      setStreaming(false)
    }
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  const tokenText = events
    .filter((event) => event.payload.type === 'token')
    .map((event) => event.payload.text)
    .join('')

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/icon.svg" alt="" width="32" height="32" />
          <h1>AgriSense</h1>
        </div>
        <div className="health" title={apiUrl('/api/health')}>
          <StatusDot state={health.state} />
          <span className="mono">{health.text}</span>
        </div>
      </header>

      <main className="panel">
        <div className="panel-head">
          <h2>Connection self-test</h2>
          <p className="muted">
            H0 scaffolding — proves browser → Vite proxy → FastAPI → SSE. The
            chat UI replaces this screen at H1–H3.
          </p>
        </div>

        <button onClick={runSelfTest} disabled={streaming}>
          {streaming ? 'Streaming…' : 'Run SSE self-test'}
        </button>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        {tokenText && (
          <div className="assembled">
            <span className="label">Assembled tokens</span>
            {/* Bangla round-trips through SSE here. If this line renders as
                boxes or mojibake, the problem is encoding, not agronomy. */}
            <p className="assembled-text">{tokenText}</p>
          </div>
        )}

        {events.length > 0 && (
          <ol className="events">
            {events.map((event) => (
              <li key={event.seq}>
                <span className="at mono">+{event.atMs}ms</span>
                <span className={`type type-${event.payload.type}`}>
                  {event.payload.type}
                </span>
                <code className="raw">{JSON.stringify(event.payload)}</code>
              </li>
            ))}
          </ol>
        )}

        {events.length > 0 && !streaming && (
          <p className="muted verdict">
            {events.length} events received. The spacing is the proof: staggered
            offsets mean a live stream, identical offsets would mean it was
            buffered and flushed at the end.
          </p>
        )}
      </main>
    </div>
  )
}
