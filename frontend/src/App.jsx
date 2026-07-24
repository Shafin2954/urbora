import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { apiUrl, fetchHealth } from './api/client.js'
import ChatPanel from './components/ChatPanel.jsx'
import FinancePanel from './components/FinancePanel.jsx'
import PlanPanel from './components/PlanPanel.jsx'
import AlertPanel from './components/AlertPanel.jsx'
import GraphPanel from './components/GraphPanel.jsx'
import AuthScreen from './components/AuthScreen.jsx'
import Sidebar from './components/Sidebar.jsx'
import { useChat } from './state/useChat.js'
import { useAuth } from './state/useAuth.js'
import { useCrops } from './state/useCrops.js'

/**
 * One responsive page (PRD.md §9): chat primary, with the provenance graph
 * alongside.
 *
 * Tabs appear only when they have something real in them. An empty tab reads
 * as a broken feature, and a tab that appears mid-conversation is itself a
 * signal that the agent produced something. So Checkout shows up when there is
 * a basket; Plan and Finance when the agent emits plan_update/finance_update.
 *
 * Layout: on a phone, tabs switch between Chat/Finance/Plan/Evidence/Checkout
 * and the graph, because the farmer needs the whole screen for one thing at a
 * time. From 900px the graph becomes a permanent side panel and the tab bar
 * stays visible to switch the left column — a judge on a laptop can still
 * reach Finance/Plan/Evidence, and watches tool calls land in the graph while
 * the answer is still being written. (The tab bar used to vanish entirely at
 * this breakpoint, which made those panes unreachable on a laptop — fixed
 * alongside this graph refactor.)
 */

const HEALTH_POLL_MS = 10000

// Demo guest bypass (hackathon safety net — CLAUDE.md rule "venue wifi drops"
// risk): the whole app otherwise sits behind a Supabase cloud login, which is
// a single point of failure for a live demo. `?guest=1` in the URL or
// VITE_DEMO_GUEST=true in .env skips it instantly (useful for a pre-set demo
// link); the visible "অতিথি হিসেবে দেখুন" button below the real login lets a
// judge get in with one click without knowing either exists. Guest identity
// is a local stub only — it is never sent to Supabase. Backend routes that
// require a real Supabase JWT (crop persistence, chat history) will still
// degrade honestly rather than crash; see AuthScreen.jsx (not owned here) for
// the real sign-in path.
const GUEST_USER = { id: 'guest', email: 'guest@demo' }
const GUEST_SESSION = { user: GUEST_USER, access_token: 'guest-demo-token' }

function guestRequestedByUrlOrEnv() {
  try {
    if (new URLSearchParams(window.location.search).get('guest') === '1') return true
  } catch { /* no window (SSR/test) — fall through to env */ }
  return import.meta.env.VITE_DEMO_GUEST === 'true'
}

export default function App() {
  const realAuth = useAuth()
  const [guestMode, setGuestMode] = useState(() => guestRequestedByUrlOrEnv())
  const auth = guestMode
    ? {
        user: GUEST_USER,
        session: GUEST_SESSION,
        loading: false,
        configured: true,
        signIn: realAuth.signIn,
        signUp: realAuth.signUp,
        signOut: () => setGuestMode(false),
      }
    : realAuth
  const crops = useCrops(auth.session)
  const { activeCropId, update: updateCrop } = crops
  const nameActiveCrop = useCallback((crop) => {
    if (crop && activeCropId) updateCrop(activeCropId, { crop }).catch(() => {})
  }, [activeCropId, updateCrop])
  const nameActiveChat = useCallback((title) => {
    if (title && activeCropId) updateCrop(activeCropId, { title }).catch(() => {})
  }, [activeCropId, updateCrop])
  const chat = useChat({ farmId: crops.activeCrop?.farm_id, sessionId: crops.activeCrop?.session_id, accessToken: auth.session?.access_token, onCropName: nameActiveCrop, onChatTitle: nameActiveChat })
  const [health, setHealth] = useState({ state: 'checking', text: 'checking…' })
  const [tab, setTab] = useState('chat')
  // The chat and the Finance tab must key on the SAME farm, or the tab's area
  // edit would recompute a projection the agent never made.
  const farmId = chat.farmId

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

  const guestButton = (
    <button
      type="button"
      onClick={() => setGuestMode(true)}
      style={{
        position: 'fixed', bottom: '16px', left: '50%', transform: 'translateX(-50%)',
        zIndex: 1000, padding: '12px 20px', minHeight: '44px', borderRadius: '8px',
        border: '1px solid #2f6b3f', background: '#f7f4ec', color: '#2f6b3f',
        fontWeight: 600, cursor: 'pointer',
      }}
    >
      অতিথি হিসেবে দেখুন (ডেমো) — Continue as guest
    </button>
  )

  if (auth.loading) return <main className="auth-screen"><p>লোড হচ্ছে…</p></main>
  if (!auth.configured) return <main className="auth-screen"><p className="error">Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.</p>{guestButton}</main>
  if (!auth.user) return <>
    <AuthScreen auth={auth} />
    {guestButton}
  </>

  return (
    <div className="app">
      <Sidebar
        crops={crops.crops}
        activeCropId={crops.activeCropId}
        onSelect={crops.setActiveCropId}
        onCreate={crops.create}
        onUpdate={crops.update}
        onDelete={crops.remove}
        onSignOut={auth.signOut}
      />
      <div className="app-main">
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
        {chat.finance && (
          <button
            role="tab"
            aria-selected={tab === 'finance'}
            className={`tab ${tab === 'finance' ? 'is-active' : ''}`}
            onClick={() => setTab('finance')}
          >
            হিসাব
          </button>
        )}
        {chat.plan && (
          <button role="tab" aria-selected={tab === 'plan'} className={`tab ${tab === 'plan' ? 'is-active' : ''}`} onClick={() => setTab('plan')}>
            পরিকল্পনা
          </button>
        )}
        <button
          role="tab"
          aria-selected={tab === 'trace'}
          className={`tab tab-trace ${tab === 'trace' ? 'is-active' : ''}`}
          onClick={() => setTab('trace')}
        >
          চিত্র{chat.trace.length > 0 ? ` (${chat.trace.length})` : ''}
        </button>
      </nav>

      {!crops.activeCrop ? <main className="empty-crop"><h2>শুরু করুন</h2><p>{crops.error ?? 'একটি নতুন আলাপ শুরু করুন।'}</p><button onClick={crops.create}>+ নতুন আলাপ</button></main> : <div className="workspace">
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

        {chat.finance && (
          <section
            className={`pane pane-finance ${tab === 'finance' ? 'is-active' : ''}`}
            aria-label="Finance"
          >
            <h2 className="pane-title">হিসাব</h2>
            <FinancePanel
              finance={chat.finance}
              farmId={farmId}
              onFinance={chat.setFinance}
            />
          </section>
        )}
        {chat.plan && (
          <section className={`pane pane-plan ${tab === 'plan' ? 'is-active' : ''}`} aria-label="Season plan">
            <h2 className="pane-title">মৌসুম পরিকল্পনা</h2>
            <PlanPanel plan={chat.plan} />
            <AlertPanel farmId={farmId} alerts={chat.alerts} onAlerts={chat.setAlerts} />
          </section>
        )}
        <aside
          className={`pane pane-trace ${tab === 'trace' ? 'is-active' : ''}`}
          aria-label="কাজের চিত্র"
        >
          <h2 className="pane-title">কাজের চিত্র</h2>
          <GraphPanel trace={chat.trace} usage={chat.usage} streaming={chat.streaming} />
        </aside>
      </div>}
      </div>
    </div>
  )
}
