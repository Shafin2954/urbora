import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiUrl, fetchHealth } from './api/client.js'
import ChatPanel from './components/ChatPanel.jsx'
import FinancePanel from './components/FinancePanel.jsx'
import PlanPanel from './components/PlanPanel.jsx'
import AlertPanel from './components/AlertPanel.jsx'
import CheckoutPanel from './components/CheckoutPanel.jsx'
import GraphPanel from './components/GraphPanel.jsx'
import AuthScreen from './components/AuthScreen.jsx'
import Sidebar from './components/Sidebar.jsx'
import SettingsModal from './components/SettingsModal.jsx'
import { useChat } from './state/useChat.js'
import { useAuth } from './state/useAuth.js'
import { useCrops } from './state/useCrops.js'
import { useSettings } from './state/useSettings.js'
import { translator } from './i18n.js'
import { BRAND_NAME } from './branding.js'
import BrandMark from './components/BrandMark.jsx'

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

// The checkout basket is derived from the finance projection the agent already
// computed, not composed here — so what the farmer is asked to pay for is the
// same priced, cited input list that produced the cost breakdown on screen.
//
// Only *purchasable* lines qualify. BBS's boro/aman/potato cost rows are a
// single aggregate expenditure figure carrying `unit: "ha"` — real data, but
// not something a farmer can order from a supplier. Listing "1 ha of total
// cultivation cost" as a basket item would be inventing a product, so those
// crops simply get no checkout tab. Mustard and lentil, whose cost rows are
// actual fertiliser quantities in kg, do.
const BUYABLE_UNITS = new Set(['kg', 'l', 'litre', 'liter', 'g', 'gm'])

function guestRequestedByUrlOrEnv() {
  try {
    if (new URLSearchParams(window.location.search).get('guest') === '1') return true
  } catch { /* no window (SSR/test) — fall through to env */ }
  return import.meta.env.VITE_DEMO_GUEST === 'true'
}

export default function App() {
  const settings = useSettings()
  const t = useMemo(() => translator(settings.language), [settings.language])
  const [settingsOpen, setSettingsOpen] = useState(false)
  const realAuth = useAuth()
  const [guestMode, setGuestMode] = useState(() => guestRequestedByUrlOrEnv())
  const [guestSession, setGuestSession] = useState(null)
  const auth = guestMode
    ? {
        user: GUEST_USER,
        session: null,
        loading: false,
        configured: true,
        signIn: realAuth.signIn,
        signUp: realAuth.signUp,
        signOut: () => setGuestMode(false),
      }
    : realAuth
  // Guest mode deliberately has no Supabase token and never touches the
  // authenticated crop index. /api/chat accepts the generated session id.
  const crops = useCrops(guestMode ? null : auth.session)
  const { activeCropId, create: createCrop, update: updateCrop } = crops
  const startGuestSession = useCallback(() => {
    setGuestSession({ session_id: crypto.randomUUID(), farm_id: null })
    setTab('chat')
  }, [])
  const handleNewChat = useCallback(() => {
    if (guestMode) return startGuestSession()
    return createCrop()
  }, [createCrop, guestMode, startGuestSession])
  const nameActiveCrop = useCallback((crop) => {
    if (!guestMode && crop && activeCropId) updateCrop(activeCropId, { crop }).catch(() => {})
  }, [activeCropId, guestMode, updateCrop])
  const nameActiveChat = useCallback((title) => {
    if (!guestMode && title && activeCropId) updateCrop(activeCropId, { title }).catch(() => {})
  }, [activeCropId, guestMode, updateCrop])
  const chat = useChat({
    farmId: guestMode ? guestSession?.farm_id : crops.activeCrop?.farm_id,
    sessionId: guestMode ? guestSession?.session_id : crops.activeCrop?.session_id,
    accessToken: guestMode ? undefined : auth.session?.access_token,
    language: settings.language,
    onCropName: nameActiveCrop,
    onChatTitle: nameActiveChat,
  })
  const [health, setHealth] = useState({ state: 'checking', text: 'checking…' })
  const [tab, setTab] = useState('chat')
  // The chat and the Finance tab must key on the SAME farm, or the tab's area
  // edit would recompute a projection the agent never made.
  const farmId = chat.farmId

  const basket = useMemo(() => {
    const items = chat.finance?.scenarios?.base?.items ?? []
    const buyable = items
      .filter((item) => BUYABLE_UNITS.has(String(item.unit ?? '').toLowerCase()))
      .map((item) => ({
        name: item.name,
        qty: item.qty,
        unit: item.unit,
        unit_price_bdt: item.unit_cost,
      }))
    if (!buyable.length || !farmId) return null
    const amount = buyable.reduce((sum, item) => sum + item.qty * item.unit_price_bdt, 0)
    return {
      farmId,
      items: buyable,
      amount: Math.round(amount * 100) / 100,
      label: 'হিসাব থেকে নেওয়া সারের তালিকা — দাম প্রতি হেক্টর।',
    }
  }, [chat.finance, farmId])

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
      className="secondary guest-button"
    >
      অতিথি হিসেবে দেখুন
    </button>
  )

  if (auth.loading) return <main className="auth-screen"><p>{t('app.loading')}</p></main>
  if (!auth.configured) return <main className="auth-screen"><p className="error">Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.</p>{guestButton}</main>
  if (!auth.user) return <>
    <AuthScreen auth={auth} />
    {guestButton}
  </>

  return (
    <div className="app">
      {!guestMode && <Sidebar
        crops={crops.crops}
        activeCropId={crops.activeCropId}
        onSelect={crops.setActiveCropId}
        onCreate={handleNewChat}
        onUpdate={crops.update}
        onDelete={crops.remove}
        onSignOut={auth.signOut}
        user={auth.user}
        t={t}
        onOpenSettings={() => setSettingsOpen(true)}
      />}
      {settingsOpen && <SettingsModal settings={settings} t={t} onClose={() => setSettingsOpen(false)} />}
      <div className="app-main">
      <header className="topbar">
        <a className="brand" href="#/">
          <BrandMark size={32} />
          <h1>{BRAND_NAME}</h1>
        </a>
        <nav className="topnav" aria-label="অন্য পাতা">
          <a href="#/">হোম</a>
          <a href="#/phone">বাটন ফোন</a>
          <a href="#/market">বাজার</a>
        </nav>
        <div className="health" title={apiUrl('/api/health')}>
          <span className={`dot dot-${health.state}`} aria-hidden="true" />
          <span className="mono">{health.text}</span>
          {chat.trace.length > 0 && (
            <span className="mono trace-count">{chat.trace.length} calls</span>
          )}
        </div>
      </header>
      {!guestMode && crops.error && <p className="error" role="alert">{crops.error}</p>}

      {/* Tabs are how you switch panes on a phone; on desktop the trace is
          always visible, so the trace tab hides itself there via CSS. */}
      <nav className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === 'chat'}
          className={`tab ${tab === 'chat' ? 'is-active' : ''}`}
          onClick={() => setTab('chat')}
        >
          {t('tab.chat')}
        </button>
        {chat.finance && (
          <button
            role="tab"
            aria-selected={tab === 'finance'}
            className={`tab ${tab === 'finance' ? 'is-active' : ''}`}
            onClick={() => setTab('finance')}
          >
            {t('tab.finance')}
          </button>
        )}
        {chat.plan && (
          <button role="tab" aria-selected={tab === 'plan'} className={`tab ${tab === 'plan' ? 'is-active' : ''}`} onClick={() => setTab('plan')}>
            {t('tab.plan')}
          </button>
        )}
        {basket && (
          <button role="tab" aria-selected={tab === 'checkout'} className={`tab ${tab === 'checkout' ? 'is-active' : ''}`} onClick={() => setTab('checkout')}>
            {t('tab.checkout')}
          </button>
        )}
        <button
          role="tab"
          aria-selected={tab === 'trace'}
          className={`tab tab-trace ${tab === 'trace' ? 'is-active' : ''}`}
          onClick={() => setTab('trace')}
        >
          {t('tab.graph')}{chat.trace.length > 0 ? ` (${chat.trace.length})` : ''}
        </button>
      </nav>

      {!(guestMode ? guestSession : crops.activeCrop) ? <main className="empty-crop"><h2>{t('start.title')}</h2><p>{crops.error ?? t('start.body')}</p>{guestMode ? <button onClick={handleNewChat}>{t('sidebar.newChat')}</button> : <p className="muted">{t('start.useSidebar')}</p>}</main> : <div className="workspace">
        <main className={`pane pane-chat ${tab === 'chat' ? 'is-active' : ''}`}>
          <ChatPanel
            messages={chat.messages}
            inputRequest={chat.inputRequest}
            streaming={chat.streaming}
            error={chat.error}
            onSend={chat.send}
            onAnswerInput={chat.answerInput}
            onNewChat={guestMode ? handleNewChat : undefined}
            t={t}
            settings={settings}
          />
        </main>

        {chat.finance && (
          <section
            className={`pane pane-finance ${tab === 'finance' ? 'is-active' : ''}`}
            aria-label="Finance"
          >
            <h2 className="pane-title">{t('pane.finance')}</h2>
            <FinancePanel
              finance={chat.finance}
              farmId={farmId}
              onFinance={chat.setFinance}
            />
          </section>
        )}
        {chat.plan && (
          <section className={`pane pane-plan ${tab === 'plan' ? 'is-active' : ''}`} aria-label="Season plan">
            <h2 className="pane-title">{t('pane.plan')}</h2>
            <PlanPanel plan={chat.plan} />
            <AlertPanel farmId={farmId} alerts={chat.alerts} onAlerts={chat.setAlerts} />
          </section>
        )}
        {basket && (
          <section className={`pane pane-checkout ${tab === 'checkout' ? 'is-active' : ''}`} aria-label="Checkout">
            <CheckoutPanel basket={basket} onDone={() => setTab('chat')} />
          </section>
        )}
        <aside
          className={`pane pane-trace ${tab === 'trace' ? 'is-active' : ''}`}
          aria-label="কাজের চিত্র"
        >
          <h2 className="pane-title">{t('pane.graph')}</h2>
          <GraphPanel trace={chat.trace} usage={chat.usage} streaming={chat.streaming} />
        </aside>
      </div>}
      </div>
    </div>
  )
}
