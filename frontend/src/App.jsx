import { useEffect, useState } from 'react'
import './App.css'
import { apiUrl, fetchHealth } from './api/client.js'
import ChatPanel from './components/ChatPanel.jsx'
import TracePanel from './components/TracePanel.jsx'
import { useChat } from './state/useChat.js'

/**
 * One responsive page (PRD.md §9): chat primary, with Trace alongside.
 *
 * Plan and Finance tabs land at H9-H12 when there is real data to put in them.
 * They are deliberately absent rather than present-and-empty — an empty tab
 * reads as a broken feature, and CLAUDE.md bans placeholder content.
 *
 * Layout: on a phone, Chat and Trace are tabs, because the farmer needs the
 * whole screen for the conversation. From 900px the trace becomes a side
 * panel, because that is the judge's view and they want to watch tool calls
 * land while the answer is still being written.
 */

const HEALTH_POLL_MS = 10000
const isDev = import.meta.env.DEV

export default function App() {
  const chat = useChat()
  const [health, setHealth] = useState({ state: 'checking', text: 'checking…' })
  const [tab, setTab] = useState('chat')

  useEffect(() => {
    const controller = new AbortController()
    let timer

    const check = async () => {
      try {
        const body = await fetchHealth(controller.signal)
        setHealth({ state: 'ok', text: body.status })
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

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img src="/icon.svg" alt="" width="30" height="30" />
          <h1>AgriSense</h1>
        </div>
        <div className="health" title={apiUrl('/api/health')}>
          <span className={`dot dot-${health.state}`} aria-hidden="true" />
          <span className="mono">{health.text}</span>
          {chat.trace.length > 0 && (
            <span className="mono trace-count">{chat.trace.length} calls</span>
          )}
        </div>
      </header>

      {/* Tabs are how you switch panes on a phone; on desktop the trace is
          always visible, so the trace tab hides itself there via CSS. */}
      <nav className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === 'chat'}
          className={`tab ${tab === 'chat' ? 'is-active' : ''}`}
          onClick={() => setTab('chat')}
        >
          কথা বলুন
        </button>
        <button
          role="tab"
          aria-selected={tab === 'trace'}
          className={`tab tab-trace ${tab === 'trace' ? 'is-active' : ''}`}
          onClick={() => setTab('trace')}
        >
          Trace{chat.trace.length > 0 ? ` (${chat.trace.length})` : ''}
        </button>
      </nav>

      <div className="workspace">
        <main className={`pane pane-chat ${tab === 'chat' ? 'is-active' : ''}`}>
          <ChatPanel
            messages={chat.messages}
            inputRequest={chat.inputRequest}
            streaming={chat.streaming}
            error={chat.error}
            onSend={chat.send}
            onAnswerInput={chat.answerInput}
          />
        </main>

        <aside
          className={`pane pane-trace ${tab === 'trace' ? 'is-active' : ''}`}
          aria-label="Agent trace"
        >
          <h2 className="pane-title">Agent trace</h2>
          <TracePanel trace={chat.trace} usage={chat.usage} />
        </aside>
      </div>

      {isDev && <DevBar chat={chat} />}
    </div>
  )
}

/**
 * Dev-only harness controls. Stripped from the production build by the
 * import.meta.env.DEV guard, so there is no chance of a "harness" button
 * appearing on stage.
 */
// Each input_request replaces the previous one, so requesting one kind at a
// time is the only way to actually interact with any but the last.
const WIDGET_KINDS = ['district', 'soil_type', 'budget_bdt', 'area', 'name']

function DevBar({ chat }) {
  const [kind, setKind] = useState(WIDGET_KINDS[0])

  return (
    <footer className="devbar">
      <span className="label">dev harness</span>
      <button
        className="secondary"
        disabled={chat.streaming}
        onClick={() => chat.send('harness', { endpoint: '/api/dev/harness' })}
      >
        Events
      </button>
      <select
        className="field field-narrow"
        value={kind}
        onChange={(event) => setKind(event.target.value)}
      >
        {WIDGET_KINDS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <button
        className="secondary"
        disabled={chat.streaming}
        onClick={() => chat.send(kind, { endpoint: '/api/dev/harness/widgets' })}
      >
        Widget
      </button>
      <span className="muted">
        contract-shaped events only — never farmer content
      </span>
    </footer>
  )
}
