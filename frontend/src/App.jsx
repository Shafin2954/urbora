import { useEffect, useState } from 'react'
import './App.css'
import { apiUrl, fetchHealth } from './api/client.js'
import ChatPanel from './components/ChatPanel.jsx'
import CheckoutPanel from './components/CheckoutPanel.jsx'
import FinancePanel from './components/FinancePanel.jsx'
import PlanPanel from './components/PlanPanel.jsx'
import EvidencePanel from './components/EvidencePanel.jsx'
import TracePanel from './components/TracePanel.jsx'
import { useChat } from './state/useChat.js'

/**
 * One responsive page (PRD.md §9): chat primary, with Trace alongside.
 *
 * Tabs appear only when they have something real in them. An empty tab reads
 * as a broken feature, and a tab that appears mid-conversation is itself a
 * signal that the agent produced something. So Checkout shows up when there is
 * a basket; Plan and Finance when the agent emits plan_update/finance_update.
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
  const [basket, setBasket] = useState(null)
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
        <button role="tab" aria-selected={tab === 'evidence'} className={`tab ${tab === 'evidence' ? 'is-active' : ''}`} onClick={() => setTab('evidence')}>
          প্রমাণ
        </button>
        {basket && (
          <button
            role="tab"
            aria-selected={tab === 'checkout'}
            className={`tab ${tab === 'checkout' ? 'is-active' : ''}`}
            onClick={() => setTab('checkout')}
          >
            কেনাকাটা
          </button>
        )}
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
          </section>
        )}
        <section className={`pane pane-evidence ${tab === 'evidence' ? 'is-active' : ''}`} aria-label="Tier 0 evidence">
          <h2 className="pane-title">Tier 0 প্রমাণ</h2>
          <EvidencePanel trace={chat.trace} plan={chat.plan} finance={chat.finance} />
        </section>

        {basket && (
          <section
            className={`pane pane-checkout ${tab === 'checkout' ? 'is-active' : ''}`}
            aria-label="Checkout"
          >
            <CheckoutPanel basket={basket} onDone={() => setTab('chat')} />
          </section>
        )}

        <aside
          className={`pane pane-trace ${tab === 'trace' ? 'is-active' : ''}`}
          aria-label="Agent trace"
        >
          <h2 className="pane-title">Agent trace</h2>
          <TracePanel trace={chat.trace} usage={chat.usage} />
        </aside>
      </div>

      {isDev && (
        <DevBar
          chat={chat}
          onBasket={setBasket}
          onFinance={async () => {
            const response = await fetch(apiUrl('/api/finance/recompute'), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                farm_id: farmId,
                overrides: {
                  crop: 'boro_rice',
                  district: 'Rajshahi',
                  area: 2,
                  area_unit: 'bigha',
                },
              }),
            })
            const body = await response.json()
            if (response.ok) setTab('finance')
            else window.alert(body.detail ?? `HTTP ${response.status}`)
            if (response.ok) chat.setFinance(body.finance)
          }}
        />
      )}
    </div>
  )
}

/**
 * A basket for exercising the checkout flow before the agent produces one.
 *
 * Visibly synthetic and in English, like the chat harness: it names itself a
 * harness and makes no agronomic claim, because a plausible-looking Bangla
 * fertiliser basket would be invented data (CLAUDE.md §2.2) and would
 * eventually be mistaken for the real thing.
 *
 * Total is ৳2.00 on purpose — NOTES #22: only ৳2 test debits on the Robi SIM.
 */
const HARNESS_BASKET = {
  label: 'UI harness basket — not a recommendation, no agronomic claim.',
  farmId: 'harness-farm',
  amount: 2.0,
  items: [
    { name: 'Harness item A', qty: 1, unit: 'unit', unit_price_bdt: 1.0 },
    { name: 'Harness item B', qty: 1, unit: 'unit', unit_price_bdt: 1.0 },
  ],
}

/**
 * The E1326 drill (NOTES #4): a basket above the simulator's ৳100 balance, so
 * the insufficient-balance recovery can be rehearsed on cue without draining
 * an account fifty times or adding a back door to the API.
 */
const HARNESS_BASKET_OVER_BALANCE = {
  ...HARNESS_BASKET,
  label: 'UI harness basket — deliberately over the simulator balance (E1326 drill).',
  amount: 500.0,
  items: [{ name: 'Harness item A', qty: 1, unit: 'unit', unit_price_bdt: 500.0 }],
}

/**
 * Dev-only harness controls. Stripped from the production build by the
 * import.meta.env.DEV guard, so there is no chance of a "harness" button
 * appearing on stage.
 */
// Each input_request replaces the previous one, so requesting one kind at a
// time is the only way to actually interact with any but the last.
const WIDGET_KINDS = ['district', 'soil_type', 'budget_bdt', 'area', 'name']

function DevBar({ chat, onBasket, onFinance }) {
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
      <button className="secondary" onClick={() => onBasket(HARNESS_BASKET)}>
        Basket
      </button>
      <button
        className="secondary"
        onClick={() => onBasket(HARNESS_BASKET_OVER_BALANCE)}
      >
        E1326
      </button>
      {/* Not a harness projection — this calls the REAL /api/finance/recompute
          for the demo farm, so whatever it shows is what the engine computed
          from data/prices.md. With the price tables still empty it surfaces the
          server's honest refusal, which is exactly what should be on screen. */}
      <button className="secondary" onClick={onFinance}>
        Finance
      </button>
      <span className="muted">
        contract-shaped events only — never farmer content
      </span>
    </footer>
  )
}
